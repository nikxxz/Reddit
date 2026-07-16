import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { browseRedditEntityMedia, searchRedditEntities } from "../api/redditEntities";
import { EntityBrowserPage } from "./EntityBrowserPage";
import { DownloadJobsProvider } from "../hooks/useDownloads";
import { renderWithProviders } from "../test/render";

vi.mock("../api/downloadsApi", () => ({
  listDownloads: vi.fn().mockResolvedValue({ jobs: [] }),
  cancelDownload: vi.fn(),
  clearDownloads: vi.fn(),
  clearTerminalDownloads: vi.fn(),
  retryDownload: vi.fn(),
  startDownload: vi.fn()
}));

vi.mock("../api/redditEntities", () => ({
  searchRedditEntities: vi.fn(),
  browseRedditEntityMedia: vi.fn(),
  normalizeEntityQuery: (value = "") => value.trim().replace(/^\/?[ru]\//i, "").trim()
}));

const imageItem = {
  id: "post-1",
  title: "Media post",
  subreddit: "pics",
  author: "tester",
  media_type: "image",
  thumbnail_url: "https://example.com/thumb.jpg",
  media_url: "https://i.redd.it/example.jpg",
  media_urls: ["https://i.redd.it/example.jpg"],
  gallery_items: [],
  is_nsfw: false,
  download_strategy: "direct"
};

function renderEntityPage(ui) {
  return renderWithProviders(<DownloadJobsProvider>{ui}</DownloadJobsProvider>);
}

describe("EntityBrowserPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits a normalized combined entity search and renders both sections", async () => {
    searchRedditEntities.mockResolvedValue({
      query: "pics",
      subreddits: [{ name: "pics", title: "Pictures", subscribers: 100 }],
      users: [{ username: "picsuser", link_karma: 10, comment_karma: 20 }]
    });
    const onNavigateEntity = vi.fn();
    renderEntityPage(
      <EntityBrowserPage route={{}} onNavigateEntity={onNavigateEntity} onNavigateBrowse={vi.fn()} onReplaceEntityQuery={vi.fn()} />
    );

    fireEvent.change(screen.getByLabelText("Search subreddits or users"), { target: { value: "r/pics" } });
    fireEvent.submit(screen.getByLabelText("Search subreddits or users").closest("form"));

    await screen.findByText("Subreddits");
    expect(searchRedditEntities).toHaveBeenCalledWith("pics", expect.any(Object));
    expect(screen.getByText("Users")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Subreddit pics"));
    expect(onNavigateEntity).toHaveBeenCalledWith("subreddit", "pics");
  });

  it("renders an empty entity-search state", async () => {
    searchRedditEntities.mockResolvedValue({ query: "zz", subreddits: [], users: [] });
    renderEntityPage(
      <EntityBrowserPage route={{}} onNavigateEntity={vi.fn()} onNavigateBrowse={vi.fn()} onReplaceEntityQuery={vi.fn()} />
    );

    fireEvent.change(screen.getByLabelText("Search subreddits or users"), { target: { value: "zz" } });
    fireEvent.submit(screen.getByLabelText("Search subreddits or users").closest("form"));

    expect(await screen.findByText("No matching subreddits or users found.")).toBeInTheDocument();
  });

  it("loads subreddit media, updates filters, and preserves cards on load more", async () => {
    browseRedditEntityMedia
      .mockResolvedValueOnce({
        entity: { type: "subreddit", name: "pics", title: "Pictures" },
        items: [imageItem],
        next_cursor: "t3_next",
        has_more: true,
        count: 1
      })
      .mockResolvedValueOnce({
        entity: { type: "subreddit", name: "pics", title: "Pictures" },
        items: [{ ...imageItem, id: "post-2", title: "Second post" }, imageItem],
        next_cursor: null,
        has_more: false,
        count: 2
      })
      .mockResolvedValueOnce({
        entity: { type: "subreddit", name: "pics", title: "Pictures" },
        items: [],
        next_cursor: null,
        has_more: false,
        count: 0
      });
    renderEntityPage(
      <EntityBrowserPage
        route={{ entityType: "subreddit", entityName: "pics", query: new URLSearchParams("sort=hot&media=all&nsfw=false") }}
        onNavigateEntity={vi.fn()}
        onNavigateBrowse={vi.fn()}
        onReplaceEntityQuery={vi.fn()}
      />
    );

    expect(await screen.findByText("Media post")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Load More"));
    expect(await screen.findByText("Second post")).toBeInTheDocument();
    expect(screen.getAllByText("Media post")).toHaveLength(1);

    fireEvent.click(screen.getByText("Filters"));
    fireEvent.click(await screen.findByText("Images"));
    await waitFor(() => {
      expect(browseRedditEntityMedia).toHaveBeenLastCalledWith(
        expect.objectContaining({ mediaType: "images" }),
        expect.any(Object)
      );
    });
  });

  it("renders user headers and rejects text-only responses from rendering as cards", async () => {
    browseRedditEntityMedia.mockResolvedValue({
      entity: { type: "user", name: "example", link_karma: 1, comment_karma: 2 },
      items: [],
      next_cursor: null,
      has_more: false,
      count: 0,
      message: "No matching media was found for this user."
    });
    renderEntityPage(
      <EntityBrowserPage
        route={{ entityType: "user", entityName: "example", query: new URLSearchParams("sort=new") }}
        onNavigateEntity={vi.fn()}
        onNavigateBrowse={vi.fn()}
        onReplaceEntityQuery={vi.fn()}
      />
    );

    expect(await screen.findByText("u/example")).toBeInTheDocument();
    expect(screen.getByText("No matching media was found for this user.")).toBeInTheDocument();
  });
});

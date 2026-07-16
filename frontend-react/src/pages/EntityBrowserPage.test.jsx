import { fireEvent, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
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

  it("preserves entity search results after opening an entity and returning to browse", async () => {
    searchRedditEntities.mockResolvedValue({
      query: "pics",
      subreddits: [{ name: "pics", title: "Pictures", subscribers: 100 }],
      users: [{ username: "picposter", link_karma: 10, comment_karma: 20 }]
    });
    browseRedditEntityMedia.mockResolvedValue({
      entity: { type: "subreddit", name: "pics", title: "Pictures" },
      items: [],
      next_cursor: null,
      has_more: false,
      count: 0
    });
    const props = {
      onNavigateEntity: vi.fn(),
      onNavigateBrowse: vi.fn(),
      onReplaceEntityQuery: vi.fn()
    };
    const { rerender } = renderEntityPage(<EntityBrowserPage route={{}} {...props} />);

    fireEvent.change(screen.getByLabelText("Search subreddits or users"), { target: { value: "pics" } });
    fireEvent.submit(screen.getByLabelText("Search subreddits or users").closest("form"));

    expect(await screen.findByLabelText("Subreddit pics")).toBeInTheDocument();

    rerender(
      <MantineProvider>
        <DownloadJobsProvider>
          <EntityBrowserPage
            route={{ entityType: "subreddit", entityName: "pics", query: new URLSearchParams() }}
            {...props}
          />
        </DownloadJobsProvider>
      </MantineProvider>
    );
    expect(await screen.findByText("r/pics")).toBeInTheDocument();

    rerender(
      <MantineProvider>
        <DownloadJobsProvider>
          <EntityBrowserPage route={{}} {...props} />
        </DownloadJobsProvider>
      </MantineProvider>
    );

    expect(screen.getByLabelText("Subreddit pics")).toBeInTheDocument();
    expect(screen.getByLabelText("Reddit user picposter")).toBeInTheDocument();
    expect(searchRedditEntities).toHaveBeenCalledTimes(1);
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
    expect(screen.getByText("1 media item · All media · Hot")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Load More"));
    expect(await screen.findByText("Second post")).toBeInTheDocument();
    expect(screen.getAllByText("Media post")).toHaveLength(1);
    expect(screen.getByText("2 media items · All media · Hot")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Filters"));
    fireEvent.click(await screen.findByText("Images"));
    await waitFor(() => {
      expect(browseRedditEntityMedia).toHaveBeenLastCalledWith(
        expect.objectContaining({ mediaType: "images" }),
        expect.any(Object)
      );
    });
  });

  it("shows only supported user sort options", async () => {
    browseRedditEntityMedia.mockResolvedValue({
      entity: { type: "user", name: "example", link_karma: 1, comment_karma: 2 },
      items: [imageItem],
      next_cursor: null,
      has_more: false,
      count: 1
    });
    renderEntityPage(
      <EntityBrowserPage
        route={{ entityType: "user", entityName: "example", query: new URLSearchParams("sort=new") }}
        onNavigateEntity={vi.fn()}
        onNavigateBrowse={vi.fn()}
        onReplaceEntityQuery={vi.fn()}
      />
    );

    expect(await screen.findByText("Media post")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Filters"));
    await screen.findByText("Media");

    expect(screen.getByDisplayValue("New")).toBeInTheDocument();
    expect(screen.queryByText("Hot")).not.toBeInTheDocument();
    expect(screen.queryByText("Rising")).not.toBeInTheDocument();
  });

  it("normalizes invalid user URL filters before requesting media", async () => {
    browseRedditEntityMedia.mockResolvedValue({
      entity: { type: "user", name: "example", link_karma: 1, comment_karma: 2 },
      items: [imageItem],
      next_cursor: null,
      has_more: false,
      count: 1
    });
    const onReplaceEntityQuery = vi.fn();
    renderEntityPage(
      <EntityBrowserPage
        route={{ entityType: "user", entityName: "example", query: new URLSearchParams("sort=hot&media=nonsense&time=century&nsfw=yes") }}
        onNavigateEntity={vi.fn()}
        onNavigateBrowse={vi.fn()}
        onReplaceEntityQuery={onReplaceEntityQuery}
      />
    );

    expect(await screen.findByText("Media post")).toBeInTheDocument();
    expect(browseRedditEntityMedia).toHaveBeenCalledTimes(1);
    expect(browseRedditEntityMedia).toHaveBeenCalledWith(
      expect.objectContaining({
        entityType: "user",
        mediaType: "all",
        sortBy: "new",
        timeFilter: "all",
        includeNsfw: false
      }),
      expect.any(Object)
    );
    expect(onReplaceEntityQuery).toHaveBeenLastCalledWith("sort=new&time=all&media=all&nsfw=false");
  });

  it("normalizes invalid subreddit URL filters and includes top time in the summary", async () => {
    browseRedditEntityMedia.mockResolvedValue({
      entity: { type: "subreddit", name: "pics", title: "Pictures" },
      items: [imageItem],
      next_cursor: null,
      has_more: false,
      count: 1
    });
    const onReplaceEntityQuery = vi.fn();
    renderEntityPage(
      <EntityBrowserPage
        route={{ entityType: "subreddit", entityName: "pics", query: new URLSearchParams("sort=banana&media=audio&time=century&nsfw=yes") }}
        onNavigateEntity={vi.fn()}
        onNavigateBrowse={vi.fn()}
        onReplaceEntityQuery={onReplaceEntityQuery}
      />
    );

    expect(await screen.findByText("Media post")).toBeInTheDocument();
    expect(browseRedditEntityMedia).toHaveBeenCalledTimes(1);
    expect(browseRedditEntityMedia).toHaveBeenCalledWith(
      expect.objectContaining({ mediaType: "all", sortBy: "hot", timeFilter: "all", includeNsfw: false }),
      expect.any(Object)
    );
    expect(onReplaceEntityQuery).toHaveBeenLastCalledWith("sort=hot&time=all&media=all&nsfw=false");

    browseRedditEntityMedia.mockClear();
    renderEntityPage(
      <EntityBrowserPage
        route={{ entityType: "subreddit", entityName: "pics", query: new URLSearchParams("sort=top&media=video&time=month&nsfw=true") }}
        onNavigateEntity={vi.fn()}
        onNavigateBrowse={vi.fn()}
        onReplaceEntityQuery={vi.fn()}
      />
    );
    expect(await screen.findByText("1 media item · Videos · Top · This month · NSFW included")).toBeInTheDocument();
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

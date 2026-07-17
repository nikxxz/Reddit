import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getUniversalSearch,
  loadMorePinterestResults,
  listUniversalProviders,
  startUniversalSearch
} from "../api/universalSearchApi";
import { renderWithProviders } from "../test/render";
import { UniversalSearchPage } from "./UniversalSearchPage";

vi.mock("../api/universalSearchApi", () => ({
  listUniversalProviders: vi.fn(),
  startUniversalSearch: vi.fn(),
  getUniversalSearch: vi.fn(),
  loadMorePinterestResults: vi.fn()
}));

const providers = [
  {
    name: "reddit",
    display_name: "Reddit",
    implementation_status: "available",
    health: "ready",
    authenticated: true,
    capabilities: { keyword_search: true }
  },
  {
    name: "tumblr",
    display_name: "Tumblr",
    implementation_status: "planned",
    health: "not_implemented",
    authenticated: false,
    capabilities: { keyword_search: true }
  },
  {
    name: "pinterest",
    display_name: "Pinterest",
    implementation_status: "planned",
    health: "not_implemented",
    authenticated: false,
    capabilities: { keyword_search: true }
  },
  {
    name: "instagram",
    display_name: "Instagram",
    implementation_status: "planned",
    health: "not_implemented",
    authenticated: false,
    capabilities: { keyword_search: true }
  }
];

const redditItem = {
  provider: "reddit",
  provider_item_id: "post-1",
  canonical_url: "https://www.reddit.com/r/wallpapers/comments/post-1/cat/",
  title: "Universal cat",
  author: "poster",
  collection: "wallpapers",
  media_type: "image",
  thumbnail_url: "https://example.com/thumb.jpg",
  preview_url: "https://example.com/cat.jpg",
  media_urls: ["https://example.com/cat.jpg"],
  media_count: null,
  width: 1200,
  height: 800,
  duration_seconds: null,
  created_at: "2026-07-17T10:00:00Z",
  nsfw: false,
  source_metadata: { collection_label: "Subreddit" },
  capabilities: { preview: true, download_single: false, download_all: false }
};

describe("UniversalSearchPage", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    listUniversalProviders.mockResolvedValue({ providers });
    startUniversalSearch.mockResolvedValue({
      search_id: "search-1",
      status: "searching",
      providers: {
        reddit: { status: "searching", result_count: 0, error: null },
        tumblr: { status: "not_implemented", result_count: 0, error: null }
      }
    });
    getUniversalSearch.mockResolvedValue({
      search_id: "search-1",
      status: "completed_with_errors",
      providers: {
        reddit: { status: "completed", result_count: 1, error: null },
        tumblr: { status: "not_implemented", result_count: 0, error: null },
        pinterest: { status: "not_implemented", result_count: 0, error: null },
        instagram: { status: "not_implemented", result_count: 0, error: null }
      },
      items: [redditItem],
      created_at: "2026-07-17T10:00:00Z",
      updated_at: "2026-07-17T10:00:01Z"
    });
    loadMorePinterestResults.mockResolvedValue({
      search_id: "search-1",
      status: "completed_with_errors",
      providers: {
        reddit: { status: "completed", result_count: 1, error: null },
        pinterest: { status: "completed", result_count: 1, error: null }
      },
      items: [redditItem],
      created_at: "2026-07-17T10:00:00Z",
      updated_at: "2026-07-17T10:00:02Z"
    });
  });

  it("renders all provider selectors and labels planned providers", async () => {
    renderWithProviders(<UniversalSearchPage />);

    expect(await screen.findByLabelText("Reddit")).toBeInTheDocument();
    expect(screen.getAllByText("Tumblr").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pinterest").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Instagram").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("checkbox").length).toBeGreaterThanOrEqual(8);
    expect(screen.getAllByText("Planned").length).toBeGreaterThanOrEqual(3);
  });

  it("submits selected providers and renders Reddit results beside planned providers", async () => {
    renderWithProviders(<UniversalSearchPage />);

    fireEvent.change(screen.getByLabelText("Search query"), {
      target: { value: "cat" }
    });
    fireEvent.click(await screen.findByRole("button", { name: "Search" }));

    await waitFor(() => expect(startUniversalSearch).toHaveBeenCalled());
    expect(startUniversalSearch.mock.calls[0][0]).toMatchObject({
      query: "cat",
      providers: ["reddit", "tumblr", "pinterest", "instagram"],
      media_types: ["image", "gif", "video", "gallery"]
    });

    await waitFor(() => expect(getUniversalSearch).toHaveBeenCalled(), { timeout: 2500 });

    expect(await screen.findByText("Universal cat")).toBeInTheDocument();
    expect(screen.getByText("Reddit - wallpapers")).toBeInTheDocument();
    expect(screen.getAllByText("Planned").length).toBeGreaterThanOrEqual(3);
  });

  it("shows Pinterest options only when Pinterest is selected", async () => {
    renderWithProviders(<UniversalSearchPage />);

    expect(await screen.findByText("Pinterest options")).toBeInTheDocument();
    expect(screen.getAllByLabelText("Pinterest mode").at(-1)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: /Pinterest/ }));
    expect(screen.queryByText("Pinterest options")).not.toBeInTheDocument();
  });

  it("opens a Universal preview without download buttons", async () => {
    renderWithProviders(<UniversalSearchPage />);

    fireEvent.change(screen.getByLabelText("Search query"), {
      target: { value: "cat" }
    });
    fireEvent.click(await screen.findByRole("button", { name: "Search" }));
    await waitFor(() => expect(getUniversalSearch).toHaveBeenCalled(), { timeout: 2500 });
    fireEvent.click(await screen.findByText("Universal cat"));

    expect(await screen.findByText("Open source")).toBeInTheDocument();
    expect(screen.getByText("Universal downloads will be added in a later phase.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /download/i })).not.toBeInTheDocument();
  });

  it("ignores stale search responses from a previous search", async () => {
    let resolveOldSearch;
    const oldSearchPromise = new Promise((resolve) => {
      resolveOldSearch = resolve;
    });
    startUniversalSearch
      .mockReturnValueOnce(oldSearchPromise)
      .mockResolvedValueOnce({
        search_id: "new-search",
        status: "searching",
        providers: { reddit: { status: "searching", result_count: 0, error: null } }
      });
    getUniversalSearch.mockResolvedValue({
      search_id: "new-search",
      status: "completed",
      providers: { reddit: { status: "completed", result_count: 1, error: null } },
      items: [{ ...redditItem, provider_item_id: "new", title: "New result" }],
      created_at: "2026-07-17T10:00:00Z",
      updated_at: "2026-07-17T10:00:01Z"
    });

    renderWithProviders(<UniversalSearchPage />);
    fireEvent.change(screen.getByLabelText("Search query"), {
      target: { value: "first" }
    });
    fireEvent.click(await screen.findByRole("button", { name: "Search" }));

    fireEvent.change(screen.getByLabelText("Search query"), {
      target: { value: "second" }
    });
    fireEvent.click(screen.getByRole("button", { name: /Search/ }));

    resolveOldSearch({
      search_id: "old-search",
      status: "completed",
      providers: { reddit: { status: "completed", result_count: 1, error: null } }
    });
    await waitFor(() => expect(getUniversalSearch).toHaveBeenCalledTimes(1), { timeout: 2500 });

    expect(await screen.findByText("New result")).toBeInTheDocument();
    expect(screen.queryByText("Old result")).not.toBeInTheDocument();
  });
});

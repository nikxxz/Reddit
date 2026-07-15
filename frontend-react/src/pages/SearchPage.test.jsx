import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { searchRedditMedia } from "../api/redditSearchApi";
import { renderWithProviders } from "../test/render";
import { SearchPage } from "./SearchPage";

vi.mock("../api/redditSearchApi", () => ({
  searchRedditMedia: vi.fn()
}));

vi.mock("../hooks/useDownloadJob", () => ({
  useDownloadJob: () => ({
    isActive: false,
    state: { status: "idle" },
    start: vi.fn(),
    cancel: vi.fn(),
    reset: vi.fn()
  })
}));

function setMobileViewport(matches) {
  window.matchMedia.mockImplementation((query) => ({
    matches: /max-width/.test(query) ? matches : false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }));
}

const resultItem = {
  id: "post-1",
  title: "Cat photo",
  subreddit: "natureismetal",
  author: "poster",
  media_type: "image",
  media_url: "https://example.com/cat.jpg",
  thumbnail_url: "https://example.com/thumb.jpg",
  created_utc: 1784073600
};

function submitSearchForm() {
  fireEvent.submit(document.querySelector("form"));
}

describe("SearchPage responsive behavior", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setMobileViewport(false);
    searchRedditMedia.mockResolvedValue({
      items: [resultItem],
      next_after: null,
      count: 1,
      media_type: "images",
      effective_sort: "relevance",
      time_filter: "all",
      subreddit: "natureismetal"
    });
  });

  it("uses separate constrained search and wide results wrappers", () => {
    renderWithProviders(<SearchPage />);

    expect(document.querySelector(".search-controls-container")).toBeInTheDocument();
    expect(document.querySelector(".search-results-container")).toBeInTheDocument();
    expect(document.querySelector(".search-controls-panel")).toBeInTheDocument();
  });

  it("collapses filters after a successful mobile search and reopens them", async () => {
    setMobileViewport(true);
    renderWithProviders(<SearchPage />);

    fireEvent.change(screen.getByLabelText("Keyword"), {
      target: { value: "cat" }
    });
    fireEvent.change(screen.getByLabelText("Subreddit"), {
      target: { value: "natureismetal" }
    });
    submitSearchForm();

    await screen.findByText("Cat photo");
    expect(screen.getByRole("button", { name: "Edit filters" })).toBeInTheDocument();
    expect(screen.getByText("cat - r/natureismetal")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Edit filters" }));

    await waitFor(() => expect(screen.getByLabelText("Keyword")).toHaveValue("cat"));
    expect(screen.getByLabelText("Subreddit")).toHaveValue("natureismetal");
  });

  it("keeps desktop filters expanded after a successful search", async () => {
    renderWithProviders(<SearchPage />);

    fireEvent.change(screen.getByLabelText("Keyword"), {
      target: { value: "cat" }
    });
    submitSearchForm();

    await screen.findByText("Cat photo");
    expect(screen.getByLabelText("Keyword")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit filters" })).not.toBeInTheDocument();
  });

  it("keeps filters open for validation errors and failed searches", async () => {
    setMobileViewport(true);
    renderWithProviders(<SearchPage />);

    submitSearchForm();
    expect(screen.getByText("Enter a keyword or subreddit.")).toBeInTheDocument();
    expect(screen.getByLabelText("Keyword")).toBeInTheDocument();

    searchRedditMedia.mockRejectedValueOnce(new Error("Search failed"));
    fireEvent.change(screen.getByLabelText("Keyword"), {
      target: { value: "cat" }
    });
    submitSearchForm();

    await screen.findByText("Search failed");
    expect(screen.getByLabelText("Keyword")).toBeInTheDocument();
  });
});

import { fireEvent, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { searchRedditMedia } from "../../api/redditSearchApi";
import { listDownloads } from "../../api/downloadsApi";
import { DownloadJobsProvider } from "../../hooks/useDownloads";
import { renderWithProviders } from "../../test/render";
import { AppLayout } from "./AppLayout";

vi.mock("../../api/redditSearchApi", () => ({
  searchRedditMedia: vi.fn()
}));

vi.mock("../../api/downloadsApi", () => ({
  listDownloads: vi.fn(),
  cancelDownload: vi.fn(),
  clearDownloads: vi.fn(),
  clearTerminalDownloads: vi.fn(),
  retryDownload: vi.fn()
}));

const connections = {
  backend: { status: "online", message: "" },
  reddit: { status: "online", message: "" }
};

const redditAuth = {
  state: {
    status: "connected",
    connected: true,
    username: "tester",
    error: null
  },
  connect: vi.fn(),
  disconnect: vi.fn(),
  retry: vi.fn()
};

function renderLayout() {
  return renderWithProviders(
    <DownloadJobsProvider>
      <AppLayout
        connections={connections}
        isChecking={false}
        onRetryConnections={vi.fn()}
        redditAuth={redditAuth}
      />
    </DownloadJobsProvider>
  );
}

describe("AppLayout page persistence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listDownloads.mockResolvedValue({ jobs: [] });
    searchRedditMedia.mockResolvedValue({
      items: [
        {
          id: "post-1",
          title: "Persistent cat result",
          subreddit: "cats",
          author: "poster",
          media_type: "image",
          thumbnail_url: "https://example.com/cat.jpg",
          created_utc: 1784073600
        }
      ],
      next_after: null,
      count: 1,
      media_type: "images",
      effective_sort: "relevance",
      time_filter: "all",
      subreddit: "cats"
    });
  });

  it("keeps search filters and results mounted while visiting downloads", async () => {
    renderLayout();

    fireEvent.change(screen.getByLabelText("Keyword"), {
      target: { value: "cat" }
    });
    fireEvent.change(screen.getByLabelText("Subreddit"), {
      target: { value: "cats" }
    });
    fireEvent.submit(document.querySelector("form"));

    expect(await screen.findByText("Persistent cat result")).toBeInTheDocument();

    const primaryNavigation = screen.getByRole("navigation", {
      name: "Primary navigation"
    });

    fireEvent.click(within(primaryNavigation).getByText("Downloads").closest("a"));
    expect(screen.getAllByText("Downloads").length).toBeGreaterThan(0);

    fireEvent.click(within(primaryNavigation).getByText("Search").closest("a"));

    expect(screen.getByText("Persistent cat result")).toBeInTheDocument();
    expect(screen.getByLabelText("Keyword")).toHaveValue("cat");
    expect(screen.getByLabelText("Subreddit")).toHaveValue("cats");
  });
});

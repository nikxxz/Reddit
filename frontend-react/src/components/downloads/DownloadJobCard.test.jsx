import { MantineProvider } from "@mantine/core";
import { fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DownloadJobCard } from "./DownloadJobCard";
import { renderWithProviders } from "../../test/render";

const job = {
  jobId: "job-1",
  postId: "post-1",
  status: "completed",
  availability: "available",
  progress: 100,
  message: "",
  mediaType: "image",
  title: "Example",
  subreddit: "pics",
  author: "user",
  thumbnailUrl: "https://preview.redd.it/thumb.jpg",
  createdAt: "2026-07-15T00:00:00Z",
  files: [],
  warnings: [],
  cancellable: false,
  retryable: false
};

describe("DownloadJobCard", () => {
  it("retries the thumbnail when the source changes", () => {
    const renderCard = (cardJob) => (
      <MantineProvider>
        <DownloadJobCard job={cardJob} pendingActions={{}} onCancel={vi.fn()} onRetry={vi.fn()} />
      </MantineProvider>
    );
    const { container, rerender } = renderWithProviders(
      <DownloadJobCard job={job} pendingActions={{}} onCancel={vi.fn()} onRetry={vi.fn()} />
    );

    fireEvent.error(container.querySelector("img"));

    rerender(renderCard({ ...job, thumbnailUrl: "/api/library/thumbnails/download-1" }));

    expect(container.querySelector("img")).toHaveAttribute(
      "src",
      "/api/library/thumbnails/download-1"
    );
  });
});

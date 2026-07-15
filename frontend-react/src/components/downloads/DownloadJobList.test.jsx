import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DownloadJobList } from "./DownloadJobList";
import { renderWithProviders } from "../../test/render";

const baseJob = {
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
  createdAt: "2026-07-15T00:00:00Z",
  files: [],
  warnings: [],
  cancellable: false,
  retryable: false
};

describe("DownloadJobList", () => {
  it("groups finalizing jobs as active", () => {
    renderWithProviders(
      <DownloadJobList
        jobs={[{ ...baseJob, jobId: "active", status: "finalizing", title: "Finalizing job" }]}
        filter="all"
        pendingActions={{}}
        onCancel={vi.fn()}
        onRetry={vi.fn()}
      />
    );

    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Finalizing job")).toBeInTheDocument();
  });

  it("renders completed_with_errors in the completed group", () => {
    renderWithProviders(
      <DownloadJobList
        jobs={[{ ...baseJob, status: "completed_with_errors", title: "Partial gallery" }]}
        filter="all"
        pendingActions={{}}
        onCancel={vi.fn()}
        onRetry={vi.fn()}
      />
    );

    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("Partial gallery")).toBeInTheDocument();
    expect(screen.getByText("Completed with errors")).toBeInTheDocument();
  });
});

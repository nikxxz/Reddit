import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DownloadStatus } from "./DownloadStatus";
import { renderWithProviders } from "../../test/render";

describe("DownloadStatus", () => {
  it("renders finalizing progress text", () => {
    renderWithProviders(
      <DownloadStatus state={{ status: "finalizing", message: "Saving file metadata...", files: [] }} />
    );

    expect(screen.getByText("Saving file metadata...")).toBeInTheDocument();
  });

  it("renders completed_with_errors with a safe persistence warning", () => {
    renderWithProviders(
      <DownloadStatus
        state={{
          status: "completed_with_errors",
          files: [],
          warnings: [
            {
              code: "history_persistence_failed",
              message: "The file downloaded, but its history record could not be saved completely."
            }
          ]
        }}
      />
    );

    expect(screen.getByText("Download completed with errors")).toBeInTheDocument();
    expect(screen.getByText("The file downloaded, but its history record could not be saved completely.")).toBeInTheDocument();
  });

  it("renders application shutdown errors safely", () => {
    renderWithProviders(
      <DownloadStatus
        state={{
          status: "failed",
          errorCode: "application_shutting_down",
          error: "The application is shutting down and cannot start new downloads."
        }}
      />
    );

    expect(screen.getByText("Download failed")).toBeInTheDocument();
    expect(screen.getByText("The application is shutting down and cannot start new downloads.")).toBeInTheDocument();
  });
});

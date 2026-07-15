import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DownloadJobProgress } from "./DownloadJobProgress";
import { renderWithProviders } from "../../test/render";

describe("DownloadJobProgress", () => {
  it("renders partial gallery counts", () => {
    renderWithProviders(
      <DownloadJobProgress
        job={{
          status: "completed_with_errors",
          mediaType: "gallery",
          files: [
            { filename: "one.jpg", status: "completed" },
            { filename: "two.jpg", status: "failed" }
          ]
        }}
      />
    );

    expect(screen.getByText("1 of 2 files downloaded")).toBeInTheDocument();
  });

  it("renders finalizing as metadata saving", () => {
    renderWithProviders(<DownloadJobProgress job={{ status: "finalizing", files: [] }} />);

    expect(screen.getByText("Saving file metadata...")).toBeInTheDocument();
  });
});

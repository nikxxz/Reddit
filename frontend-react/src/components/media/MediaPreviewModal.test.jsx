import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../test/render";
import { MediaPreviewModal } from "./MediaPreviewModal";

vi.mock("../../hooks/useDownloadJob", () => ({
  useDownloadJob: () => ({
    isActive: false,
    state: { status: "idle" },
    start: vi.fn(),
    cancel: vi.fn(),
    reset: vi.fn()
  })
}));

const baseItem = {
  id: "post-1",
  title: "Preview item",
  subreddit: "pics",
  author: "poster",
  permalink: "/r/pics/comments/post_1",
  media_type: "image",
  created_utc: 1784073600
};

describe("MediaPreviewModal", () => {
  it("shows GIF fallback when an MP4-backed GIF fails", async () => {
    renderWithProviders(
      <MediaPreviewModal
        opened
        item={{ ...baseItem, media_type: "gif", media_url: "https://example.com/a.mp4" }}
        onClose={vi.fn()}
      />
    );

    fireEvent.error(document.querySelector(".media-preview-video"));

    expect(await screen.findByText("GIF preview unavailable")).toBeInTheDocument();
  });

  it("shows video fallback when native video fails", async () => {
    renderWithProviders(
      <MediaPreviewModal
        opened
        item={{ ...baseItem, media_type: "video", media_url: "https://example.com/a.mp4" }}
        onClose={vi.fn()}
      />
    );

    fireEvent.error(document.querySelector(".media-preview-video"));

    expect(await screen.findByText("Video preview unavailable")).toBeInTheDocument();
  });

  it("renders external fallback and keeps Open on Reddit available", () => {
    renderWithProviders(
      <MediaPreviewModal
        opened
        item={{ ...baseItem, media_type: "external" }}
        onClose={vi.fn()}
      />
    );

    expect(screen.getAllByText("External preview unavailable").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /Open on Reddit/i })).toBeInTheDocument();
  });

  it("uses modal action layout classes for gallery downloads", () => {
    renderWithProviders(
      <MediaPreviewModal
        opened
        item={{
          ...baseItem,
          media_type: "gallery",
          media_urls: ["https://example.com/1.jpg", "https://example.com/2.jpg"],
          gallery_count: 2
        }}
        onClose={vi.fn()}
      />
    );

    expect(document.querySelector(".media-preview-actions")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download current/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download all 2/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open on Reddit/i })).toBeInTheDocument();
  });
});

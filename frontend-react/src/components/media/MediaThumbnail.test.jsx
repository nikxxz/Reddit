import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MediaThumbnail } from "./MediaThumbnail";
import { renderWithProviders } from "../../test/render";

const item = {
  media_type: "image",
  title: "Example image"
};

describe("MediaThumbnail", () => {
  it("uses local thumbnail endpoints", () => {
    renderWithProviders(<MediaThumbnail item={item} src="/api/library/thumbnails/download-1" />);

    expect(screen.getByAltText("Image preview for Example image")).toHaveAttribute(
      "src",
      "/api/library/thumbnails/download-1"
    );
  });

  it("falls back when the thumbnail fails", () => {
    renderWithProviders(<MediaThumbnail item={item} src="/api/library/thumbnails/download-1" />);

    fireEvent.error(screen.getByAltText("Image preview for Example image"));

    expect(screen.getByText("Preview unavailable")).toBeInTheDocument();
  });
});

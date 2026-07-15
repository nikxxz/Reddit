import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../test/render";
import { MediaCard } from "./MediaCard";

const item = {
  id: "post-1",
  title: "A very long media title that should be styled for clamping in the card",
  subreddit: "pics",
  author: "poster",
  media_type: "image",
  thumbnail_url: "",
  created_utc: 1784073600
};

describe("MediaCard", () => {
  it("renders title, metadata, and fallback preview", () => {
    renderWithProviders(<MediaCard item={item} onOpen={vi.fn()} />);

    expect(screen.getByText(item.title)).toHaveClass("media-card-title");
    expect(screen.getByText("r/pics")).toBeInTheDocument();
    expect(screen.getByText("Image preview unavailable")).toBeInTheDocument();
  });

  it("renders the compact mobile card variant", () => {
    renderWithProviders(<MediaCard compact item={item} onOpen={vi.fn()} />);

    expect(screen.getByRole("button")).toHaveClass("media-card-compact");
  });

  it("opens the preview from the whole card", () => {
    const onOpen = vi.fn();
    renderWithProviders(<MediaCard item={item} onOpen={onOpen} />);

    fireEvent.click(screen.getByRole("button"));

    expect(onOpen).toHaveBeenCalledWith(item);
  });
});

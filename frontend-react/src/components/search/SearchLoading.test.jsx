import { describe, expect, it } from "vitest";
import { renderWithProviders } from "../../test/render";
import { SearchLoading } from "./SearchLoading";

describe("SearchLoading", () => {
  it("renders one responsive skeleton grid for fresh search loading", () => {
    renderWithProviders(<SearchLoading />);

    expect(document.querySelectorAll(".search-loading-grid")).toHaveLength(1);
    expect(document.querySelectorAll(".search-result-skeleton-card")).toHaveLength(8);
  });
});

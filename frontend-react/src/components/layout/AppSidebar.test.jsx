import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppSidebar } from "./AppSidebar";
import { renderWithProviders } from "../../test/render";

const connections = {
  backend: { status: "online" },
  reddit: { status: "checking" }
};

const redditAuth = {
  state: { status: "idle", connected: false, username: "", error: null },
  connect: vi.fn(),
  disconnect: vi.fn(),
  retry: vi.fn()
};

describe("AppSidebar", () => {
  it("renders exactly the four primary navigation items in order", () => {
    renderWithProviders(
      <AppSidebar
        activeDownloadCount={0}
        activeSection="browse"
        connections={connections}
        redditAuth={redditAuth}
        onSelectSection={vi.fn()}
      />
    );

    const nav = screen.getByRole("navigation", { name: "Primary navigation" });
    expect(["Search", "Subreddits / Users", "Downloads", "Settings"].map((label) =>
      within(nav).getByLabelText(label).textContent
    )).toEqual([
      "Search",
      "Subreddits / Users",
      "Downloads",
      "Settings"
    ]);
    expect(within(nav).queryByText("History")).not.toBeInTheDocument();
  });

  it("shows active download count on the downloads item", () => {
    renderWithProviders(
      <AppSidebar
        activeDownloadCount={3}
        activeSection="search"
        connections={connections}
        redditAuth={redditAuth}
        onSelectSection={vi.fn()}
      />
    );

    expect(screen.getByLabelText("Downloads, 3 active")).toBeInTheDocument();
    expect(screen.getByLabelText("3 active downloads")).toBeInTheDocument();
  });
});

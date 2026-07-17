import { screen } from "@testing-library/react";
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
  it("renders the Universal Search navigation item", () => {
    renderWithProviders(
      <AppSidebar
        activeDownloadCount={0}
        activeSection="search"
        connections={connections}
        redditAuth={redditAuth}
        onSelectSection={vi.fn()}
      />
    );

    expect(screen.getByText("Universal Search")).toBeInTheDocument();
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

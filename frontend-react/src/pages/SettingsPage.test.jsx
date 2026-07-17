import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearPinterestSession,
  importPinterestSession,
  listUniversalProviders,
  testPinterestSession
} from "../api/universalSearchApi";
import { renderWithProviders } from "../test/render";
import { SettingsPage } from "./SettingsPage";

vi.mock("../api/universalSearchApi", () => ({
  listUniversalProviders: vi.fn(),
  importPinterestSession: vi.fn(),
  testPinterestSession: vi.fn(),
  clearPinterestSession: vi.fn()
}));

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listUniversalProviders.mockResolvedValue({
      providers: [
        {
          name: "pinterest",
          display_name: "Pinterest",
          implementation_status: "available",
          health: "session_required",
          authenticated: false,
          capabilities: { keyword_search: true },
          rate_limit: { extractor_version: "1.27.7", session_configured: false }
        }
      ]
    });
    importPinterestSession.mockResolvedValue({ configured: true, valid: true, health: "ready" });
    testPinterestSession.mockResolvedValue({ configured: true, valid: true, health: "ready" });
    clearPinterestSession.mockResolvedValue({ configured: false, valid: null, health: "session_required" });
  });

  it("renders Pinterest source controls without raw cookie paths", async () => {
    renderWithProviders(<SettingsPage />);

    expect(await screen.findByText("Pinterest source")).toBeInTheDocument();
    expect(screen.getByText("gallery-dl 1.27.7")).toBeInTheDocument();
    expect(screen.getByText("Session required")).toBeInTheDocument();
    expect(screen.getByLabelText("Import cookies.txt")).toBeInTheDocument();
    expect(screen.queryByText(/app-data/i)).not.toBeInTheDocument();
    expect(document.body.textContent).not.toContain("_auth");
    expect(document.body.textContent).not.toContain("secret");
  });

  it("imports, tests, and clears Pinterest session state", async () => {
    const { container } = renderWithProviders(<SettingsPage />);
    const file = new File(["# Netscape HTTP Cookie File\n.pinterest.com\tTRUE\t/\tTRUE\t1893456000\t_auth\tsecret\n"], "cookies.txt", {
      type: "text/plain"
    });

    await screen.findByLabelText("Import cookies.txt");
    fireEvent.change(container.querySelector('input[type="file"]'), { target: { files: [file] } });
    await waitFor(() => expect(importPinterestSession).toHaveBeenCalledWith(file));
    expect(await screen.findByText("Pinterest cookies imported.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Test session/i }));
    await waitFor(() => expect(testPinterestSession).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Clear session/i }));
    await waitFor(() => expect(clearPinterestSession).toHaveBeenCalled());
  });
});

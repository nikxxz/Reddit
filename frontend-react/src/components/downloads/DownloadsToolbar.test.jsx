import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DownloadsToolbar } from "./DownloadsToolbar";
import { renderWithProviders } from "../../test/render";

function renderToolbar(props = {}) {
  return renderWithProviders(
    <DownloadsToolbar
      filter="all"
      terminalJobCount={1}
      failedJobCount={1}
      clearPending={false}
      clearFailedPending={false}
      onFilterChange={vi.fn()}
      onClearFinished={vi.fn().mockResolvedValue({ removed: 1 })}
      onClearFailed={vi.fn().mockResolvedValue({ removed: 1 })}
      {...props}
    />
  );
}

describe("DownloadsToolbar", () => {
  it("clears failed records through the failed-only action", async () => {
    const onClearFailed = vi.fn().mockResolvedValue({ removed: 1 });
    renderToolbar({ onClearFailed });

    fireEvent.click(screen.getByText("Clear failed"));
    expect(await screen.findByText("Clear failed download records?")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Clear records"));

    expect(onClearFailed).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("Clear failed")).toBeInTheDocument();
  });

  it("disables failed clearing when there are no failed jobs", () => {
    renderToolbar({ failedJobCount: 0 });

    expect(screen.getByText("Clear failed").closest("button")).toBeDisabled();
  });
});

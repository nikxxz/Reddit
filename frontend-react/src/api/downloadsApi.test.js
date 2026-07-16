import { afterEach, describe, expect, it, vi } from "vitest";
import { clearDownloads, startDownload } from "./downloadsApi";

describe("downloadsApi", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends force_download when requested", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(JSON.stringify({ job_id: "job-1", status: "queued" }))
    });
    vi.stubGlobal("fetch", fetchMock);

    await startDownload({ post_id: "abc123", force_download: true });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/downloads",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ post_id: "abc123", force_download: true })
      })
    );
  });

  it("sends selected statuses when clearing downloads", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(JSON.stringify({ removed: 1 }))
    });
    vi.stubGlobal("fetch", fetchMock);

    await clearDownloads(["failed"]);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/downloads/clear",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ statuses: ["failed"] })
      })
    );
  });
});

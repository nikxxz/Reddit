import { afterEach, describe, expect, it, vi } from "vitest";
import { startDownload } from "./downloadsApi";

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
});

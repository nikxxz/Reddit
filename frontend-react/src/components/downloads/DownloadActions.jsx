import { Button, Group, Stack } from "@mantine/core";
import { IconDownload, IconPlayerStop } from "@tabler/icons-react";
import { DownloadStatus } from "./DownloadStatus";

const TERMINAL_STATUSES = new Set(["completed", "completed_with_errors", "failed", "cancelled"]);

export function DownloadActions({
  item,
  downloadJob,
  createPayload
}) {
  const isGallery = item?.media_type === "gallery";
  const isActive = downloadJob.isActive;
  const canRetry = downloadJob.state.status === "failed";

  const startSingle = () => {
    downloadJob.start(createPayload(isGallery ? "gallery_current" : "single"));
  };

  const startAll = () => {
    downloadJob.start(createPayload("gallery_all"));
  };

  return (
    <Stack gap="sm">
      <Group gap="sm">
        <Button
          leftSection={<IconDownload size={16} stroke={1.8} />}
          disabled={isActive}
          onClick={startSingle}
        >
          {canRetry ? "Retry" : isGallery ? "Download current" : "Download"}
        </Button>
        {isGallery ? (
          <Button
            variant="light"
            disabled={isActive}
            onClick={startAll}
          >
            Download all {item.gallery_count || item.media_urls?.length || ""}
          </Button>
        ) : null}
        {isActive ? (
          <Button
            color="red"
            variant="light"
            leftSection={<IconPlayerStop size={16} stroke={1.8} />}
            onClick={downloadJob.cancel}
          >
            Cancel
          </Button>
        ) : null}
      </Group>
      {(downloadJob.state.status !== "idle" || TERMINAL_STATUSES.has(downloadJob.state.status)) ? (
        <DownloadStatus state={downloadJob.state} />
      ) : null}
    </Stack>
  );
}

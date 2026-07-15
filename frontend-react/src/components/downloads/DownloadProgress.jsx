import { Loader, Progress, Text } from "@mantine/core";

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) {
    return null;
  }

  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DownloadProgress({ status }) {
  if (status.progress !== null && status.progress !== undefined) {
    return (
      <>
        <Progress value={status.progress} aria-label="Download progress" />
        <Text size="xs" c="gray.6">
          {status.progress}%
        </Text>
      </>
    );
  }

  return (
    <Text size="xs" c="gray.6">
      <Loader size="xs" mr={6} />
      {formatBytes(status.bytesDownloaded) || "Working..."}
    </Text>
  );
}

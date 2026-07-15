import { Alert, Stack, Text } from "@mantine/core";
import { IconAlertCircle, IconCircleCheck } from "@tabler/icons-react";
import { DownloadProgress } from "./DownloadProgress";
import { DownloadResult } from "./DownloadResult";

const STATUS_MESSAGES = {
  queued: "Queued...",
  resolving: "Preparing media...",
  downloading: "Downloading...",
  merging: "Merging audio and video...",
  completed: "Download completed",
  failed: "Download failed",
  cancelled: "Download cancelled"
};

export function DownloadStatus({ state }) {
  if (state.status === "idle") {
    return null;
  }

  if (state.status === "failed") {
    return (
      <Alert color="red" icon={<IconAlertCircle size={16} />} role="alert" variant="light">
        <Stack gap={4}>
          <Text fw={700}>Download failed</Text>
          <Text size="sm">{state.error || "The selected media could not be downloaded."}</Text>
        </Stack>
      </Alert>
    );
  }

  if (state.status === "completed") {
    return (
      <Alert color="green" icon={<IconCircleCheck size={16} />} variant="light">
        <Stack gap={6}>
          <Text fw={700}>Download completed</Text>
          <DownloadResult files={state.files} />
        </Stack>
      </Alert>
    );
  }

  if (state.status === "cancelled") {
    return (
      <Alert color="gray" variant="light">
        Download cancelled
      </Alert>
    );
  }

  return (
    <Stack gap={6} aria-live="polite">
      <Text size="sm" fw={700}>
        {state.message || STATUS_MESSAGES[state.status] || "Working..."}
      </Text>
      <DownloadProgress status={state} />
    </Stack>
  );
}

import { Alert, Stack, Text } from "@mantine/core";
import { IconAlertCircle, IconCircleCheck } from "@tabler/icons-react";
import { DownloadProgress } from "./DownloadProgress";
import { DownloadResult } from "./DownloadResult";

const STATUS_MESSAGES = {
  queued: "Queued...",
  resolving: "Preparing media...",
  downloading: "Downloading...",
  merging: "Merging audio and video...",
  finalizing: "Saving file metadata...",
  completed: "Download completed",
  completed_with_errors: "Download completed with errors",
  failed: "Download failed",
  cancelled: "Download cancelled"
};

const WARNING_MESSAGES = {
  history_persistence_failed: "The file downloaded, but its history record could not be saved completely."
};

const ERROR_MESSAGES = {
  missing_media_url: "The original media URL is unavailable.",
  missing_post_url: "The Reddit post URL is unavailable.",
  missing_gallery_urls: "Gallery media could not be loaded.",
  invalid_gallery_index: "The selected gallery item is no longer available.",
  missing_cached_item: "The selected post is no longer available. Search for it again.",
  unsupported_media_type: "This media type is not supported for downloading.",
  unsupported_download_strategy: "This media cannot currently be downloaded.",
  unsafe_url: "The media URL was rejected for safety reasons.",
  unsupported_host: "Downloads from this media host are not supported.",
  invalid_url: "The media URL is invalid.",
  hydration_failed: "Reddit could not provide full media details for this post.",
  hydration_returned_no_media: "No downloadable media was found in this post.",
  external_media_unsupported: "This external media provider is not supported.",
  reddit_video_metadata_missing: "Reddit video details were incomplete."
};

function safeErrorMessage(state) {
  if (state.errorCode && ERROR_MESSAGES[state.errorCode]) {
    return ERROR_MESSAGES[state.errorCode];
  }
  if (state.error && !/traceback|exception|https?:\/\//i.test(state.error)) {
    return state.error;
  }
  return "Selected media could not be resolved.";
}

export function DownloadStatus({ state }) {
  if (state.status === "idle") {
    return null;
  }

  if (state.status === "failed") {
    return (
      <Alert color="red" icon={<IconAlertCircle size={16} />} role="alert" variant="light">
        <Stack gap={4}>
          <Text fw={700}>Download failed</Text>
          <Text size="sm">{safeErrorMessage(state)}</Text>
          {state.errorCode ? <Text size="xs" c="red.7">Error code: {state.errorCode}</Text> : null}
        </Stack>
      </Alert>
    );
  }

  if (state.status === "completed" || state.status === "completed_with_errors") {
    return (
      <Alert color={state.status === "completed_with_errors" ? "yellow" : "green"} icon={<IconCircleCheck size={16} />} variant="light">
        <Stack gap={6}>
          <Text fw={700}>{state.status === "completed_with_errors" ? "Download completed with errors" : "Download completed"}</Text>
          {state.warnings?.map((warning) => (
            <Text key={warning.code} size="sm">
              {WARNING_MESSAGES[warning.code] || warning.message || "The download completed with a warning."}
            </Text>
          ))}
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

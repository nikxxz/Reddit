import { Collapse, Group, Image, Paper, Stack, Text, ThemeIcon, UnstyledButton } from "@mantine/core";
import { IconFile, IconPhoto } from "@tabler/icons-react";
import { useState } from "react";
import { DownloadJobActions } from "./DownloadJobActions";
import { DownloadJobProgress } from "./DownloadJobProgress";
import { DownloadStatusBadge } from "./DownloadStatusBadge";

const MEDIA_LABELS = {
  image: "Image",
  video: "Video",
  gif: "GIF",
  gallery: "Gallery",
  external: "External"
};

function formatTime(value) {
  if (!value) {
    return null;
  }

  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

function completedFiles(files) {
  return files.filter((file) => file.status === "completed");
}

function failedFiles(files) {
  return files.filter((file) => file.status === "failed");
}

export function DownloadJobCard({
  job,
  pendingActions,
  onCancel,
  onRetry
}) {
  const [filesOpen, setFilesOpen] = useState(false);
  const completed = completedFiles(job.files);
  const failed = failedFiles(job.files);
  const displayTitle =
    job.title ||
    completed[0]?.filename ||
    `${MEDIA_LABELS[job.mediaType] || "Media"} download`;
  const timestamp = formatTime(job.completedAt || job.startedAt || job.createdAt);
  const meta = [
    job.subreddit ? `r/${job.subreddit}` : null,
    job.author ? `u/${job.author}` : null,
    MEDIA_LABELS[job.mediaType] || "Media",
    timestamp
  ].filter(Boolean);

  return (
    <Paper className="download-job-card" withBorder p="md">
      <div className="download-job-card-grid">
        <div className="download-job-thumb" aria-hidden="true">
          {job.thumbnailUrl ? (
            <Image src={job.thumbnailUrl} alt="" fit="cover" />
          ) : (
            <ThemeIcon variant="light" size="xl">
              <IconPhoto size={22} stroke={1.8} />
            </ThemeIcon>
          )}
        </div>

        <Stack className="download-job-main" gap={8}>
          <Group justify="space-between" gap="xs" align="flex-start">
            <Stack gap={3} className="download-job-title-group">
              <Text fw={700} lineClamp={2}>
                {displayTitle}
              </Text>
              <Text size="sm" c="gray.6">
                {meta.join(" - ")}
              </Text>
            </Stack>
            <DownloadStatusBadge status={job.status} />
          </Group>

          {job.message ? (
            <Text size="sm" c={job.status === "failed" ? "red.7" : "gray.7"} role={job.status === "failed" ? "alert" : undefined}>
              {job.error || job.message}
              {job.errorCode ? ` (${job.errorCode})` : ""}
            </Text>
          ) : null}

          <DownloadJobProgress job={job} />

          {job.files.length ? (
            <Stack gap={6}>
              <Text size="sm" c="gray.7">
                {job.mediaType === "gallery"
                  ? `${completed.length} of ${job.files.length} files completed${failed.length ? `, ${failed.length} failed` : ""}`
                  : completed.map((file) => file.filename).filter(Boolean).join(", ")}
              </Text>
              {job.files.length > 1 ? (
                <>
                  <UnstyledButton
                    className="download-files-toggle"
                    onClick={() => setFilesOpen((open) => !open)}
                  >
                    {filesOpen ? "Hide files" : "Show files"}
                  </UnstyledButton>
                  <Collapse in={filesOpen}>
                    <Stack gap={4}>
                      {job.files.map((file, index) => (
                        <Group key={`${file.filename || index}-${file.status}`} gap="xs" wrap="nowrap">
                          <IconFile size={14} stroke={1.8} />
                          <Text size="xs" c={file.status === "failed" ? "red.7" : "gray.7"} lineClamp={1}>
                            {file.filename || `Item ${file.index || index + 1}`} - {file.status}
                          </Text>
                        </Group>
                      ))}
                    </Stack>
                  </Collapse>
                </>
              ) : null}
            </Stack>
          ) : null}
        </Stack>

        <DownloadJobActions
          job={job}
          pendingActions={pendingActions}
          onCancel={onCancel}
          onRetry={onRetry}
        />
      </div>
    </Paper>
  );
}

import { ActionIcon, Button, Group, Paper, Progress, Stack, Text } from "@mantine/core";
import { IconChevronDown, IconChevronUp, IconDownload } from "@tabler/icons-react";
import { useState } from "react";

const ACTIVE_STATUSES = new Set(["queued", "resolving", "downloading", "merging", "finalizing"]);

function getProgress(job) {
  if (typeof job.progress === "number") {
    return Math.max(0, Math.min(100, job.progress));
  }

  if (job.mediaType === "gallery" && job.files?.length) {
    const completed = job.files.filter((file) => file.status === "completed").length;
    return Math.round((completed / job.files.length) * 100);
  }

  return job.status === "queued" ? 4 : 18;
}

export function DownloadTray({ jobs, onOpenDownloads }) {
  const [expanded, setExpanded] = useState(false);
  const activeJobs = jobs.filter((job) => ACTIVE_STATUSES.has(job.status));

  if (!activeJobs.length) {
    return null;
  }

  const visibleJobs = expanded ? activeJobs.slice(0, 3) : activeJobs.slice(0, 1);

  return (
    <Paper className="download-tray" role="status" aria-live="polite">
      <Group justify="space-between" gap="sm" wrap="nowrap">
        <Group gap="xs" wrap="nowrap" miw={0}>
          <IconDownload size={18} stroke={1.9} />
          <Stack gap={0} miw={0}>
            <Text size="sm" fw={750} truncate>
              {activeJobs.length} active download{activeJobs.length === 1 ? "" : "s"}
            </Text>
            <Text size="xs" c="gray.5" truncate>
              {activeJobs[0].title || activeJobs[0].message || activeJobs[0].status}
            </Text>
          </Stack>
        </Group>
        <Group gap={4} wrap="nowrap">
          <ActionIcon
            aria-label={expanded ? "Collapse download tray" : "Expand download tray"}
            className="download-tray-icon-button"
            variant="subtle"
            onClick={() => setExpanded((open) => !open)}
          >
            {expanded ? <IconChevronDown size={16} /> : <IconChevronUp size={16} />}
          </ActionIcon>
          <Button size="xs" variant="light" onClick={onOpenDownloads}>
            View
          </Button>
        </Group>
      </Group>

      <Stack gap="xs" mt="sm">
        {visibleJobs.map((job) => (
          <Stack key={job.jobId} gap={4}>
            {expanded ? (
              <Text size="xs" c="gray.4" truncate>
                {job.title || job.message || job.status}
              </Text>
            ) : null}
            <Progress
              aria-label={`Download progress for ${job.title || job.jobId}`}
              className="download-tray-progress"
              value={getProgress(job)}
            />
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}

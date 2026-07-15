import { Button, Group } from "@mantine/core";
import { IconRefresh, IconX } from "@tabler/icons-react";

export function DownloadJobActions({
  job,
  pendingActions,
  onCancel,
  onRetry
}) {
  const cancelPending = Boolean(pendingActions[`cancel:${job.jobId}`]);
  const retryPending = Boolean(pendingActions[`retry:${job.jobId}`]);

  if (!job.cancellable && !job.retryable) {
    return null;
  }

  return (
    <Group className="download-job-actions" gap="xs" justify="flex-end">
      {job.cancellable ? (
        <Button
          color="red"
          variant="light"
          size="xs"
          leftSection={<IconX size={14} stroke={1.8} />}
          loading={cancelPending}
          disabled={cancelPending}
          onClick={() => onCancel(job.jobId)}
        >
          Cancel
        </Button>
      ) : null}
      {job.retryable ? (
        <Button
          variant="light"
          size="xs"
          leftSection={<IconRefresh size={14} stroke={1.8} />}
          loading={retryPending}
          disabled={retryPending}
          onClick={() => onRetry(job.jobId)}
        >
          Retry
        </Button>
      ) : null}
    </Group>
  );
}

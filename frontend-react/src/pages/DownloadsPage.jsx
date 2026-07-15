import { Alert, Button, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { IconAlertCircle, IconRefresh } from "@tabler/icons-react";
import { useState } from "react";
import { DownloadJobList } from "../components/downloads/DownloadJobList";
import { DownloadsToolbar } from "../components/downloads/DownloadsToolbar";
import { useDownloads } from "../hooks/useDownloads";
import "../styles/downloads-page.css";

export function DownloadsPage() {
  const [filter, setFilter] = useState("all");
  const {
    jobs,
    loading,
    error,
    actionError,
    pendingActions,
    terminalJobCount,
    refreshJobs,
    cancelJob,
    retryJob,
    clearFinished
  } = useDownloads();

  return (
    <Stack className="downloads-page" gap="md">
      <Group justify="space-between" align="flex-start" gap="sm">
        <Stack gap={3}>
          <Title order={2} size="h3">
            Downloads
          </Title>
          <Text size="sm" c="gray.6">
            Active jobs and persistent local download history.
          </Text>
        </Stack>
        {loading ? (
          <Group gap="xs">
            <Loader size="xs" />
            <Text size="sm" c="gray.6">Loading</Text>
          </Group>
        ) : null}
      </Group>

      <DownloadsToolbar
        filter={filter}
        terminalJobCount={terminalJobCount}
        clearPending={Boolean(pendingActions.clear)}
        onFilterChange={setFilter}
        onClearFinished={clearFinished}
      />

      {error ? (
        <Alert color="red" icon={<IconAlertCircle size={16} />} role="alert" variant="light">
          <Group justify="space-between" gap="sm">
            <Text>{error}</Text>
            <Button
              size="xs"
              variant="light"
              leftSection={<IconRefresh size={14} stroke={1.8} />}
              onClick={() => refreshJobs()}
            >
              Try Again
            </Button>
          </Group>
        </Alert>
      ) : null}

      {actionError ? (
        <Alert color="red" role="alert" variant="light">
          {actionError}
        </Alert>
      ) : null}

      <DownloadJobList
        jobs={jobs}
        filter={filter}
        pendingActions={pendingActions}
        onCancel={cancelJob}
        onRetry={retryJob}
      />
    </Stack>
  );
}

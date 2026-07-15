import { Stack, Text } from "@mantine/core";
import { DownloadJobCard } from "./DownloadJobCard";
import { DownloadsEmptyState } from "./DownloadsEmptyState";

const GROUPS = [
  { key: "active", label: "Active", statuses: ["resolving", "downloading", "merging"] },
  { key: "queued", label: "Queued", statuses: ["queued"] },
  { key: "failed", label: "Failed", statuses: ["failed"] },
  { key: "completed", label: "Completed", statuses: ["completed"] },
  { key: "cancelled", label: "Cancelled", statuses: ["cancelled"] }
];

function matchesFilter(job, filter) {
  if (filter === "all") {
    return true;
  }
  if (filter === "active") {
    return GROUPS[0].statuses.includes(job.status);
  }
  return job.status === filter;
}

export function DownloadJobList({
  jobs,
  filter,
  pendingActions,
  onCancel,
  onRetry
}) {
  const visibleJobs = jobs.filter((job) => matchesFilter(job, filter));

  if (!visibleJobs.length) {
    return <DownloadsEmptyState filter={filter} />;
  }

  if (filter !== "all") {
    return (
      <Stack gap="sm">
        {visibleJobs.map((job) => (
          <DownloadJobCard
            key={job.jobId}
            job={job}
            pendingActions={pendingActions}
            onCancel={onCancel}
            onRetry={onRetry}
          />
        ))}
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      {GROUPS.map((group) => {
        const groupJobs = visibleJobs.filter((job) => group.statuses.includes(job.status));
        if (!groupJobs.length) {
          return null;
        }

        return (
          <Stack key={group.key} gap="sm">
            <Text className="downloads-section-title" size="xs" fw={800} c="gray.6" tt="uppercase">
              {group.label}
            </Text>
            {groupJobs.map((job) => (
              <DownloadJobCard
                key={job.jobId}
                job={job}
                pendingActions={pendingActions}
                onCancel={onCancel}
                onRetry={onRetry}
              />
            ))}
          </Stack>
        );
      })}
    </Stack>
  );
}

import { Group, Loader, Progress, Text } from "@mantine/core";

function completedFileCount(files) {
  return files.filter((file) => file.status === "completed").length;
}

export function DownloadJobProgress({ job }) {
  if (job.status === "merging") {
    return <Text size="sm">Merging audio and video</Text>;
  }

  if (job.mediaType === "gallery" && job.files.length > 0) {
    return (
      <Text size="sm">
        {completedFileCount(job.files)} / {job.files.length} files
      </Text>
    );
  }

  if (job.progress !== null && job.progress !== undefined) {
    return (
      <div className="download-job-progress">
        <Progress value={job.progress} aria-label={`Download progress for ${job.title || job.jobId}`} />
        <Text size="xs" c="gray.6">
          {job.progress}%
        </Text>
      </div>
    );
  }

  if (["queued", "resolving", "downloading"].includes(job.status)) {
    return (
      <Group gap="xs">
        <Loader size="xs" />
        <Text size="sm">{job.message || "Working..."}</Text>
      </Group>
    );
  }

  return null;
}

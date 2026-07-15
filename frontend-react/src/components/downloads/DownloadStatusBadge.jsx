import { Badge } from "@mantine/core";

const STATUS_COLORS = {
  queued: "gray",
  resolving: "blue",
  downloading: "blue",
  merging: "violet",
  finalizing: "violet",
  completed: "green",
  completed_with_errors: "yellow",
  failed: "red",
  cancelled: "gray"
};

const STATUS_LABELS = {
  queued: "Queued",
  resolving: "Preparing",
  downloading: "Downloading",
  merging: "Merging",
  finalizing: "Finalizing",
  completed: "Completed",
  completed_with_errors: "Completed with errors",
  failed: "Failed",
  cancelled: "Cancelled"
};

export function DownloadStatusBadge({ status }) {
  return (
    <Badge color={STATUS_COLORS[status] || "gray"} variant="light">
      {STATUS_LABELS[status] || "Unknown"}
    </Badge>
  );
}

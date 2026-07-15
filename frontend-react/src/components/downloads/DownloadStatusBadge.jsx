import { Badge } from "@mantine/core";

const STATUS_COLORS = {
  queued: "gray",
  resolving: "blue",
  downloading: "blue",
  merging: "violet",
  completed: "green",
  failed: "red",
  cancelled: "gray"
};

const STATUS_LABELS = {
  queued: "Queued",
  resolving: "Preparing",
  downloading: "Downloading",
  merging: "Merging",
  completed: "Completed",
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

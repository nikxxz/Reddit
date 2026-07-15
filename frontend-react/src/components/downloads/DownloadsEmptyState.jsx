import { Paper, Stack, Text } from "@mantine/core";

export function DownloadsEmptyState({ filter }) {
  const label = filter === "all" ? "downloads" : `${filter} downloads`;

  return (
    <Paper className="downloads-empty-state" withBorder p="lg">
      <Stack gap={4}>
        <Text fw={700}>{filter === "all" ? "No downloads yet" : `No ${label}`}</Text>
        <Text size="sm" c="gray.6">
          {filter === "all"
            ? "Start a download from a media preview."
            : "Try another download status filter."}
        </Text>
      </Stack>
    </Paper>
  );
}

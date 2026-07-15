import { Button, Group, Stack, Text } from "@mantine/core";
import { StatusDot } from "../common/StatusDot";

const STATUS_LABELS = {
  checking: "Checking",
  online: "Online",
  failed: "Failed"
};

function ConnectionRow({ label, status }) {
  return (
    <Group gap="sm" wrap="nowrap">
      <Text size="sm" c="gray.7" w={92}>
        {label}
      </Text>
      <Group gap="xs" wrap="nowrap">
        <StatusDot status={status} />
        <Text size="sm" fw={600} c="gray.8">
          {STATUS_LABELS[status] ?? STATUS_LABELS.checking}
        </Text>
      </Group>
    </Group>
  );
}

export function ConnectionSummary({
  connections,
  showRetry = false,
  isChecking = false,
  onRetryConnections
}) {
  return (
    <Stack gap="xs">
      <ConnectionRow label="Backend API" status={connections.backend.status} />
      <ConnectionRow label="Reddit API" status={connections.reddit.status} />
      {showRetry ? (
        <Button
          fullWidth
          variant="light"
          size="xs"
          mt="xs"
          onClick={onRetryConnections}
          loading={isChecking}
        >
          Retry Connections
        </Button>
      ) : null}
    </Stack>
  );
}

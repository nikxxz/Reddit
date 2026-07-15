import { Button, Group, Stack, Text, Tooltip } from "@mantine/core";
import { StatusDot } from "../common/StatusDot";

const STATUS_LABELS = {
  checking: "Checking",
  online: "Online",
  failed: "Failed"
};

function ConnectionRow({ label, status, collapsed = false }) {
  const statusLabel = STATUS_LABELS[status] ?? STATUS_LABELS.checking;

  if (collapsed) {
    return (
      <Tooltip label={`${label}: ${statusLabel}`} position="right">
        <span className="connection-summary-collapsed-dot" aria-label={`${label}: ${statusLabel}`}>
          <StatusDot status={status} />
        </span>
      </Tooltip>
    );
  }

  return (
    <Group gap="sm" wrap="nowrap">
      <Text size="sm" c="gray.7" w={92}>
        {label}
      </Text>
      <Group gap="xs" wrap="nowrap">
        <StatusDot status={status} />
        <Text size="sm" fw={600} c="gray.8">
          {statusLabel}
        </Text>
      </Group>
    </Group>
  );
}

export function ConnectionSummary({
  connections,
  collapsed = false,
  showRetry = false,
  isChecking = false,
  onRetryConnections
}) {
  return (
    <Stack gap="xs" align={collapsed ? "center" : "stretch"}>
      <ConnectionRow
        collapsed={collapsed}
        label="Backend API"
        status={connections.backend.status}
      />
      <ConnectionRow
        collapsed={collapsed}
        label="Reddit API"
        status={connections.reddit.status}
      />
      {showRetry && !collapsed ? (
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

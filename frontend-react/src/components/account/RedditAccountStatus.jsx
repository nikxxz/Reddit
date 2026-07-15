import { Group, Loader, Text, ThemeIcon, Tooltip } from "@mantine/core";
import {
  IconBrandReddit,
  IconPlugConnected,
  IconPlugConnectedX
} from "@tabler/icons-react";

function getStatusCopy({ status, connected, username }) {
  if (status === "checking") {
    return "Checking Reddit account...";
  }

  if (status === "connecting") {
    return "Connecting to Reddit...";
  }

  if (status === "disconnecting") {
    return "Disconnecting Reddit account...";
  }

  if (connected && username) {
    return `Connected to u/${username}`;
  }

  if (status === "error") {
    return "Reddit account status needs attention.";
  }

  return "Not connected";
}

export function RedditAccountStatus({
  collapsed = false,
  status,
  connected,
  username
}) {
  const copy = getStatusCopy({ status, connected, username });
  const isBusy =
    status === "checking" || status === "connecting" || status === "disconnecting";

  if (collapsed) {
    return (
      <Tooltip label={copy} position="right">
        <ThemeIcon
          aria-label={copy}
          color={connected ? "green" : status === "error" ? "red" : "gray"}
          radius="xl"
          size="md"
          variant={connected ? "light" : "subtle"}
        >
          <IconBrandReddit size={17} stroke={1.9} />
        </ThemeIcon>
      </Tooltip>
    );
  }

  return (
    <Group gap="xs" wrap="nowrap" aria-live="polite">
      <ThemeIcon
        color={connected ? "green" : status === "error" ? "red" : "gray"}
        radius="xl"
        size="sm"
        variant="light"
      >
        {isBusy ? (
          <Loader size={12} />
        ) : connected ? (
          <IconPlugConnected size={14} stroke={2} />
        ) : (
          <IconPlugConnectedX size={14} stroke={2} />
        )}
      </ThemeIcon>
      <Text
        className="reddit-account-status-text"
        size="sm"
        c={connected ? "gray.8" : "gray.7"}
        fw={connected ? 600 : 400}
        title={copy}
      >
        {copy}
      </Text>
    </Group>
  );
}

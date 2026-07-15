import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconAlertCircle } from "@tabler/icons-react";
import { RedditAccountStatus } from "./RedditAccountStatus";
import { RedditConnectButton } from "./RedditConnectButton";
import { RedditDisconnectButton } from "./RedditDisconnectButton";

export function RedditAccountSection({
  collapsed = false,
  status,
  connected,
  username,
  error,
  onConnect,
  onDisconnect,
  onRetry
}) {
  const [confirmOpened, { open: openConfirm, close: closeConfirm }] =
    useDisclosure(false);

  const handleConfirmDisconnect = async () => {
    closeConfirm();
    await onDisconnect();
  };

  if (collapsed) {
    return (
      <div className="reddit-account-section reddit-account-section-collapsed">
        <RedditAccountStatus
          collapsed
          status={status}
          connected={connected}
          username={username}
        />
      </div>
    );
  }

  return (
    <Stack className="reddit-account-section" gap="xs">
      <Text size="xs" fw={700} c="gray.6" tt="uppercase">
        Reddit Account
      </Text>

      <RedditAccountStatus
        status={status}
        connected={connected}
        username={username}
      />

      {connected && username ? (
        <Stack gap={2}>
          <Text size="xs" c="gray.6">
            Connected to
          </Text>
          <Text
            className="reddit-account-username"
            size="sm"
            fw={700}
            title={`u/${username}`}
          >
            u/{username}
          </Text>
        </Stack>
      ) : (
        <Text size="xs" c="gray.6">
          Search uses anonymous access until an account is connected.
        </Text>
      )}

      {error ? (
        <Alert
          className="reddit-account-error"
          color="red"
          icon={<IconAlertCircle size={15} />}
          role="alert"
          variant="light"
        >
          <Stack gap={6}>
            <Text size="xs">{error}</Text>
            {status === "error" ? (
              <Button size="compact-xs" variant="subtle" onClick={onRetry}>
                Retry
              </Button>
            ) : null}
          </Stack>
        </Alert>
      ) : null}

      {connected ? (
        <RedditDisconnectButton status={status} onClick={openConfirm} />
      ) : (
        <RedditConnectButton status={status} onConnect={onConnect} />
      )}

      <Modal
        centered
        opened={confirmOpened}
        title="Disconnect Reddit account?"
        onClose={closeConfirm}
      >
        <Stack gap="md">
          <Text size="sm">
            Your local Reddit authorization will be removed. Anonymous Reddit
            access will remain available.
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="default" onClick={closeConfirm}>
              Cancel
            </Button>
            <Button color="red" onClick={handleConfirmDisconnect}>
              Disconnect
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

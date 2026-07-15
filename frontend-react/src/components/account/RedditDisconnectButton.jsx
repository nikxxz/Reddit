import { Button } from "@mantine/core";
import { IconLogout } from "@tabler/icons-react";

export function RedditDisconnectButton({ status, onClick }) {
  const isDisconnecting = status === "disconnecting";

  return (
    <Button
      fullWidth
      color="red"
      size="xs"
      type="button"
      variant="light"
      leftSection={<IconLogout size={15} stroke={1.9} />}
      loading={isDisconnecting}
      disabled={isDisconnecting}
      onClick={onClick}
    >
      {isDisconnecting ? "Disconnecting..." : "Disconnect"}
    </Button>
  );
}

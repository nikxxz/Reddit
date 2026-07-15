import { Button } from "@mantine/core";
import { IconLogin } from "@tabler/icons-react";

export function RedditConnectButton({ status, onConnect }) {
  const isConnecting = status === "connecting";

  return (
    <Button
      fullWidth
      size="xs"
      type="button"
      leftSection={<IconLogin size={15} stroke={1.9} />}
      loading={isConnecting}
      disabled={status === "checking"}
      onClick={onConnect}
    >
      {isConnecting ? "Connecting..." : "Connect Reddit"}
    </Button>
  );
}

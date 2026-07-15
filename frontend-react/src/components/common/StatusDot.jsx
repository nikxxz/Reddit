import { Box } from "@mantine/core";

const STATUS_COLORS = {
  checking: "yellow.6",
  online: "green.6",
  failed: "red.6"
};

export function StatusDot({ status }) {
  return (
    <Box
      className={status === "checking" ? "status-dot-pulse" : undefined}
      component="span"
      aria-hidden="true"
      bg={STATUS_COLORS[status] ?? STATUS_COLORS.checking}
      style={{
        width: 9,
        height: 9,
        borderRadius: 999,
        flex: "0 0 9px"
      }}
    />
  );
}

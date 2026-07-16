import { Button, Group, Modal, Select, SegmentedControl, Stack, Text } from "@mantine/core";
import { IconAlertTriangle, IconTrash } from "@tabler/icons-react";
import { useState } from "react";

const FILTERS = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "queued", label: "Queued" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" }
];

export function DownloadsToolbar({
  filter,
  terminalJobCount,
  failedJobCount,
  clearPending,
  clearFailedPending,
  onFilterChange,
  onClearFinished,
  onClearFailed
}) {
  const [confirmMode, setConfirmMode] = useState(null);
  const confirmOpen = Boolean(confirmMode);
  const isFailedMode = confirmMode === "failed";
  const confirmTitle = isFailedMode ? "Clear failed download records?" : "Clear finished download records?";
  const confirmAction = isFailedMode ? onClearFailed : onClearFinished;
  const confirmPending = isFailedMode ? clearFailedPending : clearPending;

  const handleClear = async () => {
    const result = await confirmAction();
    if (result) {
      setConfirmMode(null);
    }
  };

  return (
    <>
      <Group className="downloads-toolbar" justify="space-between" align="center" gap="sm">
        <SegmentedControl
          className="downloads-filter-tabs"
          aria-label="Filter downloads by status"
          value={filter}
          onChange={onFilterChange}
          data={FILTERS}
        />
        <Select
          className="downloads-filter-select"
          aria-label="Filter downloads by status"
          value={filter}
          onChange={(value) => onFilterChange(value || "all")}
          data={FILTERS}
          allowDeselect={false}
        />
        <Button
          variant="light"
          color="yellow"
          leftSection={<IconAlertTriangle size={16} stroke={1.8} />}
          disabled={!failedJobCount}
          onClick={() => setConfirmMode("failed")}
        >
          Clear failed
        </Button>
        <Button
          variant="light"
          color="red"
          leftSection={<IconTrash size={16} stroke={1.8} />}
          disabled={!terminalJobCount}
          onClick={() => setConfirmMode("finished")}
        >
          Clear finished
        </Button>
      </Group>

      <Modal
        opened={confirmOpen}
        onClose={() => setConfirmMode(null)}
        title={confirmTitle}
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            {isFailedMode
              ? "Only failed download records will be removed. Downloaded files will not be deleted."
              : "Downloaded files will not be deleted."}
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirmMode(null)}>
              Cancel
            </Button>
            <Button color={isFailedMode ? "yellow" : "red"} loading={confirmPending} onClick={handleClear}>
              Clear records
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

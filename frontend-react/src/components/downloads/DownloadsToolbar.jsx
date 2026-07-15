import { Button, Group, Modal, Select, SegmentedControl, Stack, Text } from "@mantine/core";
import { IconTrash } from "@tabler/icons-react";
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
  clearPending,
  onFilterChange,
  onClearFinished
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleClear = async () => {
    const result = await onClearFinished();
    if (result) {
      setConfirmOpen(false);
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
          color="red"
          leftSection={<IconTrash size={16} stroke={1.8} />}
          disabled={!terminalJobCount}
          onClick={() => setConfirmOpen(true)}
        >
          Clear finished
        </Button>
      </Group>

      <Modal
        opened={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Clear finished download records?"
        centered
      >
        <Stack gap="md">
          <Text size="sm">Downloaded files will not be deleted.</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button color="red" loading={clearPending} onClick={handleClear}>
              Clear records
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

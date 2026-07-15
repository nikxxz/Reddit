import {
  Box,
  Divider,
  Group,
  NavLink,
  Stack,
  Text,
  Title
} from "@mantine/core";
import {
  IconDownload,
  IconHistory,
  IconSearch,
  IconSettings
} from "@tabler/icons-react";
import { ConnectionSummary } from "./ConnectionSummary";

const NAV_ITEMS = [
  { value: "search", label: "Search", icon: IconSearch },
  { value: "downloads", label: "Downloads", icon: IconDownload },
  { value: "history", label: "History", icon: IconHistory },
  { value: "settings", label: "Settings", icon: IconSettings }
];

export function AppSidebar({ activeSection, connections, onSelectSection }) {
  return (
    <Stack h="100%" gap="md" p="md">
      <Box>
        <Title order={2} size="h4" lh={1.15}>
          Reddit Media Downloader
        </Title>
        <Text size="xs" c="gray.6" mt={4}>
          Personal media browser
        </Text>
      </Box>

      <Stack gap={4} component="nav" aria-label="Primary navigation">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.value}
            active={activeSection === item.value}
            label={item.label}
            leftSection={<item.icon size={18} stroke={1.8} />}
            onClick={() => onSelectSection(item.value)}
            variant="light"
          />
        ))}
      </Stack>

      <Box flex={1} />

      <Stack gap="sm">
        <Divider />

        <Stack gap="xs">
          <Text size="xs" fw={700} c="gray.6" tt="uppercase">
            Connections
          </Text>
          <ConnectionSummary connections={connections} />
        </Stack>

        <Divider />

        <Stack gap={6}>
          <Text size="xs" fw={700} c="gray.6" tt="uppercase">
            Account
          </Text>
          <Group gap="xs">
            <Text size="sm" c="gray.7">
              Not connected
            </Text>
          </Group>
        </Stack>
      </Stack>
    </Stack>
  );
}

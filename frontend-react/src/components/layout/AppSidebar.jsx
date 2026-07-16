import {
  Box,
  Badge,
  Divider,
  NavLink,
  Stack,
  Text,
  Tooltip,
  Title
} from "@mantine/core";
import {
  IconCompass,
  IconDownload,
  IconSearch,
  IconSettings
} from "@tabler/icons-react";
import { RedditAccountSection } from "../account/RedditAccountSection";
import { ConnectionSummary } from "./ConnectionSummary";

const NAV_ITEMS = [
  { value: "search", label: "Search", icon: IconSearch },
  { value: "browse", label: "Subreddits / Users", icon: IconCompass },
  { value: "downloads", label: "Downloads", icon: IconDownload },
  { value: "settings", label: "Settings", icon: IconSettings }
];

export function AppSidebar({
  activeDownloadCount = 0,
  activeSection,
  collapsed = false,
  connections,
  onSelectSection,
  redditAuth
}) {
  return (
    <Stack h="100%" gap="md" p={collapsed ? "sm" : "md"}>
      {collapsed ? null : (
        <Box>
          <Title order={2} size="h4" lh={1.15}>
            Reddit Media Downloader
          </Title>
          <Text size="xs" c="gray.6" mt={4}>
            Personal media browser
          </Text>
        </Box>
      )}

      <Stack
        gap={4}
        component="nav"
        aria-label="Primary navigation"
        align={collapsed ? "center" : "stretch"}
      >
        {NAV_ITEMS.map((item) => (
          <Tooltip
            key={item.value}
            disabled={!collapsed}
            label={item.label}
            position="right"
          >
            <NavLink
              active={activeSection === item.value}
              aria-label={
                item.value === "downloads" && activeDownloadCount
                  ? `${item.label}, ${activeDownloadCount} active`
                  : item.label
              }
              className={collapsed ? "sidebar-navlink-collapsed" : undefined}
              label={collapsed ? undefined : item.label}
              leftSection={<item.icon size={18} stroke={1.8} />}
              rightSection={
                item.value === "downloads" && activeDownloadCount ? (
                  <Badge size="xs" variant="filled" aria-label={`${activeDownloadCount} active downloads`}>
                    {activeDownloadCount}
                  </Badge>
                ) : undefined
              }
              onClick={() => onSelectSection(item.value)}
              variant="light"
            />
          </Tooltip>
        ))}
      </Stack>

      <Box flex={1} />

      <Stack gap="sm">
        <Divider />

        <Stack gap="xs">
          {collapsed ? null : (
            <Text size="xs" fw={700} c="gray.6" tt="uppercase">
              Connections
            </Text>
          )}
          <ConnectionSummary collapsed={collapsed} connections={connections} />
        </Stack>

        <Divider />

        <RedditAccountSection
          collapsed={collapsed}
          status={redditAuth.state.status}
          connected={redditAuth.state.connected}
          username={redditAuth.state.username}
          error={redditAuth.state.error}
          onConnect={redditAuth.connect}
          onDisconnect={redditAuth.disconnect}
          onRetry={redditAuth.retry}
        />
      </Stack>
    </Stack>
  );
}

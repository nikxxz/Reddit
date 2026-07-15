import { Burger, Group, Image, Stack, Text, Title } from "@mantine/core";
import redditIcon from "../../../../assets/reddit.png";

export function AppHeader({ opened, onToggle }) {
  return (
    <Group h="100%" px="md" gap="sm" wrap="nowrap">
      <Burger
        opened={opened}
        onClick={onToggle}
        size="sm"
        aria-label={opened ? "Close navigation" : "Open navigation"}
      />
      <Image
        className="app-header-icon"
        src={redditIcon}
        alt=""
        aria-hidden="true"
      />
      <Stack gap={0} miw={0}>
        <Title order={1} size="h3" lh={1.1} className="app-title">
          Reddit Media Downloader
        </Title>
        <Text size="xs" c="gray.6" visibleFrom="xs">
          Personal media browser
        </Text>
      </Stack>
    </Group>
  );
}

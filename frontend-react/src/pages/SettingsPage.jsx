import { Paper, Stack, Text, Title } from "@mantine/core";

export function SettingsPage() {
  return (
    <Paper component="section" withBorder p="lg">
      <Stack gap="xs">
        <Title order={2} size="h3">Settings</Title>
        <Text size="sm" c="gray.6">Settings will be available in a future update.</Text>
      </Stack>
    </Paper>
  );
}

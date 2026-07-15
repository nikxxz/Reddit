import { Button, Paper, Stack, Text, Title } from "@mantine/core";

export function SearchError({ error, onRetry }) {
  return (
    <Paper
      className="search-results-panel"
      component="section"
      role="alert"
      withBorder
      p={{ base: "md", sm: "lg" }}
      radius="md"
    >
      <Stack gap="xs">
        <Title order={3} size="h4">
          Reddit search failed
        </Title>
        <Text size="sm" c="gray.6">
          {error || "Unable to complete Reddit search."}
        </Text>
        <Button className="search-state-action" onClick={onRetry}>
          Try Again
        </Button>
      </Stack>
    </Paper>
  );
}

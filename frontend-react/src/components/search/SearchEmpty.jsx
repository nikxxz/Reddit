import { Button, Paper, Stack, Text, Title } from "@mantine/core";

function getEmptyCopy(state) {
  const message = state.responseMeta?.message || "";

  if (/media/i.test(message) && !/post/i.test(message)) {
    return {
      title: "No matching media",
      body: "Posts were found, but none contained supported media."
    };
  }

  if (state.lastRequest?.mediaType && state.lastRequest.mediaType !== "all") {
    return {
      title: "No media matches the current filters",
      body: "Try another media type, time range, or NSFW setting."
    };
  }

  return {
    title: "No Reddit posts found",
    body: "No posts matched the current search."
  };
}

export function SearchEmpty({ state, onClearFilters }) {
  const copy = getEmptyCopy(state);
  const canClearFilters =
    state.lastRequest?.mediaType !== "all" ||
    state.lastRequest?.sortBy !== "relevance" ||
    state.lastRequest?.timeFilter !== "all" ||
    state.lastRequest?.includeNsfw;

  return (
    <Paper
      className="search-results-panel"
      component="section"
      aria-live="polite"
      withBorder
      p={{ base: "md", sm: "lg" }}
      radius="md"
    >
      <Stack gap="xs">
        <Title order={3} size="h4">
          {copy.title}
        </Title>
        <Text size="sm" c="gray.6">
          {copy.body}
        </Text>
        {canClearFilters ? (
          <Button className="search-state-action" variant="light" onClick={onClearFilters}>
            Clear filters
          </Button>
        ) : null}
      </Stack>
    </Paper>
  );
}

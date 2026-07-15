import { Button, Group, Paper, Stack, Text } from "@mantine/core";

const MEDIA_LABELS = {
  all: "All media",
  images: "Images",
  videos: "Videos",
  gifs: "GIFs",
  gallery: "Gallery"
};

const SORT_LABELS = {
  relevance: "Relevance",
  new: "New",
  top: "Top",
  hot: "Hot"
};

const TIME_LABELS = {
  all: "All time",
  day: "Today",
  week: "This week",
  month: "This month",
  year: "This year"
};

function getSearchSummaryLines(values) {
  const context = [
    values.query?.trim() || null,
    values.subreddit?.trim() ? `r/${values.subreddit.trim().replace(/^r\//i, "")}` : null
  ].filter(Boolean);

  const filters = [
    MEDIA_LABELS[values.mediaType] || "All media",
    SORT_LABELS[values.sortBy] || "Relevance",
    values.timeFilter === "all" ? null : TIME_LABELS[values.timeFilter],
    values.includeNsfw ? "NSFW on" : null
  ].filter(Boolean);

  return {
    context: context.join(" - ") || "Reddit media",
    filters: filters.join(" - ") || "All media"
  };
}

export function SearchSummary({ values, resultCount, onEdit }) {
  const summary = getSearchSummaryLines(values);

  return (
    <Paper
      className="search-summary-card"
      component="section"
      aria-label="Current search filters"
      withBorder
      p="md"
      radius="md"
    >
      <Stack gap="xs">
        <Group justify="space-between" align="flex-start" gap="sm">
          <Stack gap={2}>
            <Text fw={700} lineClamp={1}>
              {summary.context}
            </Text>
            <Text size="sm" c="gray.6" lineClamp={1}>
              {summary.filters}
              {Number.isFinite(resultCount) ? ` - ${resultCount} results` : ""}
            </Text>
          </Stack>
          <Button variant="light" size="xs" onClick={onEdit}>
            Edit filters
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}

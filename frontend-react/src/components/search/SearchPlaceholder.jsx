import { Paper, Stack, Text } from "@mantine/core";

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

function getSubmittedMessage(values) {
  if (!values) {
    return "Search results will appear here.";
  }

  if (values.query && values.subreddit) {
    return `Ready to search for "${values.query}" in r/${values.subreddit}`;
  }

  if (values.query) {
    return `Ready to search Reddit for "${values.query}"`;
  }

  return `Ready to browse media from r/${values.subreddit}`;
}

function getFilterSummary(values) {
  if (!values) {
    return "Enter a keyword, a subreddit, or both.";
  }

  return [
    MEDIA_LABELS[values.mediaType],
    SORT_LABELS[values.sortBy],
    TIME_LABELS[values.timeFilter],
    values.includeNsfw ? "NSFW on" : "NSFW off"
  ].join(" - ");
}

export function SearchPlaceholder({ submittedValues }) {
  return (
    <Paper
      className="search-placeholder"
      component="section"
      aria-live="polite"
      withBorder
      p={{ base: "md", sm: "lg" }}
      radius="md"
    >
      <Stack gap="xs">
        <Text fw={600}>{getSubmittedMessage(submittedValues)}</Text>
        <Text size="sm" c="gray.6">
          {getFilterSummary(submittedValues)}
        </Text>
      </Stack>
    </Paper>
  );
}

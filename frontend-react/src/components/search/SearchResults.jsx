import { Paper, Stack, Text } from "@mantine/core";
import { MediaGrid } from "../media/MediaGrid";
import { MediaPreviewModal } from "../media/MediaPreviewModal";
import { useMediaPreview } from "../../hooks/useMediaPreview";
import { SearchEmpty } from "./SearchEmpty";
import { SearchError } from "./SearchError";
import { SearchLoading } from "./SearchLoading";

const MEDIA_LABELS = {
  all: "All media",
  images: "Images",
  videos: "Videos",
  gifs: "GIFs",
  image: "Images",
  video: "Videos",
  gif: "GIFs",
  gallery: "Galleries",
  external: "External media"
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

function getIdleSummary() {
  return {
    title: "Search results will appear here.",
    detail: "Enter a keyword, a subreddit, or both."
  };
}

function getResultsSummary(state) {
  const request = state.lastRequest || {};
  const meta = state.responseMeta || {};
  const query = request.query;
  const subreddit = meta.subreddit || request.subreddit;
  const mediaType = MEDIA_LABELS[meta.mediaType] || MEDIA_LABELS[request.mediaType] || "Media";
  const sort = SORT_LABELS[meta.effectiveSort] || SORT_LABELS[request.sortBy];
  const time = TIME_LABELS[meta.timeFilter] || TIME_LABELS[request.timeFilter];
  const resultCount = Number.isFinite(meta.count) && meta.count > state.items.length
    ? meta.count
    : state.items.length;
  const title = query && subreddit
    ? `${query} in r/${subreddit}`
    : query
      ? query
      : subreddit
        ? `Browsing r/${subreddit}`
        : "Reddit media results";
  const detail = [
    mediaType,
    sort,
    time,
    request.includeNsfw ? "NSFW included" : "NSFW off"
  ].filter(Boolean).join(" - ");

  return { title, detail, resultCount };
}

function IdlePlaceholder() {
  const summary = getIdleSummary();

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
        <Text fw={600}>{summary.title}</Text>
        <Text size="sm" c="gray.6">
          {summary.detail}
        </Text>
      </Stack>
    </Paper>
  );
}

function ResultsList({ state, onLoadMore }) {
  const { opened, selectedItem, openPreview, closePreview } = useMediaPreview();
  const summary = getResultsSummary(state);

  return (
    <>
      <Paper
        className="search-results-panel"
        component="section"
        aria-live="polite"
        withBorder
        p={{ base: "md", sm: "lg" }}
        radius="md"
      >
        <Stack gap="md">
          <div className="search-results-header">
            <Text fw={700} lineClamp={1}>{summary.title}</Text>
            <Text size="sm" c="gray.6">
              {summary.detail}
            </Text>
            <Text className="search-results-count" size="sm" fw={700}>
              {summary.resultCount} result{summary.resultCount === 1 ? "" : "s"}
            </Text>
          </div>
          <MediaGrid
            items={state.items}
            isLoadingMore={state.isLoadingMore}
            loadMoreError={state.loadMoreError}
            nextAfter={state.nextAfter}
            onLoadMore={onLoadMore}
            onOpenPreview={openPreview}
          />
        </Stack>
      </Paper>
      <MediaPreviewModal
        opened={opened}
        item={selectedItem}
        onClose={closePreview}
      />
    </>
  );
}

export function SearchResults({
  state,
  onRetry,
  onLoadMore,
  onClearFilters
}) {
  switch (state.status) {
    case "idle":
      return <IdlePlaceholder />;
    case "loading":
      return <SearchLoading />;
    case "empty":
      return <SearchEmpty state={state} onClearFilters={onClearFilters} />;
    case "error":
      return <SearchError error={state.error} onRetry={onRetry} />;
    case "success":
      return <ResultsList state={state} onLoadMore={onLoadMore} />;
    default:
      return null;
  }
}

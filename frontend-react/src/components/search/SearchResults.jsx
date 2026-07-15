import { Paper, Stack, Text } from "@mantine/core";
import { MediaGrid } from "../media/MediaGrid";
import { MediaPreviewModal } from "../media/MediaPreviewModal";
import { useMediaPreview } from "../../hooks/useMediaPreview";
import { SearchEmpty } from "./SearchEmpty";
import { SearchError } from "./SearchError";
import { SearchLoading } from "./SearchLoading";

const MEDIA_LABELS = {
  all: "Media",
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

function getIdleSummary() {
  return {
    title: "Search results will appear here.",
    detail: "Enter a keyword, a subreddit, or both."
  };
}

function getSuccessSummary(state) {
  const request = state.lastRequest || {};
  const meta = state.responseMeta || {};
  const query = request.query;
  const subreddit = meta.subreddit || request.subreddit;
  const mediaType = MEDIA_LABELS[meta.mediaType] || MEDIA_LABELS[request.mediaType] || "Media";
  const sort = SORT_LABELS[meta.effectiveSort] || SORT_LABELS[request.sortBy];

  if (query && subreddit) {
    return `Showing results for "${query}" in r/${subreddit}`;
  }

  if (query) {
    return `Showing results for "${query}"`;
  }

  if (subreddit) {
    const suffix = sort ? ` - Sorted by ${sort}` : "";
    return `Browsing ${mediaType} from r/${subreddit}${suffix}`;
  }

  return "Showing Reddit media results";
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
          <Stack gap={2}>
            <Text fw={600}>{getSuccessSummary(state)}</Text>
            <Text size="sm" c="gray.6">
              {state.items.length} result{state.items.length === 1 ? "" : "s"}
            </Text>
          </Stack>
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

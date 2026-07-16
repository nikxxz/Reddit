import { Alert, Button, Group, Paper, Popover, Stack, Text, Title } from "@mantine/core";
import { IconAdjustmentsHorizontal, IconArrowLeft } from "@tabler/icons-react";
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { searchRedditEntities } from "../api/redditEntities";
import { EntityHeader } from "../components/entities/EntityHeader";
import { EntitySearchForm } from "../components/entities/EntitySearchForm";
import { EntitySearchResults } from "../components/entities/EntitySearchResults";
import { MediaGrid } from "../components/media/MediaGrid";
import { MediaPreviewModal } from "../components/media/MediaPreviewModal";
import { SearchFilters } from "../components/search/SearchFilters";
import { SearchLoading } from "../components/search/SearchLoading";
import { useEntityMedia } from "../hooks/useEntityMedia";
import { useMediaPreview } from "../hooks/useMediaPreview";
import "../styles/entities.css";

const ENTITY_INITIAL = {
  status: "idle",
  query: "",
  subreddits: [],
  users: [],
  error: null
};

const MEDIA_OPTIONS = [
  { value: "all", label: "All media", urlValue: "all" },
  { value: "images", label: "Images", urlValue: "image" },
  { value: "videos", label: "Videos", urlValue: "video" },
  { value: "gifs", label: "GIFs", urlValue: "gif" },
  { value: "gallery", label: "Gallery", urlValue: "gallery" }
];

const SUBREDDIT_SORTS = [
  { value: "hot", label: "Hot" },
  { value: "new", label: "New" },
  { value: "top", label: "Top" },
  { value: "rising", label: "Rising" }
];

const USER_SORTS = [
  { value: "new", label: "New" },
  { value: "top", label: "Top" }
];

const TIME_OPTIONS = [
  { value: "hour", label: "Past hour" },
  { value: "day", label: "Today" },
  { value: "week", label: "This week" },
  { value: "month", label: "This month" },
  { value: "year", label: "This year" },
  { value: "all", label: "All time" }
];

const MEDIA_URL_TO_UI = new Map(
  MEDIA_OPTIONS.flatMap((item) => [[item.value, item.value], [item.urlValue, item.value]])
);

function entityReducer(state, action) {
  if (action.type === "START") {
    return { ...ENTITY_INITIAL, status: "loading", query: action.query };
  }
  if (action.type === "SUCCESS") {
    return {
      status: "success",
      query: action.query,
      subreddits: action.subreddits,
      users: action.users,
      error: null
    };
  }
  if (action.type === "ERROR") {
    return { ...ENTITY_INITIAL, status: "error", query: action.query, error: action.error };
  }
  return state;
}

function queryFromFilters(filters) {
  const params = new URLSearchParams();
  const mediaOption = MEDIA_OPTIONS.find((item) => item.value === filters.mediaType) || MEDIA_OPTIONS[0];
  params.set("sort", filters.sortBy);
  params.set("time", filters.timeFilter);
  params.set("media", mediaOption.urlValue);
  params.set("nsfw", filters.includeNsfw ? "true" : "false");
  return params.toString();
}

function filtersFromRoute(route) {
  const params = route?.query || new URLSearchParams();
  const sortOptions = route?.entityType === "user" ? USER_SORTS : SUBREDDIT_SORTS;
  const fallbackSort = route?.entityType === "user" ? "new" : "hot";
  const rawSort = params.get("sort") || fallbackSort;
  const sortBy = sortOptions.some((option) => option.value === rawSort) ? rawSort : fallbackSort;
  const timeFilter = TIME_OPTIONS.some((option) => option.value === params.get("time")) ? params.get("time") : "all";
  return {
    mediaType: MEDIA_URL_TO_UI.get(params.get("media")) || "all",
    sortBy,
    timeFilter: sortBy === "top" ? timeFilter : "all",
    includeNsfw: params.get("nsfw") === "true"
  };
}

function sameFilters(left, right) {
  return left.mediaType === right.mediaType &&
    left.sortBy === right.sortBy &&
    left.timeFilter === right.timeFilter &&
    left.includeNsfw === right.includeNsfw;
}

function labelFor(options, value, fallback = value) {
  return options.find((option) => option.value === value)?.label || fallback;
}

function MediaResultSummary({ count, filters, sortOptions }) {
  if (count <= 0) {
    return null;
  }
  const parts = [
    `${count} media ${count === 1 ? "item" : "items"}`,
    labelFor(MEDIA_OPTIONS, filters.mediaType, "All media"),
    labelFor(sortOptions, filters.sortBy)
  ];
  if (filters.sortBy === "top") {
    parts.push(labelFor(TIME_OPTIONS, filters.timeFilter, "All time"));
  }
  if (filters.includeNsfw) {
    parts.push("NSFW included");
  }
  return (
    <Text className="entity-media-summary" size="sm" c="gray.6">
      {parts.join(" · ")}
    </Text>
  );
}

export function EntityBrowserPage({ route, onNavigateEntity, onNavigateBrowse, onReplaceEntityQuery }) {
  const [searchState, dispatchSearch] = useReducer(entityReducer, ENTITY_INITIAL);
  const searchControllerRef = useRef(null);

  const submitSearch = useCallback(async (query) => {
    searchControllerRef.current?.abort();
    const nextController = new AbortController();
    searchControllerRef.current = nextController;
    dispatchSearch({ type: "START", query });
    try {
      const response = await searchRedditEntities(query, { signal: nextController.signal });
      dispatchSearch({
        type: "SUCCESS",
        query: response.query,
        subreddits: response.subreddits,
        users: response.users
      });
    } catch (error) {
      if (error.name !== "AbortError") {
        dispatchSearch({
          type: "ERROR",
          query,
          error: error.message || "Unable to search Reddit."
        });
      }
    } finally {
      if (searchControllerRef.current === nextController) {
        searchControllerRef.current = null;
      }
    }
  }, []);

  useEffect(() => () => searchControllerRef.current?.abort(), []);

  if (route?.entityType && route?.entityName) {
    return (
      <EntityMediaPage
        route={route}
        onNavigateBrowse={onNavigateBrowse}
        onReplaceEntityQuery={onReplaceEntityQuery}
      />
    );
  }
  return <EntitySearchPage state={searchState} onSubmit={submitSearch} onNavigateEntity={onNavigateEntity} />;
}

function EntitySearchPage({ state, onSubmit, onNavigateEntity }) {
  return (
    <Stack className="entity-browser-page" gap="md">
      <Paper className="entity-search-panel" component="section" withBorder p={{ base: "md", sm: "lg" }}>
        <Stack gap="sm">
          <Stack gap={3}>
            <Title order={2} size="h3">Subreddits / Users</Title>
            <Text size="sm" c="gray.6">Search for a subreddit or Reddit user, then browse their media.</Text>
          </Stack>
          <EntitySearchForm isLoading={state.status === "loading"} onSubmit={onSubmit} />
        </Stack>
      </Paper>
      <EntitySearchResults state={state} onOpenEntity={onNavigateEntity} />
    </Stack>
  );
}

function EntityMediaPage({ route, onNavigateBrowse, onReplaceEntityQuery }) {
  const initialFilters = useMemo(() => filtersFromRoute(route), [route]);
  const [filters, setFilters] = useState(initialFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const { state, load, loadMore } = useEntityMedia();
  const { opened, selectedItem, openPreview, closePreview } = useMediaPreview();
  const sortOptions = route.entityType === "user" ? USER_SORTS : SUBREDDIT_SORTS;

  useEffect(() => {
    const next = filtersFromRoute(route);
    setFilters((current) => sameFilters(current, next) ? current : next);
  }, [route]);

  useEffect(() => {
    load({
      entityType: route.entityType,
      entityName: route.entityName,
      mediaType: filters.mediaType,
      sortBy: filters.sortBy,
      timeFilter: filters.timeFilter,
      includeNsfw: filters.includeNsfw,
      limit: 24
    });
  }, [filters, load, route.entityName, route.entityType]);

  useEffect(() => {
    onReplaceEntityQuery(queryFromFilters(filters));
  }, [filters, onReplaceEntityQuery]);

  const setFieldValue = (field, value) => {
    setFilters((current) => ({ ...current, [field]: value }));
  };

  const emptyMessage = state.message ||
    (route.entityType === "subreddit"
      ? "No matching media was found in this subreddit."
      : "No matching media was found for this user.");

  return (
    <Stack className="entity-browser-page" gap="md">
      <Group justify="space-between" align="center" gap="sm">
        <Button variant="subtle" leftSection={<IconArrowLeft size={16} stroke={1.8} />} onClick={onNavigateBrowse}>
          Subreddits / Users
        </Button>
        <Popover opened={filtersOpen} onChange={setFiltersOpen} position="bottom-end" shadow="xl" width={360} withinPortal>
          <Popover.Target>
            <Button variant="light" leftSection={<IconAdjustmentsHorizontal size={16} stroke={1.8} />} onClick={() => setFiltersOpen((open) => !open)}>
              Filters
            </Button>
          </Popover.Target>
          <Popover.Dropdown>
            <SearchFilters
              values={filters}
              onFieldChange={setFieldValue}
              sortOptions={sortOptions}
              disableTime={filters.sortBy !== "top"}
            />
          </Popover.Dropdown>
        </Popover>
      </Group>
      <EntityHeader entity={state.entity} fallbackType={route.entityType} fallbackName={route.entityName} />
      <MediaResultSummary count={state.items.length} filters={filters} sortOptions={sortOptions} />
      {state.status === "loading" ? <SearchLoading /> : null}
      {state.status === "error" ? (
        <Alert color="red" role="alert">{state.error}</Alert>
      ) : null}
      {state.status === "empty" ? (
        <Paper withBorder p="lg">
          <Text fw={700}>{emptyMessage}</Text>
        </Paper>
      ) : null}
      {state.status === "success" ? (
        <Paper className="search-results-panel" withBorder p={{ base: "md", sm: "lg" }}>
          <MediaGrid
            items={state.items}
            isLoadingMore={state.isLoadingMore}
            loadMoreError={state.loadMoreError}
            nextAfter={state.nextCursor}
            onLoadMore={loadMore}
            onOpenPreview={openPreview}
          />
        </Paper>
      ) : null}
      <MediaPreviewModal opened={opened} item={selectedItem} onClose={closePreview} />
    </Stack>
  );
}

import { Alert, Button, Group, Paper, Popover, Stack, Text, Title } from "@mantine/core";
import { IconAdjustmentsHorizontal, IconArrowLeft } from "@tabler/icons-react";
import { useCallback, useEffect, useMemo, useReducer, useState } from "react";
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

const SUBREDDIT_SORTS = [
  { value: "hot", label: "Hot" },
  { value: "new", label: "New" },
  { value: "top", label: "Top" },
  { value: "rising", label: "Rising" }
];

const USER_SORTS = [
  { value: "new", label: "New" },
  { value: "top", label: "Top" },
  { value: "hot", label: "Hot" }
];

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
  params.set("sort", filters.sortBy);
  params.set("time", filters.timeFilter);
  params.set("media", filters.mediaType);
  params.set("nsfw", filters.includeNsfw ? "true" : "false");
  return params.toString();
}

function filtersFromRoute(route) {
  const params = route?.query || new URLSearchParams();
  return {
    mediaType: params.get("media") || "all",
    sortBy: params.get("sort") || (route?.entityType === "user" ? "new" : "hot"),
    timeFilter: params.get("time") || "all",
    includeNsfw: params.get("nsfw") === "true"
  };
}

function sameFilters(left, right) {
  return left.mediaType === right.mediaType &&
    left.sortBy === right.sortBy &&
    left.timeFilter === right.timeFilter &&
    left.includeNsfw === right.includeNsfw;
}

export function EntityBrowserPage({ route, onNavigateEntity, onNavigateBrowse, onReplaceEntityQuery }) {
  if (route?.entityType && route?.entityName) {
    return (
      <EntityMediaPage
        route={route}
        onNavigateBrowse={onNavigateBrowse}
        onReplaceEntityQuery={onReplaceEntityQuery}
      />
    );
  }
  return <EntitySearchPage onNavigateEntity={onNavigateEntity} />;
}

function EntitySearchPage({ onNavigateEntity }) {
  const [state, dispatch] = useReducer(entityReducer, ENTITY_INITIAL);
  const [controller, setController] = useState(null);

  const submit = useCallback(async (query) => {
    controller?.abort();
    const nextController = new AbortController();
    setController(nextController);
    dispatch({ type: "START", query });
    try {
      const response = await searchRedditEntities(query, { signal: nextController.signal });
      dispatch({
        type: "SUCCESS",
        query: response.query,
        subreddits: response.subreddits,
        users: response.users
      });
    } catch (error) {
      if (error.name !== "AbortError") {
        dispatch({
          type: "ERROR",
          query,
          error: error.message || "Unable to search Reddit."
        });
      }
    }
  }, [controller]);

  useEffect(() => () => controller?.abort(), [controller]);

  return (
    <Stack className="entity-browser-page" gap="md">
      <Paper className="entity-search-panel" component="section" withBorder p={{ base: "md", sm: "lg" }}>
        <Stack gap="sm">
          <Stack gap={3}>
            <Title order={2} size="h3">Subreddits / Users</Title>
            <Text size="sm" c="gray.6">Search for a subreddit or Reddit user, then browse their media.</Text>
          </Stack>
          <EntitySearchForm isLoading={state.status === "loading"} onSubmit={submit} />
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
    if (route.entityType === "user" && next.sortBy === "rising") {
      next.sortBy = "new";
    }
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

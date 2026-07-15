import { searchRedditMedia } from "../api/redditApi.js";
import { sampleMedia } from "../data/sampleMedia.js";
import { bindFilterHandlers, renderActiveFilter } from "../handlers/filterHandlers.js";
import { bindSearchHandlers } from "../handlers/searchHandlers.js";
import { clearSelection } from "../handlers/selectionHandlers.js";
import { renderMediaGrid, uniqueById } from "../renderers/mediaGrid.js";
import {
  renderSearchHeading,
  renderSearchState,
  renderSortSummary,
} from "../renderers/stateRenderer.js";
import { SearchStatus, state } from "../state.js";
import { normalizeSubreddit } from "../utils/formatting.js";


export function initializeSearchPage(elements) {
  bindSearchHandlers(elements, {
    onSubmit: (event) => handleSearchSubmit(event, elements),
    onRetry: () => retryLastSearch(elements),
    onLoadMore: () => loadMore(elements),
  });
  bindFilterHandlers(elements, {
    onMediaFilter: (filter) => applyMediaFilter(elements, filter),
    onSortChange: () => handleSortChange(elements),
    onNsfwChange: () => handleNsfwChange(elements),
  });
  initializeNsfwPreference(elements);
  renderSortSummary(elements);
  renderSearchPage(elements);
}


export function getVisibleMedia() {
  if (state.hasSearched) {
    return state.items;
  }
  if (state.activeMediaFilter === "all") {
    return sampleMedia;
  }
  return sampleMedia.filter((item) => item.media_type === state.activeMediaFilter);
}


export function renderSearchPage(elements) {
  const visibleItems = getVisibleMedia();
  elements.mediaGrid.replaceChildren(
    ...renderMediaGrid(visibleItems, () => renderSearchPage(elements)),
  );
  renderSearchHeading(elements, state, visibleItems);
  renderSearchState(elements, state, visibleItems);
}


function applyMediaFilter(elements, filter) {
  state.activeMediaFilter = filter;
  renderActiveFilter(elements, filter);
  if (state.searchQuery || state.subreddit) {
    startFreshSearch(elements, buildCurrentRequest({ after: null }));
  } else {
    renderSearchPage(elements);
  }
}


function handleSortChange(elements) {
  state.sortBy = elements.sortSelect.value;
  renderSortSummary(elements);
  if (state.searchQuery || state.subreddit) {
    startFreshSearch(elements, buildCurrentRequest({ after: null }));
  }
}


function initializeNsfwPreference(elements) {
  state.includeNsfw = localStorage.getItem("redditMediaDownloader.includeNsfw") === "true";
  elements.includeNsfwToggle.checked = state.includeNsfw;
}


function handleNsfwChange(elements) {
  state.includeNsfw = Boolean(elements.includeNsfwToggle.checked);
  localStorage.setItem("redditMediaDownloader.includeNsfw", String(state.includeNsfw));
  if (state.searchQuery || state.subreddit) {
    startFreshSearch(elements, buildCurrentRequest({ after: null }));
  }
}


function handleSearchSubmit(event, elements) {
  event.preventDefault();
  const query = elements.searchInput.value.trim();
  const subreddit = normalizeSubreddit(elements.subredditInput.value);
  if (!query && !subreddit) {
    clearSearchResults();
    state.searchStatus = SearchStatus.ERROR;
    state.error = "Enter a keyword or subreddit.";
    state.hasSearched = true;
    clearSelection();
    renderSearchPage(elements);
    return;
  }

  state.searchQuery = query;
  state.subreddit = subreddit;
  elements.subredditInput.value = state.subreddit;
  startFreshSearch(elements, buildCurrentRequest({ after: null }));
}


function buildCurrentRequest({ after = null } = {}) {
  return {
    query: state.searchQuery,
    subreddit: state.subreddit,
    mediaType: state.activeMediaFilter,
    sort: state.sortBy,
    timeFilter: state.timeFilter,
    limit: 24,
    after,
    includeNsfw: state.includeNsfw,
  };
}


async function startFreshSearch(elements, request) {
  if (!request.query && !request.subreddit) {
    return;
  }
  if (state.activeSearchController) {
    state.activeSearchController.abort();
  }
  const controller = new AbortController();
  state.activeSearchController = controller;

  state.searchStatus = SearchStatus.LOADING;
  state.loading = true;
  state.isLoadingMore = false;
  state.error = "";
  state.emptyTitle = "";
  state.emptyMessage = "";
  state.hasSearched = true;
  state.items = [];
  state.nextAfter = null;
  state.lastRequest = { ...request, after: null };
  clearSelection();
  renderSearchPage(elements);

  try {
    const data = await searchRedditMedia({
      ...request,
      signal: controller.signal,
      timeoutMs: 25000,
    });
    const incoming = Array.isArray(data.items) ? data.items : [];
    state.items = uniqueById([], incoming);
    state.nextAfter = data.next_after || null;
    state.searchMode = data.mode || inferSearchMode(request);
    state.emptyMessage = data.message || "";
    applyFinalStatus(data);
  } catch (error) {
    if (error.name === "AbortError") {
      state.error = "Reddit search timed out. Please try again.";
    } else {
      state.error = error.message || "Unable to search Reddit at this time.";
    }
    state.searchStatus = SearchStatus.ERROR;
  } finally {
    if (state.activeSearchController === controller) {
      state.loading = false;
      state.activeSearchController = null;
      renderSearchPage(elements);
    }
  }
}


async function loadMore(elements) {
  if (!state.nextAfter || state.isLoadingMore || state.searchStatus !== SearchStatus.SUCCESS) {
    return;
  }
  const request = {
    ...(state.lastRequest || buildCurrentRequest({ after: null })),
    after: state.nextAfter,
  };
  state.isLoadingMore = true;
  renderSearchPage(elements);
  try {
    const data = await searchRedditMedia({
      ...request,
      timeoutMs: 25000,
    });
    const incoming = Array.isArray(data.items) ? data.items : [];
    state.items = state.items.concat(uniqueById(state.items, incoming));
    state.nextAfter = data.next_after || null;
    state.searchStatus = state.items.length ? SearchStatus.SUCCESS : SearchStatus.EMPTY;
  } catch (error) {
    state.error = error.message || "Unable to search Reddit at this time.";
    state.searchStatus = SearchStatus.ERROR;
  } finally {
    state.isLoadingMore = false;
    renderSearchPage(elements);
  }
}


function retryLastSearch(elements) {
  if (!state.lastRequest) {
    return;
  }
  state.searchQuery = state.lastRequest.query || "";
  state.subreddit = state.lastRequest.subreddit || "";
  startFreshSearch(elements, { ...state.lastRequest, after: null });
}


function applyFinalStatus(data) {
  if (state.items.length > 0) {
    state.searchStatus = SearchStatus.SUCCESS;
    return;
  }
  state.searchStatus = SearchStatus.EMPTY;
  if (data.message?.startsWith("No Reddit posts")) {
    state.emptyTitle = "No Reddit posts found";
    state.emptyMessage = "No posts matched the current search in this subreddit.";
  } else if (data.message?.startsWith("Matching posts")) {
    state.emptyTitle = "No matching media";
    state.emptyMessage = "Matching posts were found, but none contained supported media.";
  } else {
    state.emptyTitle = "No media matches the current filters";
    state.emptyMessage = data.message || "Try another media type, sort option, or enable NSFW content.";
  }
}


function inferSearchMode(request) {
  if (request.query && request.subreddit) {
    return "subreddit_search";
  }
  if (request.query) {
    return "global_search";
  }
  return "subreddit_browse";
}

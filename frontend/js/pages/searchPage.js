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
import { state } from "../state.js";
import { normalizeSubreddit } from "../utils/formatting.js";


export function initializeSearchPage(elements) {
  bindSearchHandlers(elements, {
    onSubmit: (event) => handleSearchSubmit(event, elements),
    onRetry: () => runSearch(elements, { append: false }),
    onLoadMore: () => runSearch(elements, { append: true }),
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
  if (state.searchQuery) {
    runSearch(elements, { append: false });
  } else {
    renderSearchPage(elements);
  }
}


function handleSortChange(elements) {
  state.sortBy = elements.sortSelect.value;
  renderSortSummary(elements);
  if (state.searchQuery) {
    runSearch(elements, { append: false });
  }
}


function initializeNsfwPreference(elements) {
  state.includeNsfw = localStorage.getItem("redditMediaDownloader.includeNsfw") === "true";
  elements.includeNsfwToggle.checked = state.includeNsfw;
}


function handleNsfwChange(elements) {
  state.includeNsfw = Boolean(elements.includeNsfwToggle.checked);
  localStorage.setItem("redditMediaDownloader.includeNsfw", String(state.includeNsfw));
  if (state.searchQuery) {
    runSearch(elements, { append: false });
  }
}


function handleSearchSubmit(event, elements) {
  event.preventDefault();
  const query = elements.searchInput.value.trim();
  if (!query) {
    state.searchQuery = "";
    state.subreddit = normalizeSubreddit(elements.subredditInput.value);
    state.hasSearched = false;
    state.error = "";
    state.items = [];
    state.nextAfter = null;
    clearSelection();
    renderSearchPage(elements);
    return;
  }

  state.searchQuery = query;
  state.subreddit = normalizeSubreddit(elements.subredditInput.value);
  elements.subredditInput.value = state.subreddit;
  runSearch(elements, { append: false });
}


async function runSearch(elements, { append = false } = {}) {
  if (!state.searchQuery) {
    return;
  }
  if (state.activeSearchController) {
    state.activeSearchController.abort();
  }
  const controller = new AbortController();
  state.activeSearchController = controller;

  state.loading = true;
  state.error = "";
  state.hasSearched = true;
  if (!append) {
    state.items = [];
    state.nextAfter = null;
    clearSelection();
  }
  renderSearchPage(elements);

  try {
    const data = await searchRedditMedia({
      query: state.searchQuery,
      subreddit: state.subreddit,
      mediaType: state.activeMediaFilter,
      sort: state.sortBy,
      timeFilter: "all",
      limit: 24,
      after: append ? state.nextAfter : null,
      includeNsfw: state.includeNsfw,
      signal: controller.signal,
      timeoutMs: 25000,
    });
    const incoming = Array.isArray(data.items) ? data.items : [];
    const uniqueItems = uniqueById(state.items, incoming);
    state.items = append ? state.items.concat(uniqueItems) : uniqueItems;
    state.nextAfter = data.next_after || null;
  } catch (error) {
    if (error.name === "AbortError") {
      state.error = "Reddit search timed out. Please try again.";
    } else {
      state.error = error.message || "Unable to search Reddit at this time.";
    }
  } finally {
    if (state.activeSearchController === controller) {
      state.loading = false;
      state.activeSearchController = null;
      renderSearchPage(elements);
    }
  }
}

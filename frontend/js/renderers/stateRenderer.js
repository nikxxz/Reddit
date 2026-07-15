import { setHidden } from "../utils/dom.js";
import { SearchStatus } from "../state.js";


export function renderSearchState(elements, state, visibleItems) {
  const status = state.searchStatus || SearchStatus.IDLE;
  const showGrid =
    (status === SearchStatus.IDLE && visibleItems.length > 0) ||
    (status === SearchStatus.SUCCESS && visibleItems.length > 0);
  elements.mediaGrid.hidden = !showGrid;
  setHidden(elements.loadingState, status !== SearchStatus.LOADING);
  setHidden(elements.emptyState, status !== SearchStatus.EMPTY);
  setHidden(elements.errorState, status !== SearchStatus.ERROR);
  setHidden(elements.loadMoreSkeletons, !state.isLoadingMore);
  elements.emptyTitle.textContent = state.emptyTitle || "No matching media found";
  elements.emptyMessage.textContent =
    state.emptyMessage || "Try choosing another media type filter.";
  elements.errorMessage.textContent = state.error || "Unable to search Reddit at this time.";
  elements.loadMoreRow.hidden =
    status !== SearchStatus.SUCCESS ||
    visibleItems.length === 0 ||
    !state.nextAfter ||
    state.isLoadingMore;
  elements.loadMoreButton.disabled = state.isLoadingMore;
  elements.searchButton.disabled = status === SearchStatus.LOADING;
  elements.searchButton.textContent =
    status === SearchStatus.LOADING ? "Searching..." : "Search";
}


export function renderSearchHeading(elements, state, visibleItems) {
  if (state.searchStatus === SearchStatus.LOADING) {
    elements.resultsTitle.textContent = "Searching Reddit...";
    elements.resultSummary.textContent = "Searching Reddit...";
    return;
  }
  if (state.searchStatus === SearchStatus.ERROR) {
    elements.resultsTitle.textContent = "Reddit search failed";
    elements.resultSummary.textContent = "Search unavailable";
    return;
  }

  const selectedVisible = visibleItems.filter((item) => state.selectedIds.has(item.id)).length;
  const resultWord = visibleItems.length === 1 ? "result" : "results";
  if (state.hasSearched) {
    elements.resultsTitle.textContent = searchHeading(state);
    elements.resultSummary.textContent =
      `${visibleItems.length} ${resultWord} - ${selectedVisible} selected`;
    return;
  }

  elements.resultsTitle.textContent = "Browse sample media";
  elements.resultSummary.textContent =
    `${visibleItems.length} sample ${resultWord} - ${selectedVisible} selected`;
}


function searchHeading(state) {
  const mediaLabel =
    state.activeMediaFilter === "all"
      ? "media"
      : `${state.activeMediaFilter.charAt(0).toUpperCase()}${state.activeMediaFilter.slice(1)}s`;
  if (state.searchQuery && state.subreddit) {
    return `Showing results for "${state.searchQuery}" in r/${state.subreddit}`;
  }
  if (state.searchQuery) {
    return `Showing results for "${state.searchQuery}"`;
  }
  return `Browsing ${mediaLabel} from r/${state.subreddit}`;
}


export function renderSortSummary(elements) {
  const selectedOption = elements.sortSelect.options[elements.sortSelect.selectedIndex];
  elements.sortSummary.textContent = `Sorted by ${selectedOption.textContent}`;
}

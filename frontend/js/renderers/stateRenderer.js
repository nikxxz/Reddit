import { setHidden } from "../utils/dom.js";


export function renderSearchState(elements, state, visibleItems) {
  elements.mediaGrid.hidden =
    state.loading || Boolean(state.error) || visibleItems.length === 0;
  setHidden(
    elements.emptyState,
    state.loading || Boolean(state.error) || visibleItems.length > 0,
  );
  setHidden(elements.loadingState, !state.loading);
  setHidden(elements.errorState, !state.error);
  elements.emptyMessage.textContent =
    state.emptyMessage || "Try choosing another media type filter.";
  elements.errorMessage.textContent = state.error || "Unable to search Reddit at this time.";
  elements.loadMoreRow.hidden =
    !state.hasSearched || state.loading || Boolean(state.error) || !state.nextAfter;
  elements.loadMoreButton.disabled = state.loading;
  elements.searchButton.disabled = state.loading;
}


export function renderSearchHeading(elements, state, visibleItems) {
  if (state.loading) {
    elements.resultsTitle.textContent = "Searching Reddit...";
    elements.resultSummary.textContent = "Searching Reddit...";
    return;
  }
  if (state.error) {
    elements.resultsTitle.textContent = "Reddit search failed";
    elements.resultSummary.textContent = "Search unavailable";
    return;
  }

  const selectedVisible = visibleItems.filter((item) => state.selectedIds.has(item.id)).length;
  const resultWord = visibleItems.length === 1 ? "result" : "results";
  if (state.hasSearched) {
    elements.resultsTitle.textContent = state.searchQuery
      ? `Showing results for "${state.searchQuery}"`
      : `Browsing r/${state.subreddit}`;
    elements.resultSummary.textContent =
      `${visibleItems.length} ${resultWord} - ${selectedVisible} selected`;
    return;
  }

  elements.resultsTitle.textContent = "Browse sample media";
  elements.resultSummary.textContent =
    `${visibleItems.length} sample ${resultWord} - ${selectedVisible} selected`;
}


export function renderSortSummary(elements) {
  const selectedOption = elements.sortSelect.options[elements.sortSelect.selectedIndex];
  elements.sortSummary.textContent = `Sorted by ${selectedOption.textContent}`;
}

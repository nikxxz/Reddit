export function bindSearchHandlers(elements, actions) {
  elements.searchForm.addEventListener("submit", actions.onSubmit);
  elements.tryAgainButton.addEventListener("click", actions.onRetry);
  elements.loadMoreButton.addEventListener("click", actions.onLoadMore);
}

export const state = {
  appName: "Media Finder",
  redditUsername: "",
  currentPage: "search",
  sidebarCollapsed: false,
  activeMediaFilter: "all",
  sortBy: "relevance",
  selectedIds: new Set(),
  searchQuery: "",
  subreddit: "",
  items: [],
  nextAfter: null,
  loading: false,
  error: "",
  hasSearched: false,
  connections: {
    backend: "Checking",
    reddit: "Checking",
    redditReadOnly: null,
  },
};


export function clearSearchResults() {
  state.items = [];
  state.nextAfter = null;
  state.error = "";
}


export function resetSelection() {
  state.selectedIds.clear();
}


export function setCurrentPage(page) {
  state.currentPage = page;
}

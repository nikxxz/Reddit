export const SearchStatus = {
  IDLE: "idle",
  LOADING: "loading",
  SUCCESS: "success",
  EMPTY: "empty",
  ERROR: "error",
};


export const state = {
  appName: "Media Finder",
  redditUsername: "",
  currentPage: "search",
  sidebarCollapsed: false,
  activeMediaFilter: "all",
  sortBy: "relevance",
  timeFilter: "all",
  selectedIds: new Set(),
  searchQuery: "",
  subreddit: "",
  searchMode: null,
  searchStatus: SearchStatus.IDLE,
  isLoadingMore: false,
  lastRequest: null,
  includeNsfw: false,
  activeSearchController: null,
  items: [],
  nextAfter: null,
  loading: false,
  error: "",
  emptyTitle: "",
  emptyMessage: "",
  hasSearched: false,
  connections: {
    backend: "Checking",
    reddit: "Checking",
    redditReadOnly: null,
  },
  redditAuth: {
    connected: false,
    connecting: false,
    username: "",
  },
};


export function clearSearchResults() {
  state.items = [];
  state.nextAfter = null;
  state.error = "";
  state.emptyTitle = "";
  state.emptyMessage = "";
}


export function resetSelection() {
  state.selectedIds.clear();
}


export function setCurrentPage(page) {
  state.currentPage = page;
}

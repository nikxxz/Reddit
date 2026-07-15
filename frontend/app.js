const sampleMedia = [
  {
    id: "mountain-lake",
    title: "Mountain Lake at Sunrise",
    subreddit: "EarthPorn",
    mediaType: "image",
    thumbnail: "linear-gradient(135deg, #2563eb 0%, #7dd3fc 52%, #facc15 100%)",
    resolution: "3840x2160",
    author: "sample_hiker",
    createdAt: "Today",
  },
  {
    id: "neon-city",
    title: "Neon City Walk",
    subreddit: "Cyberpunk",
    mediaType: "video",
    thumbnail: "linear-gradient(135deg, #111827 0%, #7c3aed 48%, #06b6d4 100%)",
    duration: "00:28",
    author: "sample_runner",
    createdAt: "Yesterday",
  },
  {
    id: "cat-jump",
    title: "Cat Missing the Jump",
    subreddit: "gifs",
    mediaType: "gif",
    thumbnail: "linear-gradient(135deg, #0f766e 0%, #84cc16 54%, #f97316 100%)",
    duration: "Loop",
    author: "sample_loop",
    createdAt: "2 days ago",
  },
  {
    id: "desert-road",
    title: "Desert Road",
    subreddit: "wallpapers",
    mediaType: "image",
    thumbnail: "linear-gradient(135deg, #475569 0%, #f59e0b 50%, #fee2e2 100%)",
    resolution: "2560x1440",
    author: "sample_driver",
    createdAt: "3 days ago",
  },
  {
    id: "ocean-waves",
    title: "Ocean Waves in Slow Motion",
    subreddit: "NatureIsFuckingLit",
    mediaType: "video",
    thumbnail: "linear-gradient(135deg, #0f172a 0%, #0284c7 48%, #a7f3d0 100%)",
    duration: "00:42",
    author: "sample_tide",
    createdAt: "Last week",
  },
  {
    id: "pixel-rain",
    title: "Pixel Art Rain",
    subreddit: "PixelArt",
    mediaType: "gif",
    thumbnail: "linear-gradient(135deg, #1e293b 0%, #2563eb 45%, #f472b6 100%)",
    duration: "Loop",
    author: "sample_pixels",
    createdAt: "Last week",
  },
];

const state = {
  appName: "Media Finder",
  redditUsername: "",
  sidebarCollapsed: false,
  activeMediaFilter: "all",
  sortBy: "relevance",
  selectedIds: new Set(),
  searchQuery: "",
};

const appShell = document.getElementById("app-shell");
const appTitle = document.getElementById("app-title");
const appUsername = document.getElementById("app-username");
const brandMark = document.getElementById("brand-mark");
const sidebarToggle = document.getElementById("sidebar-toggle");
const mobileSidebarToggle = document.getElementById("mobile-sidebar-toggle");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const filterButtons = document.querySelectorAll(".filter-button");
const sortSelect = document.getElementById("sort-select");
const mediaGrid = document.getElementById("media-grid");
const emptyState = document.getElementById("empty-state");
const resultsTitle = document.getElementById("results-title");
const resultSummary = document.getElementById("result-summary");
const sortSummary = document.getElementById("sort-summary");
const backendStatus = document.getElementById("backend-status");
const redditStatus = document.getElementById("reddit-status");

function normalizeUsername(username) {
  if (!username) {
    return "";
  }

  return username.startsWith("/u/") || username.startsWith("u/")
    ? username.replace(/^\/?u\//, "")
    : username;
}

function applyAppConfig() {
  const username = normalizeUsername(state.redditUsername);
  const usernameText = username ? `u/${username}` : "No Reddit username set";
  const brandInitial = state.appName.trim().charAt(0).toUpperCase() || "M";

  document.title = state.appName;
  appTitle.textContent = state.appName;
  appUsername.textContent = usernameText;
  brandMark.textContent = brandInitial;
  brandMark.setAttribute("title", state.appName);
  appTitle.closest(".sidebar-brand").setAttribute(
    "title",
    `${state.appName} - ${usernameText}`,
  );
}

async function loadAppConfig() {
  try {
    const response = await fetch("/api/app-config");
    if (!response.ok) {
      throw new Error("App config request failed");
    }

    const config = await response.json();
    state.appName = config.app_name || state.appName;
    state.redditUsername = config.reddit_username || "";
  } catch (error) {
    state.redditUsername = "";
  }

  applyAppConfig();
}

function loadSavedSidebarState() {
  state.sidebarCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
  applySidebarState();
}

function applySidebarState() {
  appShell.classList.toggle("sidebar-collapsed", state.sidebarCollapsed);
  const action = state.sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar";
  sidebarToggle.setAttribute("aria-label", action);
  sidebarToggle.setAttribute("title", action);
}

function toggleSidebar() {
  state.sidebarCollapsed = !state.sidebarCollapsed;
  localStorage.setItem("sidebarCollapsed", String(state.sidebarCollapsed));
  applySidebarState();
}

function setStatus(element, label, status) {
  const normalized = status.toLowerCase();
  const dot = element.querySelector(".status-dot");
  const text = element.querySelector(".status-text");

  dot.className = `status-dot ${normalized}`;
  text.textContent = status;
  element.setAttribute("title", `${label}: ${status}`);
}

async function checkBackendHealth() {
  setStatus(backendStatus, "Backend API", "Checking");

  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error("Health check failed");
  }

  const data = await response.json();
  if (data.status !== "ok") {
    throw new Error("Unexpected health response");
  }

  setStatus(backendStatus, "Backend API", "Online");
}

async function checkRedditConnection() {
  setStatus(redditStatus, "Reddit API", "Checking");

  const response = await fetch("/api/reddit/test");
  const data = await response.json();

  if (!response.ok || data.status !== "ok") {
    throw new Error("Reddit API connection failed");
  }

  setStatus(redditStatus, "Reddit API", "Online");
}

async function checkConnections() {
  try {
    await checkBackendHealth();
  } catch (error) {
    setStatus(backendStatus, "Backend API", "Failed");
    setStatus(redditStatus, "Reddit API", "Failed");
    return;
  }

  try {
    await checkRedditConnection();
  } catch (error) {
    setStatus(redditStatus, "Reddit API", "Failed");
  }
}

function getVisibleMedia() {
  if (state.activeMediaFilter === "all") {
    return sampleMedia;
  }

  return sampleMedia.filter((item) => item.mediaType === state.activeMediaFilter);
}

function getMediaDetail(item) {
  return item.resolution || item.duration || "";
}

function createMediaCard(item) {
  const article = document.createElement("article");
  article.className = "media-card";
  article.classList.toggle("selected", state.selectedIds.has(item.id));
  article.style.setProperty("--thumb-bg", item.thumbnail);

  const thumbnail = document.createElement("div");
  thumbnail.className = "thumbnail";

  const badge = document.createElement("span");
  badge.className = "media-badge";
  badge.textContent = item.mediaType;

  const selectWrap = document.createElement("label");
  selectWrap.className = "select-wrap";
  selectWrap.setAttribute("title", `Select ${item.title}`);

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = state.selectedIds.has(item.id);
  checkbox.setAttribute("aria-label", `Select ${item.title}`);
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) {
      state.selectedIds.add(item.id);
    } else {
      state.selectedIds.delete(item.id);
    }
    updateSelectionCount();
    article.classList.toggle("selected", checkbox.checked);
  });

  const thumbnailLabel = document.createElement("span");
  thumbnailLabel.textContent = item.mediaType;

  const body = document.createElement("div");
  body.className = "card-body";

  const title = document.createElement("h2");
  title.textContent = item.title;

  const subreddit = document.createElement("p");
  subreddit.className = "subreddit";
  subreddit.textContent = `r/${item.subreddit}`;

  const meta = document.createElement("div");
  meta.className = "media-meta";

  const mediaType = document.createElement("span");
  mediaType.textContent = item.mediaType.charAt(0).toUpperCase() + item.mediaType.slice(1);

  const detail = document.createElement("span");
  detail.textContent = getMediaDetail(item);

  const footnote = document.createElement("p");
  footnote.className = "card-footnote";

  const author = document.createElement("span");
  author.textContent = `by ${item.author}`;

  const createdAt = document.createElement("span");
  createdAt.textContent = item.createdAt;

  selectWrap.appendChild(checkbox);
  thumbnail.append(badge, selectWrap, thumbnailLabel);
  meta.append(mediaType, detail);
  footnote.append(author, createdAt);
  body.append(title, subreddit, meta, footnote);
  article.append(thumbnail, body);

  return article;
}

function renderMediaGrid() {
  const visibleMedia = getVisibleMedia();
  mediaGrid.replaceChildren(...visibleMedia.map(createMediaCard));
  mediaGrid.hidden = visibleMedia.length === 0;
  emptyState.hidden = visibleMedia.length > 0;
  updateSelectionCount();
}

function applyMediaFilter(filter) {
  state.activeMediaFilter = filter;

  filterButtons.forEach((button) => {
    const isActive = button.dataset.filter === filter;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });

  renderMediaGrid();
}

function updateSelectionCount() {
  const visibleMedia = getVisibleMedia();
  const selectedVisible = visibleMedia.filter((item) => state.selectedIds.has(item.id)).length;
  const resultWord = visibleMedia.length === 1 ? "result" : "results";

  resultSummary.textContent = `${visibleMedia.length} sample ${resultWord} - ${selectedVisible} selected`;
}

function updateResultHeading() {
  resultsTitle.textContent = state.searchQuery
    ? `Showing sample results for "${state.searchQuery}"`
    : "Browse sample media";
}

function updateSortSummary() {
  const selectedOption = sortSelect.options[sortSelect.selectedIndex];
  sortSummary.textContent = `Sorted by ${selectedOption.textContent}`;
}

function handleSearchSubmit(event) {
  event.preventDefault();
  state.searchQuery = searchInput.value.trim();
  updateResultHeading();
}

function bindEvents() {
  sidebarToggle.addEventListener("click", toggleSidebar);
  mobileSidebarToggle.addEventListener("click", toggleSidebar);
  searchForm.addEventListener("submit", handleSearchSubmit);

  filterButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.classList.contains("active")));
    button.addEventListener("click", () => applyMediaFilter(button.dataset.filter));
  });

  sortSelect.addEventListener("change", () => {
    state.sortBy = sortSelect.value;
    updateSortSummary();
  });
}

function init() {
  loadSavedSidebarState();
  bindEvents();
  loadAppConfig();
  updateResultHeading();
  updateSortSummary();
  renderMediaGrid();
  checkConnections();
}

window.addEventListener("load", init);

import { fetchAppConfig } from "./api/healthApi.js";
import { elements } from "./config.js";
import { checkConnections, initializeConnectionsPage } from "./pages/connectionsPage.js";
import { initializeDownloadsPage } from "./pages/downloadsPage.js";
import { initializeHistoryPage } from "./pages/historyPage.js";
import { initializeSearchPage } from "./pages/searchPage.js";
import { initializeSettingsPage } from "./pages/settingsPage.js";
import { initializeSidebar, renderActivePage } from "./handlers/sidebarHandlers.js";
import { state } from "./state.js";
import { normalizeUsername } from "./utils/formatting.js";


function applyAppConfig() {
  const username = normalizeUsername(state.redditUsername);
  const usernameText = username ? `u/${username}` : "No Reddit username set";
  const brandInitial = state.appName.trim().charAt(0).toUpperCase() || "M";

  document.title = state.appName;
  elements.appTitle.textContent = state.appName;
  elements.appUsername.textContent = usernameText;
  elements.brandMark.textContent = brandInitial;
  elements.brandMark.setAttribute("title", state.appName);
  elements.appTitle.closest(".sidebar-brand").setAttribute(
    "title",
    `${state.appName} - ${usernameText}`,
  );
}


async function loadAppConfig() {
  try {
    const config = await fetchAppConfig();
    state.appName = config.app_name || state.appName;
    state.redditUsername = config.reddit_username || "";
  } catch (error) {
    state.redditUsername = "";
  }
  applyAppConfig();
}


function init() {
  initializeSidebar(elements, () => renderActivePage(elements));
  initializeSearchPage(elements);
  initializeConnectionsPage(elements);
  initializeDownloadsPage();
  initializeHistoryPage();
  initializeSettingsPage();
  renderActivePage(elements);
  loadAppConfig();
  checkConnections(elements);
}


window.addEventListener("load", init);

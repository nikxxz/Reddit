import { fetchHealth } from "../api/healthApi.js";
import { testRedditConnection } from "../api/redditApi.js";
import { renderConnectionsPage, renderSidebarStatus } from "../renderers/statusRenderer.js";
import { state } from "../state.js";


export function initializeConnectionsPage(elements) {
  elements.retryConnectionsButton.addEventListener("click", () => checkConnections(elements));
}


export async function checkConnections(elements) {
  state.connections.backend = "Checking";
  state.connections.reddit = "Checking";
  state.connections.redditReadOnly = null;
  renderSidebarStatus(elements, state);
  renderConnectionsPage(elements, state);

  try {
    const health = await fetchHealth();
    if (health.status !== "ok") {
      throw new Error("Unexpected health response");
    }
    state.connections.backend = "Online";
  } catch (error) {
    state.connections.backend = "Failed";
    state.connections.reddit = "Failed";
    renderSidebarStatus(elements, state);
    renderConnectionsPage(elements, state);
    return;
  }

  try {
    const reddit = await testRedditConnection();
    if (reddit.status !== "ok") {
      throw new Error("Reddit API connection failed");
    }
    state.connections.reddit = "Online";
    state.connections.redditReadOnly = Boolean(reddit.reddit?.read_only);
  } catch (error) {
    state.connections.reddit = "Failed";
    state.connections.redditReadOnly = null;
  }

  renderSidebarStatus(elements, state);
  renderConnectionsPage(elements, state);
}

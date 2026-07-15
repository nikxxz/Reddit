import { fetchHealth } from "../api/healthApi.js";
import {
  getRedditAuthStatus,
  logoutRedditAuth,
  startRedditAuth,
  testRedditConnection,
} from "../api/redditApi.js";
import { renderConnectionsPage, renderSidebarStatus } from "../renderers/statusRenderer.js";
import { state } from "../state.js";


export function initializeConnectionsPage(elements) {
  elements.retryConnectionsButton.addEventListener("click", () => checkConnections(elements));
  elements.redditAuthButton.addEventListener("click", () => handleRedditAuthClick(elements));
  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin) {
      return;
    }
    if (event.data?.type === "reddit-auth-success" || event.data?.type === "reddit-auth-error") {
      refreshRedditAuthStatus(elements);
    }
  });
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
  refreshRedditAuthStatus(elements);
}


export async function refreshRedditAuthStatus(elements) {
  try {
    const status = await getRedditAuthStatus();
    state.redditAuth.connected = Boolean(status.connected);
    state.redditAuth.username = status.username || "";
  } catch (error) {
    state.redditAuth.connected = false;
    state.redditAuth.username = "";
  } finally {
    state.redditAuth.connecting = false;
    renderSidebarStatus(elements, state);
  }
}


async function handleRedditAuthClick(elements) {
  if (state.redditAuth.connected) {
    await disconnectReddit(elements);
    return;
  }
  await connectReddit(elements);
}


async function connectReddit(elements) {
  const popup = openCenteredPopup("about:blank");
  if (!popup) {
    state.redditAuth.connecting = false;
    renderSidebarStatus(elements, state);
    return;
  }
  state.redditAuth.connecting = true;
  renderSidebarStatus(elements, state);
  try {
    const data = await startRedditAuth();
    popup.location.href = data.url;
    pollAuthStatus(elements, popup);
  } catch (error) {
    popup.close();
    state.redditAuth.connecting = false;
    renderSidebarStatus(elements, state);
  }
}


async function disconnectReddit(elements) {
  state.redditAuth.connecting = true;
  renderSidebarStatus(elements, state);
  try {
    await logoutRedditAuth();
  } finally {
    state.redditAuth.connected = false;
    state.redditAuth.username = "";
    state.redditAuth.connecting = false;
    renderSidebarStatus(elements, state);
    checkConnections(elements);
  }
}


function openCenteredPopup(url) {
  const width = 640;
  const height = 760;
  const left = Math.max(0, window.screenX + (window.outerWidth - width) / 2);
  const top = Math.max(0, window.screenY + (window.outerHeight - height) / 2);
  return window.open(
    url,
    "reddit-oauth",
    `popup=yes,width=${width},height=${height},left=${left},top=${top}`,
  );
}


function pollAuthStatus(elements, popup) {
  let attempts = 0;
  const interval = window.setInterval(async () => {
    attempts += 1;
    try {
      const status = await getRedditAuthStatus();
      if (status.connected) {
        window.clearInterval(interval);
        state.redditAuth.connected = true;
        state.redditAuth.username = status.username || "";
        state.redditAuth.connecting = false;
        renderSidebarStatus(elements, state);
        checkConnections(elements);
        return;
      }
    } catch {
      // Keep polling while the popup is active.
    }
    if (attempts >= 180 || popup?.closed) {
      window.clearInterval(interval);
      refreshRedditAuthStatus(elements);
    }
  }, 1000);
}

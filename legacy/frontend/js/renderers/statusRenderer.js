function setStatus(element, label, status) {
  const normalized = status.toLowerCase();
  const dot = element.querySelector(".status-dot");
  const text = element.querySelector(".status-text");

  dot.className = `status-dot ${normalized}`;
  text.textContent = status;
  element.setAttribute("title", `${label}: ${status}`);
}


export function renderSidebarStatus(elements, state) {
  setStatus(elements.backendStatus, "Backend API", state.connections.backend);
  setStatus(elements.redditStatus, "Reddit API", state.connections.reddit);
  renderRedditAccount(elements, state);
}


export function renderConnectionsPage(elements, state) {
  elements.connectionBackend.textContent = state.connections.backend;
  elements.connectionReddit.textContent = state.connections.reddit;
  elements.connectionMode.textContent = state.redditAuth.connected
    ? "Authenticated"
    : state.connections.redditReadOnly === true
      ? "Read-only"
      : "Unavailable";
}


export function renderRedditAccount(elements, state) {
  const auth = state.redditAuth;
  elements.appUsername.textContent = auth.connected
    ? `u/${auth.username}`
    : state.redditUsername
      ? `u/${state.redditUsername}`
      : "No Reddit username set";
  elements.redditAuthButton.disabled = auth.connecting;
  elements.redditAccountUsername.textContent = "";
  if (auth.connecting) {
    elements.redditAccountDot.className = "status-dot checking";
    elements.redditAccountStatus.textContent = "Connecting...";
    elements.redditAuthButton.textContent = "Connect Reddit";
    elements.redditAccountPanel.setAttribute("title", "Connecting Reddit account");
    return;
  }
  if (auth.connected) {
    elements.redditAccountDot.className = "status-dot online";
    elements.redditAccountStatus.textContent = "Connected";
    elements.redditAccountUsername.textContent = `u/${auth.username}`;
    elements.redditAuthButton.textContent = "Disconnect";
    elements.redditAccountPanel.setAttribute("title", `Connected to u/${auth.username}`);
    return;
  }
  elements.redditAccountDot.className = "status-dot failed";
  elements.redditAccountStatus.textContent = "Disconnected";
  elements.redditAuthButton.textContent = "Connect Reddit";
  elements.redditAccountPanel.setAttribute("title", "Reddit account not connected");
}

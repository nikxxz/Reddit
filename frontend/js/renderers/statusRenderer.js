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
}


export function renderConnectionsPage(elements, state) {
  elements.connectionBackend.textContent = state.connections.backend;
  elements.connectionReddit.textContent = state.connections.reddit;
  elements.connectionMode.textContent =
    state.connections.redditReadOnly === true ? "Read-only" : "Unavailable";
}

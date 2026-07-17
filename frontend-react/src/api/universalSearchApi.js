import { apiRequest } from "./apiClient";

export function listUniversalProviders({ signal } = {}) {
  return apiRequest("/api/universal/providers", { signal });
}

export function startUniversalSearch(payload, { signal } = {}) {
  return apiRequest("/api/universal/search", {
    method: "POST",
    body: payload,
    signal
  });
}

export function getUniversalSearch(searchId, { signal } = {}) {
  return apiRequest(`/api/universal/search/${searchId}`, { signal });
}

export function loadMorePinterestResults(searchId, { signal } = {}) {
  return apiRequest(`/api/universal/search/${searchId}/providers/pinterest/more`, {
    method: "POST",
    signal
  });
}

export async function importPinterestSession(file, { signal } = {}) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/universal/providers/pinterest/session", {
    method: "POST",
    body: form,
    signal
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail?.detail || "Pinterest cookie import failed.");
  }
  return data;
}

export function testPinterestSession({ signal } = {}) {
  return apiRequest("/api/universal/providers/pinterest/session/test", {
    method: "POST",
    signal
  });
}

export function clearPinterestSession({ signal } = {}) {
  return apiRequest("/api/universal/providers/pinterest/session", {
    method: "DELETE",
    signal
  });
}

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


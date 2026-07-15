import { apiRequest } from "./apiClient";

export function getRedditConnectionStatus({ signal } = {}) {
  return apiRequest("/api/reddit/test", { signal });
}

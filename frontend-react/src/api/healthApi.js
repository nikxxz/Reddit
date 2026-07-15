import { apiRequest } from "./apiClient";

export function getBackendHealth({ signal } = {}) {
  return apiRequest("/api/health", { signal });
}

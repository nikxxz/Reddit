import { apiRequest } from "./apiClient";

export function startDownload(payload, { signal } = {}) {
  return apiRequest("/api/downloads", {
    method: "POST",
    body: payload,
    signal
  });
}

export function getDownloadStatus(jobId, { signal } = {}) {
  return apiRequest(`/api/downloads/${jobId}`, { signal });
}

export function cancelDownload(jobId, { signal } = {}) {
  return apiRequest(`/api/downloads/${jobId}/cancel`, {
    method: "POST",
    signal
  });
}

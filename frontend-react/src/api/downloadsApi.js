import { apiRequest } from "./apiClient";

export function startDownload(payload, { signal } = {}) {
  return apiRequest("/api/downloads", {
    method: "POST",
    body: payload,
    signal
  });
}

export function listDownloads(status = "all", { signal } = {}) {
  const query = status && status !== "all" ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest(`/api/downloads${query}`, { signal });
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

export function retryDownload(jobId, { signal } = {}) {
  return apiRequest(`/api/downloads/${jobId}/retry`, {
    method: "POST",
    signal
  });
}

export function clearTerminalDownloads({ signal } = {}) {
  return apiRequest("/api/downloads/terminal", {
    method: "DELETE",
    signal
  });
}

export function clearDownloads(statuses, { signal } = {}) {
  return apiRequest("/api/downloads/clear", {
    method: "POST",
    body: { statuses },
    signal
  });
}

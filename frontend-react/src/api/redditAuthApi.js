import { apiRequest } from "./apiClient";

export async function getRedditAuthStatus({ signal } = {}) {
  const data = await apiRequest("/api/reddit/auth/status", { signal });

  return {
    connected: Boolean(data?.connected),
    username: data?.username || null,
    readOnly: data?.connected ? Boolean(data?.read_only) : true
  };
}

export async function getRedditLoginUrl({ frontendOrigin, signal } = {}) {
  const searchParams = new URLSearchParams();

  if (frontendOrigin) {
    searchParams.set("frontend_origin", frontendOrigin);
  }

  const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
  const data = await apiRequest(`/api/reddit/auth/login${suffix}`, { signal });
  const url = data?.authorization_url || data?.url;

  if (!url) {
    throw new Error("Unable to start Reddit login.");
  }

  return url;
}

export function logoutRedditAccount({ signal } = {}) {
  return apiRequest("/api/reddit/auth/logout", {
    method: "POST",
    signal
  });
}

import { requestJson } from "./client.js";


export function testRedditConnection() {
  return requestJson("/api/reddit/test");
}


export function getRedditAuthStatus() {
  return requestJson("/api/reddit/auth/status");
}


export function startRedditAuth() {
  return requestJson("/api/reddit/auth/login");
}


export function logoutRedditAuth() {
  return requestJson("/api/reddit/auth/logout", { method: "POST" });
}


export function searchRedditMedia(params) {
  const searchParams = new URLSearchParams({
    q: params.query,
    media_type: params.mediaType,
    sort: params.sort,
    time_filter: params.timeFilter || "all",
    limit: String(params.limit || 24),
  });
  if (params.subreddit) {
    searchParams.set("subreddit", params.subreddit);
  }
  if (params.after) {
    searchParams.set("after", params.after);
  }
  searchParams.set("include_nsfw", String(Boolean(params.includeNsfw)));
  return requestJson(`/api/reddit/search?${searchParams.toString()}`, {
    signal: params.signal,
    timeoutMs: params.timeoutMs || 25000,
  });
}

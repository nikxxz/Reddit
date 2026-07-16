import { apiRequest } from "./apiClient";

const MEDIA_TYPE_MAP = {
  all: "all",
  images: "image",
  videos: "video",
  gifs: "gif",
  gallery: "gallery"
};

export function normalizeEntityQuery(value = "") {
  return value.trim().replace(/^\/?[ru]\//i, "").trim();
}

export function buildEntitySearchParams(query, limit = 20) {
  const params = new URLSearchParams();
  params.set("q", normalizeEntityQuery(query));
  params.set("limit", String(limit));
  return params;
}

export async function searchRedditEntities(query, { signal } = {}) {
  const params = buildEntitySearchParams(query);
  const data = await apiRequest(`/api/reddit/entities/search?${params.toString()}`, { signal });
  return {
    query: data?.query || normalizeEntityQuery(query),
    subreddits: Array.isArray(data?.subreddits) ? data.subreddits : [],
    users: Array.isArray(data?.users) ? data.users : []
  };
}

export function buildEntityMediaParams(params = {}) {
  const searchParams = new URLSearchParams();
  searchParams.set("entity_type", params.entityType);
  searchParams.set("entity_name", params.entityName);
  searchParams.set("sort", params.sortBy || "hot");
  searchParams.set("time_filter", params.timeFilter || "all");
  searchParams.set("media_type", MEDIA_TYPE_MAP[params.mediaType] || params.mediaType || "all");
  searchParams.set("include_nsfw", params.includeNsfw ? "true" : "false");
  searchParams.set("limit", String(params.limit || 24));
  if (params.cursor) {
    searchParams.set("cursor", params.cursor);
  }
  return searchParams;
}

export async function browseRedditEntityMedia(params, { signal } = {}) {
  const searchParams = buildEntityMediaParams(params);
  const data = await apiRequest(`/api/reddit/media?${searchParams.toString()}`, { signal });
  return {
    ...data,
    items: Array.isArray(data?.items) ? data.items : [],
    count: Number.isFinite(data?.count) ? data.count : data?.items?.length || 0,
    next_cursor: data?.next_cursor || null,
    has_more: Boolean(data?.has_more)
  };
}

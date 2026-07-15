import { apiRequest } from "./apiClient";

const MEDIA_TYPE_MAP = {
  all: "all",
  images: "image",
  videos: "video",
  gifs: "gif",
  gallery: "gallery"
};

const SORT_MAP = {
  relevance: "relevance",
  new: "new",
  top: "top",
  hot: "hot"
};

const TIME_FILTER_MAP = {
  all: "all",
  day: "day",
  today: "day",
  week: "week",
  month: "month",
  year: "year"
};

export function buildRedditSearchParams(params = {}) {
  const searchParams = new URLSearchParams();
  const query = params.query?.trim() || params.q?.trim() || "";
  const subreddit = (params.subreddit || "").trim().replace(/^r\//i, "");
  const mediaType = MEDIA_TYPE_MAP[params.mediaType] || params.media_type || "all";
  const sort = SORT_MAP[params.sortBy] || params.sort || "relevance";
  const timeFilter =
    TIME_FILTER_MAP[params.timeFilter] || params.time_filter || "all";
  const limit = params.limit || 24;

  if (query) {
    searchParams.set("q", query);
  }

  if (subreddit) {
    searchParams.set("subreddit", subreddit);
  }

  searchParams.set("media_type", mediaType);
  searchParams.set("sort", sort);
  searchParams.set("time_filter", timeFilter);
  searchParams.set("include_nsfw", params.includeNsfw ? "true" : "false");
  searchParams.set("limit", String(limit));

  if (params.after) {
    searchParams.set("after", params.after);
  }

  return searchParams;
}

export async function searchRedditMedia(params, { signal } = {}) {
  const searchParams = buildRedditSearchParams(params);
  const data = await apiRequest(`/api/reddit/search?${searchParams.toString()}`, {
    signal
  });

  return {
    ...data,
    items: Array.isArray(data?.items) ? data.items : [],
    count: Number.isFinite(data?.count) ? data.count : data?.items?.length || 0,
    next_after: data?.next_after || null
  };
}

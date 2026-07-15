export function normalizeUsername(username) {
  if (!username) {
    return "";
  }
  return username.startsWith("/u/") || username.startsWith("u/")
    ? username.replace(/^\/?u\//, "")
    : username;
}


export function normalizeSubreddit(value) {
  let cleaned = value.trim();
  try {
    const parsed = new URL(cleaned);
    if (
      ["reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com"].includes(
        parsed.hostname.toLowerCase(),
      )
    ) {
      cleaned = parsed.pathname;
    }
  } catch {
    // Treat non-URL input as a subreddit name or r/name path.
  }
  return cleaned.trim().replace(/^\/?r\//i, "").replace(/^\/+|\/+$/g, "");
}


export function formatMediaDetail(item) {
  if (item.media_type === "gallery") {
    const count = item.gallery_count || 0;
    return count ? `${count} ${count === 1 ? "item" : "items"}` : "Gallery";
  }
  if (item.width && item.height) {
    return `${item.width}x${item.height}`;
  }
  if (item.duration) {
    const minutes = Math.floor(item.duration / 60);
    const seconds = item.duration % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  if (item.media_type === "gif") {
    return "Loop";
  }
  return "";
}

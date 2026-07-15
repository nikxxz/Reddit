export function normalizeUsername(username) {
  if (!username) {
    return "";
  }
  return username.startsWith("/u/") || username.startsWith("u/")
    ? username.replace(/^\/?u\//, "")
    : username;
}


export function normalizeSubreddit(value) {
  return value.trim().replace(/^\/?r\//i, "");
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

const MEDIA_LABELS = {
  image: "Image",
  video: "Video",
  gif: "GIF",
  gallery: "Gallery",
  external: "External"
};

export function getMediaTypeLabel(type) {
  return MEDIA_LABELS[type] || "Media";
}

export function formatDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return null;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);

  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

export function formatCreatedDate(timestamp) {
  if (!Number.isFinite(timestamp)) {
    return null;
  }

  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric"
  }).format(new Date(timestamp * 1000));
}

export function getDimensionText(item) {
  if (item.width && item.height) {
    return `${item.width} x ${item.height}`;
  }

  return null;
}

export function getCompactMetadata(item) {
  const parts = [];
  const dimensions = getDimensionText(item);
  const duration = formatDuration(item.duration);

  if (item.media_type === "gallery" && item.gallery_count) {
    parts.push(`${item.gallery_count} items`);
  } else if (duration) {
    parts.push(duration);
  } else if (dimensions) {
    parts.push(dimensions);
  } else if (item.media_type === "external") {
    parts.push("External media");
  }

  const createdDate = formatCreatedDate(item.created_utc);

  if (createdDate) {
    parts.push(createdDate);
  }

  return parts.join(" - ");
}

export function getModalMetadata(item) {
  return [
    getMediaTypeLabel(item.media_type),
    getDimensionText(item),
    formatDuration(item.duration),
    item.gallery_count ? `${item.gallery_count} items` : null,
    formatCreatedDate(item.created_utc)
  ].filter(Boolean);
}

export function getMediaUrls(item) {
  const urls = Array.isArray(item.media_urls) ? item.media_urls : [];
  const primaryUrl = item.media_url || item.thumbnail_url;
  const allUrls = primaryUrl ? [primaryUrl, ...urls] : urls;

  return Array.from(new Set(allUrls)).filter(isSafeHttpUrl);
}

export function getPrimaryMediaUrl(item) {
  return getMediaUrls(item)[0] || getSafeHttpUrl(item.thumbnail_url);
}

export function getThumbnailUrl(item) {
  if (item.media_type === "gallery") {
    const galleryUrl = Array.isArray(item.media_urls) ? item.media_urls[0] : null;
    return getSafeHttpUrl(galleryUrl) || getSafeHttpUrl(item.thumbnail_url);
  }

  if (item.media_type === "video" || item.media_type === "external") {
    return getSafeHttpUrl(item.thumbnail_url);
  }

  return getSafeHttpUrl(item.thumbnail_url) || getPrimaryMediaUrl(item);
}

export function getRedditUrl(item) {
  const candidate = item.permalink || item.post_url;

  if (!candidate) {
    return null;
  }

  if (candidate.startsWith("/")) {
    return `https://www.reddit.com${candidate}`;
  }

  return getSafeHttpUrl(candidate);
}

export function getSafeHttpUrl(url) {
  return isSafeHttpUrl(url) ? url : null;
}

export function isSafeHttpUrl(url) {
  if (!url || typeof url !== "string") {
    return false;
  }

  try {
    const parsed = new URL(url, window.location.origin);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export function isVideoUrl(url) {
  return /\.(mp4|webm|ogg)(\?|#|$)/i.test(url || "");
}

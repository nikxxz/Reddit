import { toggleSelection } from "../handlers/selectionHandlers.js";
import { formatRedditDate } from "../utils/dates.js";
import { formatMediaDetail } from "../utils/formatting.js";
import { isSafeHttpUrl } from "../utils/urls.js";


function renderThumbnail(container, item) {
  container.style.removeProperty("--thumb-bg");
  const label = document.createElement("span");
  label.className = "thumbnail-label";
  label.textContent = item.media_type;

  if (isSafeHttpUrl(item.thumbnail_url)) {
    container.classList.add("thumbnail-loading", "has-image");
    container.appendChild(label);
    const image = document.createElement("img");
    image.alt = "";
    image.loading = "lazy";
    image.referrerPolicy = "no-referrer";
    image.addEventListener("load", () => {
      container.classList.remove("thumbnail-loading");
      container.classList.add("thumbnail-loaded");
    });
    image.addEventListener("error", () => {
      image.remove();
      container.classList.remove("thumbnail-loading", "has-image");
      container.classList.add("thumbnail-failed");
      label.textContent = `${item.media_type} unavailable`;
    });
    image.src = item.thumbnail_url;
    container.appendChild(image);
    return;
  }

  container.classList.add("thumbnail-failed");
  container.style.setProperty(
    "--thumb-bg",
    item.thumbnail || "linear-gradient(135deg, #475569 0%, #94a3b8 100%)",
  );
  container.appendChild(label);
}


export function createMediaCard(item, options) {
  const article = document.createElement("article");
  article.className = "media-card";
  article.classList.toggle("selected", options.selectedIds.has(item.id));

  const thumbnail = document.createElement("div");
  thumbnail.className = "thumbnail";

  const badge = document.createElement("span");
  badge.className = "media-badge";
  badge.textContent = item.media_type;

  const nsfwBadge = document.createElement("span");
  nsfwBadge.className = "nsfw-badge";
  nsfwBadge.textContent = "NSFW";

  const selectWrap = document.createElement("label");
  selectWrap.className = "select-wrap";
  selectWrap.setAttribute("title", `Select ${item.title}`);

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = options.selectedIds.has(item.id);
  checkbox.setAttribute("aria-label", `Select ${item.title}`);
  checkbox.addEventListener("change", () => {
    toggleSelection(item.id, checkbox.checked);
    article.classList.toggle("selected", checkbox.checked);
    options.onSelectionChange();
  });

  const body = document.createElement("div");
  body.className = "card-body";

  const title = document.createElement("h2");
  title.textContent = item.title || "Untitled Reddit post";

  const subreddit = document.createElement("p");
  subreddit.className = "subreddit";
  subreddit.textContent = item.subreddit ? `r/${item.subreddit}` : "r/unknown";

  const meta = document.createElement("p");
  meta.className = "media-meta";
  const detail = formatMediaDetail(item);
  meta.textContent = [detail, formatRedditDate(item)].filter(Boolean).join(" · ");

  selectWrap.appendChild(checkbox);
  renderThumbnail(thumbnail, item);
  thumbnail.append(badge);
  if (item.is_nsfw) {
    thumbnail.append(nsfwBadge);
  }
  thumbnail.append(selectWrap);
  body.append(title, subreddit, meta);
  article.append(thumbnail, body);
  return article;
}

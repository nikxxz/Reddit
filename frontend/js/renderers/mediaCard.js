import { toggleSelection } from "../handlers/selectionHandlers.js";
import { formatRedditDate } from "../utils/dates.js";
import { formatMediaDetail } from "../utils/formatting.js";
import { isSafeHttpUrl } from "../utils/urls.js";


function renderThumbnail(container, item) {
  container.style.removeProperty("--thumb-bg");
  container.classList.toggle("has-image", isSafeHttpUrl(item.thumbnail_url));

  if (isSafeHttpUrl(item.thumbnail_url)) {
    const image = document.createElement("img");
    image.src = item.thumbnail_url;
    image.alt = "";
    image.loading = "lazy";
    image.referrerPolicy = "no-referrer";
    container.appendChild(image);
    return;
  }

  container.style.setProperty(
    "--thumb-bg",
    item.thumbnail || "linear-gradient(135deg, #475569 0%, #94a3b8 100%)",
  );
  const thumbnailLabel = document.createElement("span");
  thumbnailLabel.className = "thumbnail-label";
  thumbnailLabel.textContent = item.media_type;
  container.appendChild(thumbnailLabel);
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

  const meta = document.createElement("div");
  meta.className = "media-meta";

  const mediaType = document.createElement("span");
  mediaType.textContent = item.media_type.charAt(0).toUpperCase() + item.media_type.slice(1);

  const detail = document.createElement("span");
  detail.textContent = formatMediaDetail(item);

  const footnote = document.createElement("p");
  footnote.className = "card-footnote";

  const author = document.createElement("span");
  author.textContent = `by ${item.author || "[deleted]"}`;

  const createdAt = document.createElement("span");
  createdAt.textContent = formatRedditDate(item);

  selectWrap.appendChild(checkbox);
  renderThumbnail(thumbnail, item);
  thumbnail.append(badge, selectWrap);
  meta.append(mediaType, detail);
  footnote.append(author, createdAt);
  body.append(title, subreddit, meta, footnote);
  article.append(thumbnail, body);
  return article;
}

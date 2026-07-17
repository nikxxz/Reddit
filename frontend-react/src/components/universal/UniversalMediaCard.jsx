import { Badge, Group, Paper, Stack, Text } from "@mantine/core";
import {
  getCompactMetadata,
  getMediaTypeLabel,
  getThumbnailUrl
} from "../media/MediaMetadata";
import { MediaThumbnail } from "../media/MediaThumbnail";
import { providerDisplayName } from "./providerDisplay";

function toPreviewItem(item) {
  return {
    id: `${item.provider}:${item.provider_item_id}`,
    title: item.title,
    media_type: item.media_type,
    thumbnail_url: item.thumbnail_url,
    media_url: item.preview_url,
    media_urls: item.media_urls || [],
    width: item.width,
    height: item.height,
    duration: item.duration_seconds,
    gallery_count: item.media_count,
    created_utc: item.created_at ? Date.parse(item.created_at) / 1000 : null
  };
}

export function UniversalMediaCard({ item, onOpen, compact = false }) {
  const previewItem = toPreviewItem(item);
  const metadata = getCompactMetadata(previewItem);
  const collectionLabel = [providerDisplayName(item.provider), item.collection]
    .filter(Boolean)
    .join(" - ");

  const handleKeyDown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(item);
    }
  };

  return (
    <Paper
      className={`media-card universal-media-card ${compact ? "media-card-compact" : ""}`}
      role="button"
      tabIndex={0}
      onClick={() => onOpen(item)}
      onKeyDown={handleKeyDown}
      aria-label={`Open ${providerDisplayName(item.provider)} result ${item.title}`}
    >
      <div className="media-card-preview">
        <MediaThumbnail
          item={previewItem}
          src={getThumbnailUrl(previewItem)}
          alt={`${getMediaTypeLabel(item.media_type)} preview for ${item.title}`}
        />
        <Group className="media-card-badges" gap={6}>
          <Badge size="xs" variant="filled" aria-label={`Provider ${providerDisplayName(item.provider)}`}>
            {providerDisplayName(item.provider)}
          </Badge>
          <Badge size="xs" variant="filled">
            {getMediaTypeLabel(item.media_type)}
          </Badge>
          {item.media_count ? (
            <Badge size="xs" color="gray" variant="filled">
              {item.media_count}
            </Badge>
          ) : null}
          {item.nsfw ? (
            <Badge size="xs" color="red" variant="filled">
              NSFW
            </Badge>
          ) : null}
        </Group>
      </div>

      <Stack className="media-card-body" gap={5}>
        <Text className="media-card-title" fw={650} lineClamp={compact ? 3 : 2}>
          {item.title || "Untitled result"}
        </Text>
        <Text size="sm" c="gray.6" truncate>
          {collectionLabel || providerDisplayName(item.provider)}
        </Text>
        <Text className="media-card-meta" size="xs" c="gray.6" lineClamp={1}>
          {metadata || getMediaTypeLabel(item.media_type)}
        </Text>
      </Stack>
    </Paper>
  );
}

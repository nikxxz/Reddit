import { Badge, Group, Paper, Stack, Text } from "@mantine/core";
import { GalleryCardCarousel } from "./GalleryCardCarousel";
import {
  getCompactMetadata,
  getMediaTypeLabel,
  getThumbnailUrl
} from "./MediaMetadata";
import { MediaThumbnail } from "./MediaThumbnail";

function shouldUseCardCarousel(item, compact) {
  return (
    !compact &&
    item.media_type === "gallery" &&
    Array.isArray(item.media_urls) &&
    item.media_urls.length > 1
  );
}

export function MediaCard({ item, onOpen, compact = false }) {
  const metadata = getCompactMetadata(item);

  const handleKeyDown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(item);
    }
  };

  return (
    <Paper
      className={`media-card ${compact ? "media-card-compact" : ""}`}
      role="button"
      tabIndex={0}
      withBorder
      onClick={() => onOpen(item)}
      onKeyDown={handleKeyDown}
    >
      <div className="media-card-preview">
        {shouldUseCardCarousel(item, compact) ? (
          <GalleryCardCarousel item={item} />
        ) : (
          <MediaThumbnail
            item={item}
            src={getThumbnailUrl(item)}
            alt={`${getMediaTypeLabel(item.media_type)} preview for ${item.title}`}
          />
        )}
        <Group className="media-card-badges" gap={6}>
          <Badge size="xs" variant="filled">
            {getMediaTypeLabel(item.media_type)}
          </Badge>
          {item.gallery_count ? (
            <Badge size="xs" color="gray" variant="filled">
              {item.gallery_count}
            </Badge>
          ) : null}
          {item.is_nsfw ? (
            <Badge size="xs" color="red" variant="filled">
              NSFW
            </Badge>
          ) : null}
        </Group>
      </div>

      <Stack className="media-card-body" gap={5}>
        <Text className="media-card-title" fw={650} lineClamp={compact ? 3 : 2}>
          {item.title || "Untitled Reddit post"}
        </Text>
        <Text size="sm" c="gray.6" truncate>
          {item.subreddit ? `r/${item.subreddit}` : "Reddit"}
        </Text>
        <Text className="media-card-meta" size="xs" c="gray.6" lineClamp={1}>
          {metadata || getMediaTypeLabel(item.media_type)}
        </Text>
      </Stack>
    </Paper>
  );
}

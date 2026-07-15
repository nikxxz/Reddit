import { Badge, Image, Paper, Stack, Text } from "@mantine/core";
import { useState } from "react";

const MEDIA_LABELS = {
  image: "Image",
  video: "Video",
  gif: "GIF",
  gallery: "Gallery",
  external: "External",
  all: "Media"
};

function getMetaText(item) {
  const parts = [MEDIA_LABELS[item.media_type] || item.media_type || "Media"];

  if (item.width && item.height) {
    parts.push(`${item.width}x${item.height}`);
  }

  if (item.duration) {
    parts.push(`${item.duration}s`);
  }

  if (item.gallery_count) {
    parts.push(`${item.gallery_count} items`);
  }

  return parts.join(" · ");
}

export function SearchResultItem({ item }) {
  const [hasImageError, setHasImageError] = useState(false);
  const mediaLabel = MEDIA_LABELS[item.media_type] || "Media";
  const hasThumbnail = Boolean(item.thumbnail_url) && !hasImageError;

  return (
    <Paper className="search-result-row" withBorder p="sm" radius="md">
      <div className="search-result-thumb" aria-hidden={hasThumbnail ? undefined : "true"}>
        {hasThumbnail ? (
          <Image
            alt={`Thumbnail for ${item.title}`}
            className="search-result-image"
            fit="cover"
            h="100%"
            loading="lazy"
            src={item.thumbnail_url}
            w="100%"
            onError={() => setHasImageError(true)}
          />
        ) : (
          <div className="search-result-thumb-placeholder">{mediaLabel}</div>
        )}
      </div>
      <Stack className="search-result-content" gap={4}>
        <Text className="search-result-title" fw={600} lineClamp={2}>
          {item.title || "Untitled Reddit post"}
        </Text>
        <Text size="sm" c="gray.6">
          {item.subreddit ? `r/${item.subreddit}` : "Reddit"}
        </Text>
        <Text size="sm" c="gray.6">
          {getMetaText(item)}
        </Text>
        {item.is_nsfw ? (
          <Badge className="search-result-badge" color="red" variant="light">
            NSFW
          </Badge>
        ) : null}
      </Stack>
    </Paper>
  );
}

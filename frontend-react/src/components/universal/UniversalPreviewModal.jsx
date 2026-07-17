import { Badge, Button, Group, Modal, Stack, Text, Title } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { IconExternalLink } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { GalleryPreviewCarousel } from "../media/GalleryPreviewCarousel";
import {
  getMediaTypeLabel,
  getModalMetadata,
  getSafeHttpUrl,
  isVideoUrl
} from "../media/MediaMetadata";
import { MediaFallback, MediaThumbnail } from "../media/MediaThumbnail";
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

function PreviewContent({ item }) {
  const previewItem = useMemo(() => toPreviewItem(item), [item]);
  const [videoFailed, setVideoFailed] = useState(false);
  const url = getSafeHttpUrl(item.preview_url);

  useEffect(() => {
    setVideoFailed(false);
  }, [item.provider_item_id, url]);

  if (item.media_type === "gallery") {
    return <GalleryPreviewCarousel item={previewItem} />;
  }

  if ((item.media_type === "video" || item.media_type === "gif") && url && isVideoUrl(url) && !videoFailed) {
    return (
      <video
        className="media-preview-video"
        controls
        loop={item.media_type === "gif"}
        muted={item.media_type === "gif"}
        playsInline
        preload="metadata"
        poster={item.thumbnail_url || undefined}
        onError={() => setVideoFailed(true)}
      >
        <source src={url} />
        Preview unavailable.
      </video>
    );
  }

  if (item.media_type === "video" || item.media_type === "gif") {
    return <UniversalFallback item={item} />;
  }

  if (!url && !item.thumbnail_url) {
    return <UniversalFallback item={item} />;
  }

  return (
    <MediaThumbnail
      item={previewItem}
      src={url || item.thumbnail_url}
      contain
      alt={`${getMediaTypeLabel(item.media_type)} preview for ${item.title}`}
    />
  );
}

function UniversalFallback({ item }) {
  return (
    <Stack className="media-preview-fallback" gap="xs" align="center" justify="center">
      <MediaFallback type={item.media_type} label="Preview unavailable" />
      <Text size="sm">Provider: {providerDisplayName(item.provider)}</Text>
      <Text size="sm">Media type: {getMediaTypeLabel(item.media_type)}</Text>
    </Stack>
  );
}

export function UniversalPreviewModal({ opened, item, onClose }) {
  const isMobile = useMediaQuery("(max-width: 48em)");
  const previewItem = item ? toPreviewItem(item) : null;
  const metadata = previewItem ? getModalMetadata(previewItem) : [];
  const sourceUrl = item ? getSafeHttpUrl(item.canonical_url) : null;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={item?.title || "Universal preview"}
      size="xl"
      fullScreen={isMobile}
      centered={!isMobile}
      closeButtonProps={{ "aria-label": "Close universal media preview" }}
    >
      {item ? (
        <Stack gap="md">
          <div className="media-preview-stage">
            <PreviewContent item={item} />
          </div>

          <Stack className="media-preview-details" gap="xs">
            <Group gap="xs">
              <Badge variant="light">{providerDisplayName(item.provider)}</Badge>
              <Badge variant="light">{getMediaTypeLabel(item.media_type)}</Badge>
              {item.nsfw ? (
                <Badge color="red" variant="light">
                  NSFW
                </Badge>
              ) : null}
            </Group>
            <Title className="media-preview-title" order={3} size="h4">
              {item.title || "Untitled result"}
            </Title>
            <Text size="sm" c="gray.6">
              {[item.collection ? `${providerDisplayName(item.provider)} - ${item.collection}` : providerDisplayName(item.provider), item.author]
                .filter(Boolean)
                .join(" - ")}
            </Text>
            {metadata.length ? (
              <Text size="sm" c="gray.6">
                {metadata.join(" - ")}
              </Text>
            ) : null}
            <div className="media-preview-actions universal-preview-actions">
              {sourceUrl ? (
                <Button
                  className="media-preview-reddit-link"
                  component="a"
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  leftSection={<IconExternalLink size={16} stroke={1.8} />}
                  variant="subtle"
                >
                  Open source
                </Button>
              ) : null}
              <Text size="sm" c="gray.6">
                Universal downloads will be added in a later phase.
              </Text>
            </div>
          </Stack>
        </Stack>
      ) : null}
    </Modal>
  );
}

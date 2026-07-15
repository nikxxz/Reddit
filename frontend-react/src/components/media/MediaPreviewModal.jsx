import { Badge, Button, Group, Modal, Stack, Text, Title } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { IconExternalLink } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { DownloadActions } from "../downloads/DownloadActions";
import { useDownloadJob } from "../../hooks/useDownloadJob";
import { GalleryPreviewCarousel } from "./GalleryPreviewCarousel";
import {
  getMediaTypeLabel,
  getModalMetadata,
  getPrimaryMediaUrl,
  getRedditUrl,
  getThumbnailUrl,
  isVideoUrl
} from "./MediaMetadata";
import { MediaFallback, MediaThumbnail } from "./MediaThumbnail";

function PreviewContent({ item, activeGalleryIndex, onGallerySlideChange }) {
  const url = getPrimaryMediaUrl(item);
  const [videoFailed, setVideoFailed] = useState(false);

  useEffect(() => {
    setVideoFailed(false);
  }, [item.id, url]);

  if (item.media_type === "gallery") {
    return (
      <GalleryPreviewCarousel
        item={item}
        activeSlide={activeGalleryIndex}
        onSlideChange={onGallerySlideChange}
      />
    );
  }

  if (item.media_type === "video" && url && isVideoUrl(url) && !videoFailed) {
    return (
      <video
        className="media-preview-video"
        controls
        preload="metadata"
        poster={getThumbnailUrl(item) || undefined}
        onError={() => setVideoFailed(true)}
      >
        <source src={url} />
        Video preview unavailable.
      </video>
    );
  }

  if (item.media_type === "gif" && url && isVideoUrl(url) && !videoFailed) {
    return (
      <video
        className="media-preview-video"
        controls
        loop
        muted
        playsInline
        preload="metadata"
        poster={getThumbnailUrl(item) || undefined}
        onError={() => setVideoFailed(true)}
      >
        <source src={url} />
        GIF preview unavailable.
      </video>
    );
  }

  if (item.media_type === "video") {
    return <MediaFallback type="video" />;
  }

  if (item.media_type === "gif") {
    return <MediaFallback type="gif" />;
  }

  if (item.media_type === "external") {
    return (
      <Stack className="media-preview-fallback" gap="xs" align="center" justify="center">
        <MediaThumbnail item={item} src={getThumbnailUrl(item)} contain />
        <Text fw={700}>External preview unavailable</Text>
      </Stack>
    );
  }

  return (
    <MediaThumbnail
      item={item}
      src={url}
      contain
      alt={`${getMediaTypeLabel(item.media_type)} preview for ${item.title}`}
    />
  );
}

export function MediaPreviewModal({ opened, item, onClose }) {
  const isMobile = useMediaQuery("(max-width: 48em)");
  const [activeGalleryIndex, setActiveGalleryIndex] = useState(0);
  const downloadJob = useDownloadJob();
  const { reset } = downloadJob;
  const redditUrl = item ? getRedditUrl(item) : null;
  const metadata = item ? getModalMetadata(item) : [];

  useEffect(() => {
    setActiveGalleryIndex(0);
    reset();
  }, [item?.id, reset]);

  const createDownloadPayload = (scope) => {
    if (!item) {
      return null;
    }

    return {
      post_id: item.id,
      gallery_index: item.media_type === "gallery" ? activeGalleryIndex : null,
      download_scope: scope
    };
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={item?.title || "Media preview"}
      size="xl"
      fullScreen={isMobile}
      centered={!isMobile}
      closeButtonProps={{ "aria-label": "Close media preview" }}
    >
      {item ? (
        <Stack gap="md">
          <div className="media-preview-stage">
            <PreviewContent
              item={item}
              activeGalleryIndex={activeGalleryIndex}
              onGallerySlideChange={setActiveGalleryIndex}
            />
          </div>

          <Stack className="media-preview-details" gap="xs">
            <Group gap="xs">
              <Badge variant="light">{getMediaTypeLabel(item.media_type)}</Badge>
              {item.is_nsfw ? (
                <Badge color="red" variant="light">
                  NSFW
                </Badge>
              ) : null}
            </Group>
            <Title className="media-preview-title" order={3} size="h4">
              {item.title || "Untitled Reddit post"}
            </Title>
            <Text size="sm" c="gray.6">
              {[
                item.subreddit ? `r/${item.subreddit}` : null,
                item.author ? `u/${item.author}` : null
              ]
                .filter(Boolean)
                .join(" - ")}
            </Text>
            {metadata.length ? (
              <Text size="sm" c="gray.6">
                {metadata.join(" - ")}
              </Text>
            ) : null}
            <div className="media-preview-actions">
              {redditUrl ? (
                <Button
                  className="media-preview-reddit-link"
                  component="a"
                  href={redditUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  leftSection={<IconExternalLink size={16} stroke={1.8} />}
                  variant="subtle"
                >
                  Open on Reddit
                </Button>
              ) : null}
              <DownloadActions
                item={item}
                downloadJob={downloadJob}
                createPayload={createDownloadPayload}
                className="media-preview-download-actions"
              />
            </div>
          </Stack>
        </Stack>
      ) : null}
    </Modal>
  );
}

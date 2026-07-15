import { Image, Skeleton, Stack, Text, ThemeIcon } from "@mantine/core";
import {
  IconFileUnknown,
  IconPhoto,
  IconPhotoOff,
  IconVideo
} from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { getMediaTypeLabel, getPrimaryMediaUrl, getSafeHttpUrl } from "./MediaMetadata";

function MediaIcon({ type }) {
  const iconProps = { size: 22, stroke: 1.8 };

  if (type === "video" || type === "gif") {
    return <IconVideo {...iconProps} />;
  }

  if (type === "image" || type === "gallery") {
    return <IconPhoto {...iconProps} />;
  }

  if (type === "external") {
    return <IconFileUnknown {...iconProps} />;
  }

  return <IconPhotoOff {...iconProps} />;
}

export function MediaThumbnail({
  item,
  src,
  alt,
  contain = false,
  className = ""
}) {
  const safeSrc = getSafeHttpUrl(src) || getPrimaryMediaUrl(item);
  const [status, setStatus] = useState(safeSrc ? "loading" : "failed");

  useEffect(() => {
    setStatus(safeSrc ? "loading" : "failed");
  }, [safeSrc]);

  return (
    <div className={`media-thumbnail ${contain ? "media-thumbnail-contain" : ""} ${className}`}>
      {safeSrc && status !== "failed" ? (
        <>
          {status === "loading" ? (
            <Skeleton className="media-thumbnail-skeleton" aria-hidden="true" />
          ) : null}
          <Image
            alt={alt || `${getMediaTypeLabel(item.media_type)} preview for ${item.title}`}
            className={`media-thumbnail-image ${status === "loaded" ? "media-thumbnail-image-loaded" : ""}`}
            fit={contain ? "contain" : "cover"}
            loading="lazy"
            src={safeSrc}
            onError={() => setStatus("failed")}
            onLoad={() => setStatus("loaded")}
          />
        </>
      ) : (
        <MediaFallback type={item.media_type} />
      )}
    </div>
  );
}

export function MediaFallback({ type = "image", label }) {
  const fallbackLabel = label || `${getMediaTypeLabel(type)} preview unavailable`;

  return (
    <Stack
      className="media-thumbnail-fallback"
      gap={6}
      align="center"
      justify="center"
      role="img"
      aria-label={fallbackLabel}
    >
      <ThemeIcon color="gray" radius="xl" size="lg" variant="light">
        <MediaIcon type={type} />
      </ThemeIcon>
      <Text size="xs" c="gray.6" ta="center">
        {fallbackLabel}
      </Text>
    </Stack>
  );
}

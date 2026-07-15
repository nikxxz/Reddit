import { Carousel } from "@mantine/carousel";
import { Text } from "@mantine/core";
import { useState } from "react";
import { MediaThumbnail } from "./MediaThumbnail";
import { getMediaUrls } from "./MediaMetadata";

export function GalleryPreviewCarousel({ item, activeSlide, onSlideChange }) {
  const urls = getMediaUrls(item);
  const [internalActiveSlide, setInternalActiveSlide] = useState(0);
  const currentSlide = activeSlide ?? internalActiveSlide;

  const handleSlideChange = (index) => {
    setInternalActiveSlide(index);
    onSlideChange?.(index);
  };

  if (urls.length === 0) {
    return <MediaThumbnail item={item} contain />;
  }

  return (
    <div className="gallery-preview-carousel">
      <Carousel
        height="100%"
        withIndicators={urls.length > 1}
        onSlideChange={handleSlideChange}
        previousControlProps={{ "aria-label": "Previous gallery image" }}
        nextControlProps={{ "aria-label": "Next gallery image" }}
      >
        {urls.map((url, index) => (
          <Carousel.Slide key={`${item.id}-preview-${url}-${index}`}>
            <MediaThumbnail
              item={item}
              src={url}
              contain
              alt={`Gallery image ${index + 1} for ${item.title}`}
            />
          </Carousel.Slide>
        ))}
      </Carousel>
      {urls.length > 1 ? (
        <Text className="gallery-preview-count" size="xs" fw={700}>
          {currentSlide + 1} / {urls.length}
        </Text>
      ) : null}
    </div>
  );
}

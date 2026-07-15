import { Carousel } from "@mantine/carousel";
import { MediaThumbnail } from "./MediaThumbnail";

export function GalleryCardCarousel({ item }) {
  const urls = (Array.isArray(item.media_urls) ? item.media_urls : []).slice(0, 5);

  if (urls.length <= 1) {
    return (
      <MediaThumbnail
        item={item}
        src={urls[0] || item.thumbnail_url}
        alt={`Gallery preview for ${item.title}`}
      />
    );
  }

  return (
    <div
      className="gallery-card-carousel"
      onClick={(event) => event.stopPropagation()}
      onKeyDown={(event) => event.stopPropagation()}
      onPointerDown={(event) => event.stopPropagation()}
    >
      <Carousel
        withIndicators={false}
        height="100%"
        previousControlProps={{ "aria-label": "Previous gallery image" }}
        nextControlProps={{ "aria-label": "Next gallery image" }}
      >
        {urls.map((url, index) => (
          <Carousel.Slide key={`${item.id}-${url}-${index}`}>
            <MediaThumbnail
              item={item}
              src={url}
              alt={`Gallery preview ${index + 1} for ${item.title}`}
            />
          </Carousel.Slide>
        ))}
      </Carousel>
    </div>
  );
}

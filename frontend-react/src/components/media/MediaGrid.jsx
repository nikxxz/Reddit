import { Stack } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { LoadMoreButton } from "../search/LoadMoreButton";
import { MediaCard } from "./MediaCard";

export function MediaGrid({
  items,
  isLoadingMore,
  loadMoreError,
  nextAfter,
  onLoadMore,
  onOpenPreview
}) {
  const compact = useMediaQuery("(max-width: 40em)");
  const hasLoadMore = items.length > 0 && nextAfter;

  return (
    <Stack gap="md">
      <div className="media-grid" data-compact={compact ? "true" : "false"}>
        {items.map((item) => (
          <MediaCard
            compact={compact}
            item={item}
            key={item.id}
            onOpen={onOpenPreview}
          />
        ))}
      </div>
      {hasLoadMore ? (
        <LoadMoreButton
          isLoadingMore={isLoadingMore}
          loadMoreError={loadMoreError}
          onLoadMore={onLoadMore}
        />
      ) : null}
    </Stack>
  );
}

import { Button, Loader, Stack, Text } from "@mantine/core";

export function LoadMoreButton({
  isLoadingMore,
  loadMoreError,
  onLoadMore
}) {
  return (
    <Stack className="load-more-area" gap="xs" align="center">
      {loadMoreError ? (
        <Text size="sm" c="red.7" role="alert">
          {loadMoreError}
        </Text>
      ) : null}
      <Button
        type="button"
        variant="light"
        disabled={isLoadingMore}
        leftSection={isLoadingMore ? <Loader size="xs" /> : null}
        onClick={onLoadMore}
      >
        {isLoadingMore ? "Loading more..." : loadMoreError ? "Retry Load More" : "Load More"}
      </Button>
    </Stack>
  );
}

import { Paper, Skeleton, Stack } from "@mantine/core";

export function SearchLoading() {
  return (
    <Paper
      className="search-results-panel"
      component="section"
      aria-live="polite"
      withBorder
      p={{ base: "md", sm: "lg" }}
      radius="md"
    >
      <div className="media-grid search-loading-grid" aria-hidden="true">
        {Array.from({ length: 8 }, (_, index) => (
          <Stack className="search-result-skeleton-card" gap="xs" key={index}>
            <Skeleton className="search-result-skeleton-preview" radius="sm" />
            <Skeleton height={18} radius="xl" />
            <Skeleton height={14} width="54%" radius="xl" />
            <Skeleton height={14} width="72%" radius="xl" />
          </Stack>
        ))}
      </div>
    </Paper>
  );
}

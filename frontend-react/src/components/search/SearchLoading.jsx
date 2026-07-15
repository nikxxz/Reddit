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
      <Stack gap="sm" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => (
          <div className="search-result-row search-result-skeleton" key={index}>
            <Skeleton className="search-result-thumb" radius="sm" />
            <Stack className="search-result-content" gap="xs">
              <Skeleton height={18} radius="xl" />
              <Skeleton height={14} width="42%" radius="xl" />
              <Skeleton height={14} width="64%" radius="xl" />
            </Stack>
          </div>
        ))}
      </Stack>
    </Paper>
  );
}

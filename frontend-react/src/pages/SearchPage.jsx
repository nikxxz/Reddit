import { Divider, Paper, Stack, Text, Title } from "@mantine/core";
import { useEffect, useRef } from "react";
import { SearchFilters } from "../components/search/SearchFilters";
import { SearchForm } from "../components/search/SearchForm";
import { SearchResults } from "../components/search/SearchResults";
import { useSearchForm } from "../hooks/useSearchForm";
import { useRedditSearch } from "../hooks/useRedditSearch";
import "../styles/search.css";
import "../styles/search-results.css";

export function SearchPage() {
  const {
    values,
    submittedValues,
    submitRevision,
    setFieldValue,
    submitSearch,
    clearFilters
  } = useSearchForm();
  const { state, runSearch, retrySearch, loadMore } = useRedditSearch();
  const lastSubmitRevisionRef = useRef(submitRevision);

  useEffect(() => {
    if (!submittedValues) {
      return undefined;
    }

    if (submitRevision !== lastSubmitRevisionRef.current) {
      lastSubmitRevisionRef.current = submitRevision;
      runSearch(submittedValues);
      return undefined;
    }

    const debounceId = window.setTimeout(() => {
      runSearch(submittedValues);
    }, 300);

    return () => {
      window.clearTimeout(debounceId);
    };
  }, [submittedValues, submitRevision, runSearch]);

  return (
    <Stack className="search-page" gap="md">
      <Paper
        className="search-controls-panel"
        component="section"
        aria-labelledby="search-page-title"
        withBorder
        shadow="xs"
        p={{ base: "md", sm: "lg" }}
        radius="md"
      >
        <Stack gap="md">
          <Stack gap={4}>
            <Title id="search-page-title" order={2} size="h3">
              Search Reddit media
            </Title>
            <Text className="search-page-description" c="gray.6">
              Find images, videos, GIFs, galleries, and external media links.
            </Text>
          </Stack>

          <SearchForm
            values={values}
            onFieldChange={setFieldValue}
            onSubmit={submitSearch}
          />

          <Divider />

          <SearchFilters values={values} onFieldChange={setFieldValue} />
        </Stack>
      </Paper>

      <SearchResults
        state={state}
        onRetry={retrySearch}
        onLoadMore={loadMore}
        onClearFilters={clearFilters}
      />
    </Stack>
  );
}

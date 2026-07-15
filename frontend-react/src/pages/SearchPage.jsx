import { Button, Group, Paper, Popover, Stack, Text, Title } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { IconAdjustmentsHorizontal } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { SearchFilters } from "../components/search/SearchFilters";
import { SearchForm } from "../components/search/SearchForm";
import { SearchResults } from "../components/search/SearchResults";
import { SearchSummary } from "../components/search/SearchSummary";
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
  const isMobile = useMediaQuery("(max-width: 40em)");
  const [filtersExpanded, setFiltersExpanded] = useState(true);
  const [filtersPopoverOpened, setFiltersPopoverOpened] = useState(false);
  const lastSubmitRevisionRef = useRef(submitRevision);
  const keywordInputRef = useRef(null);

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

  useEffect(() => {
    if (!isMobile) {
      setFiltersExpanded(true);
      return;
    }

    if (values.validationError || state.status === "error" || state.status === "idle") {
      setFiltersExpanded(true);
      return;
    }

    if (state.status === "success" || state.status === "empty") {
      setFiltersExpanded(false);
    }
  }, [isMobile, state.status, values.validationError]);

  const handleEditFilters = () => {
    setFiltersExpanded(true);
    window.setTimeout(() => keywordInputRef.current?.focus(), 0);
  };

  const showCollapsedSummary =
    isMobile &&
    !filtersExpanded &&
    (state.status === "success" || state.status === "empty");

  return (
    <Stack className="search-page" gap="md">
      <div className="search-controls-container">
        {showCollapsedSummary ? (
          <SearchSummary
            values={values}
            resultCount={state.items.length}
            onEdit={handleEditFilters}
          />
        ) : null}

        {!showCollapsedSummary ? (
          <Paper
            className="search-controls-panel"
            component="section"
            aria-labelledby="search-page-title"
            withBorder
            p={{ base: "md", sm: "lg" }}
            radius="md"
          >
            <Stack gap="sm">
              <Group justify="space-between" align="flex-start" gap="sm">
                <Stack gap={3}>
                  <Title id="search-page-title" order={2} size="h4">
                    Search Reddit media
                  </Title>
                  <Text className="search-page-description" size="sm" c="gray.6">
                    Find images, videos, GIFs, galleries, and external media links.
                  </Text>
                </Stack>

                <Popover
                  opened={filtersPopoverOpened}
                  onChange={setFiltersPopoverOpened}
                  position="bottom-end"
                  shadow="xl"
                  width={360}
                  withinPortal
                >
                  <Popover.Target>
                    <Button
                      className="search-filter-toggle"
                      variant="subtle"
                      leftSection={<IconAdjustmentsHorizontal size={16} stroke={1.8} />}
                      onClick={() => setFiltersPopoverOpened((opened) => !opened)}
                    >
                      Filters
                    </Button>
                  </Popover.Target>
                  <Popover.Dropdown className="search-filters-popover">
                    <SearchFilters values={values} onFieldChange={setFieldValue} />
                  </Popover.Dropdown>
                </Popover>
              </Group>

              <div className="search-toolbar">
                <SearchForm
                  values={values}
                  onFieldChange={setFieldValue}
                  onSubmit={submitSearch}
                  keywordInputRef={keywordInputRef}
                />
              </div>
            </Stack>
          </Paper>
        ) : null}
      </div>

      <div className="search-results-container">
        <SearchResults
          state={state}
          onRetry={retrySearch}
          onLoadMore={loadMore}
          onClearFilters={clearFilters}
        />
      </div>
    </Stack>
  );
}

import { Divider, Paper, Stack, Text, Title } from "@mantine/core";
import { SearchFilters } from "../components/search/SearchFilters";
import { SearchForm } from "../components/search/SearchForm";
import { SearchPlaceholder } from "../components/search/SearchPlaceholder";
import { useSearchForm } from "../hooks/useSearchForm";
import "../styles/search.css";

export function SearchPage() {
  const { values, submittedValues, setFieldValue, submitSearch } =
    useSearchForm();

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

      <SearchPlaceholder submittedValues={submittedValues} />
    </Stack>
  );
}

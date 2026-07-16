import { Button, Group, TextInput } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import { useState } from "react";
import { normalizeEntityQuery } from "../../api/redditEntities";

export function EntitySearchForm({ initialQuery = "", isLoading = false, onSubmit }) {
  const [query, setQuery] = useState(initialQuery);
  const [error, setError] = useState(null);

  const handleSubmit = (event) => {
    event.preventDefault();
    const normalized = normalizeEntityQuery(query);
    if (normalized.length < 2) {
      setError("Enter at least 2 characters.");
      return;
    }
    setError(null);
    onSubmit(normalized);
  };

  return (
    <form onSubmit={handleSubmit}>
      <Group className="entity-search-form" align="flex-start" gap="sm">
        <TextInput
          className="entity-search-input"
          label="Search subreddits or users"
          placeholder="Search subreddits or users"
          value={query}
          error={error}
          onChange={(event) => setQuery(event.currentTarget.value)}
        />
        <Button
          className="entity-search-button"
          type="submit"
          loading={isLoading}
          leftSection={<IconSearch size={16} stroke={1.8} />}
        >
          Search
        </Button>
      </Group>
    </form>
  );
}

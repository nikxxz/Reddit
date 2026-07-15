import { Button, Group, Stack, Text, TextInput } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";

export function SearchForm({ values, onFieldChange, onSubmit, keywordInputRef }) {
  const hasError = Boolean(values.validationError);

  return (
    <form
      aria-describedby={hasError ? "search-validation-message" : undefined}
      noValidate
      onSubmit={onSubmit}
    >
      <Stack gap="xs">
        <Group className="search-form-row" align="flex-end" gap="sm">
          <TextInput
            className="search-keyword-input"
            ref={keywordInputRef}
            label="Keyword"
            placeholder="Search Reddit media"
            value={values.query}
            onChange={(event) => onFieldChange("query", event.currentTarget.value)}
          />
          <TextInput
            className="search-subreddit-input"
            label="Subreddit"
            placeholder="Subreddit, optional"
            value={values.subreddit}
            onChange={(event) =>
              onFieldChange("subreddit", event.currentTarget.value)
            }
          />
          <Button
            className="search-submit-button"
            leftSection={<IconSearch size={16} stroke={1.9} />}
            type="submit"
          >
            Search
          </Button>
        </Group>

        {hasError ? (
          <Text id="search-validation-message" size="sm" c="red.7" fw={600}>
            {values.validationError}
          </Text>
        ) : null}
      </Stack>
    </form>
  );
}

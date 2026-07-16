import { Button, Group, Select, Stack, Switch, Text } from "@mantine/core";

const MEDIA_TYPES = [
  { value: "all", label: "All" },
  { value: "images", label: "Images" },
  { value: "videos", label: "Videos" },
  { value: "gifs", label: "GIFs" },
  { value: "gallery", label: "Gallery" }
];

const DEFAULT_SORT_OPTIONS = [
  { value: "relevance", label: "Relevance" },
  { value: "new", label: "New" },
  { value: "top", label: "Top" },
  { value: "hot", label: "Hot" }
];

const TIME_OPTIONS = [
  { value: "hour", label: "Past hour" },
  { value: "all", label: "All time" },
  { value: "day", label: "Today" },
  { value: "week", label: "This week" },
  { value: "month", label: "This month" },
  { value: "year", label: "This year" }
];

export function SearchFilters({
  values,
  onFieldChange,
  sortOptions = DEFAULT_SORT_OPTIONS,
  disableTime = false
}) {
  return (
    <Stack gap="md">
      <Stack gap="xs">
        <Text size="sm" fw={600}>
          Media
        </Text>
        <Group className="media-button-group" gap="xs">
          {MEDIA_TYPES.map((item) => (
            <Button
              key={item.value}
              size="xs"
              variant={values.mediaType === item.value ? "filled" : "light"}
              onClick={() => onFieldChange("mediaType", item.value)}
            >
              {item.label}
            </Button>
          ))}
        </Group>
      </Stack>

      <Group className="filter-control-row" align="flex-end" gap="md">
        <Select
          className="filter-select"
          label="Sort"
          data={sortOptions}
          value={values.sortBy}
          allowDeselect={false}
          onChange={(value) => onFieldChange("sortBy", value)}
        />
        <Select
          className="filter-select"
          label="Time"
          data={TIME_OPTIONS}
          value={values.timeFilter}
          disabled={disableTime}
          allowDeselect={false}
          onChange={(value) => onFieldChange("timeFilter", value)}
        />
        <Switch
          className="filter-nsfw-switch"
          label="Include NSFW"
          checked={values.includeNsfw}
          onChange={(event) =>
            onFieldChange("includeNsfw", event.currentTarget.checked)
          }
        />
      </Group>
    </Stack>
  );
}

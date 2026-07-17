import {
  Badge,
  Button,
  Checkbox,
  Group,
  Paper,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Title
} from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { IconSearch, IconWorldSearch } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { useMediaPreview } from "../hooks/useMediaPreview";
import { useUniversalSearch } from "../hooks/useUniversalSearch";
import { UniversalMediaCard } from "../components/universal/UniversalMediaCard";
import { UniversalPreviewModal } from "../components/universal/UniversalPreviewModal";
import "../styles/search.css";
import "../styles/universal-search.css";

const PROVIDER_ORDER = ["reddit", "tumblr", "pinterest", "instagram"];
const MEDIA_TYPES = [
  { value: "image", label: "Images" },
  { value: "gif", label: "GIFs" },
  { value: "video", label: "Videos" },
  { value: "gallery", label: "Galleries" }
];

const SORT_OPTIONS = [
  { value: "source_balanced", label: "Source balanced" },
  { value: "grouped", label: "Grouped by source" },
  { value: "relevance", label: "Relevance" },
  { value: "new", label: "Newest" },
  { value: "top", label: "Top" }
];

export function UniversalSearchPage() {
  const { state, submitSearch } = useUniversalSearch();
  const preview = useMediaPreview();
  const isMobile = useMediaQuery("(max-width: 40em)");
  const [query, setQuery] = useState("");
  const [providers, setProviders] = useState(PROVIDER_ORDER);
  const [mediaTypes, setMediaTypes] = useState(["image", "gif", "video", "gallery"]);
  const [includeNsfw, setIncludeNsfw] = useState(false);
  const [sort, setSort] = useState("source_balanced");
  const [tumblrMode, setTumblrMode] = useState("tag");
  const [tumblrBlog, setTumblrBlog] = useState("");
  const [tumblrTag, setTumblrTag] = useState("");
  const [validationError, setValidationError] = useState("");

  const providerMap = useMemo(
    () => Object.fromEntries((state.providerMetadata || []).map((provider) => [provider.name, provider])),
    [state.providerMetadata]
  );

  const handleSubmit = (event) => {
    event.preventDefault();
    const cleanQuery = query.trim();
    if (!cleanQuery) {
      setValidationError("Enter a search query.");
      return;
    }
    if (!providers.length) {
      setValidationError("Select at least one source.");
      return;
    }
    if (!mediaTypes.length) {
      setValidationError("Select at least one media type.");
      return;
    }
    if (providers.includes("tumblr") && tumblrMode !== "tag" && !normalizeTumblrBlog(tumblrBlog)) {
      setValidationError("Enter a valid Tumblr blog name or URL.");
      return;
    }
    setValidationError("");
    submitSearch({
      query: cleanQuery,
      providers,
      media_types: mediaTypes,
      sort,
      include_nsfw: includeNsfw,
      limit_per_provider: 24,
      provider_filters: {
        tumblr: {
          mode: tumblrMode === "blog" && (tumblrTag.trim() || cleanQuery) ? "blog_tag" : tumblrMode,
          blog: tumblrMode === "tag" ? null : tumblrBlog.trim(),
          tag: tumblrTag.trim() || null
        }
      }
    });
  };

  return (
    <Stack className="search-page universal-search-page" gap="md">
      <div className="search-controls-container">
        <Paper
          className="search-controls-panel"
          component="section"
          aria-labelledby="universal-search-title"
          withBorder
          p={{ base: "md", sm: "lg" }}
          radius="md"
        >
          <Stack gap="md">
            <Group justify="space-between" align="flex-start" gap="sm">
              <Stack gap={3}>
                <Title id="universal-search-title" order={2} size="h4">
                  Universal Search
                </Title>
                <Text className="search-page-description" size="sm" c="gray.6">
                  Search media across multiple sources
                </Text>
              </Stack>
              <IconWorldSearch size={28} stroke={1.6} aria-hidden="true" />
            </Group>

            <form onSubmit={handleSubmit}>
              <Stack gap="md">
                <Group className="universal-search-row" gap="sm" align="flex-end">
                  <TextInput
                    className="universal-query-input"
                    label="Search query"
                    value={query}
                    onChange={(event) => setQuery(event.currentTarget.value)}
                    error={validationError || undefined}
                    placeholder="cyberpunk city"
                  />
                  <Button
                    className="search-submit-button"
                    type="submit"
                    leftSection={<IconSearch size={16} stroke={1.8} />}
                  >
                    {state.status === "searching" ? "Search again" : "Search"}
                  </Button>
                </Group>

                <Checkbox.Group
                  label="Sources"
                  value={providers}
                  onChange={setProviders}
                >
                  <Group className="universal-chip-row" gap="xs">
                    {PROVIDER_ORDER.map((providerName) => {
                      const provider = providerMap[providerName];
                      const planned = provider?.implementation_status === "planned" || provider?.health === "not_implemented";
                      return (
                        <Checkbox
                          key={providerName}
                          value={providerName}
                          label={
                            <Group gap={6} wrap="nowrap">
                              <Text span>{provider?.display_name || displayProvider(providerName)}</Text>
                              {planned ? <Badge size="xs" variant="light">Planned</Badge> : null}
                            </Group>
                          }
                        />
                      );
                    })}
                  </Group>
                </Checkbox.Group>

                <Checkbox.Group
                  label="Media"
                  value={mediaTypes}
                  onChange={setMediaTypes}
                >
                  <Group className="universal-chip-row" gap="xs">
                    {MEDIA_TYPES.map((mediaType) => (
                      <Checkbox key={mediaType.value} value={mediaType.value} label={mediaType.label} />
                    ))}
                  </Group>
                </Checkbox.Group>

                <Group className="universal-filter-row" gap="md" align="flex-end">
                  <Select
                    className="universal-sort-select"
                    label="Sort"
                    data={SORT_OPTIONS}
                    value={sort}
                    onChange={(value) => setSort(value || "source_balanced")}
                    allowDeselect={false}
                  />
                  <Switch
                    label="Include NSFW"
                    checked={includeNsfw}
                    onChange={(event) => setIncludeNsfw(event.currentTarget.checked)}
                  />
                </Group>

                {providers.includes("tumblr") ? (
                  <Paper className="universal-provider-options" withBorder p="sm" radius="sm">
                    <Stack gap="sm">
                      <Group justify="space-between" gap="sm">
                        <Text fw={700} size="sm">Tumblr options</Text>
                        <Badge variant="light">Tag-oriented</Badge>
                      </Group>
                      <Group className="universal-filter-row" gap="md" align="flex-end">
                        <Select
                          label="Tumblr search mode"
                          data={[
                            { value: "tag", label: "Tags" },
                            { value: "blog", label: "Blog" }
                          ]}
                          value={tumblrMode}
                          onChange={(value) => setTumblrMode(value || "tag")}
                          allowDeselect={false}
                        />
                        {tumblrMode === "blog" ? (
                          <TextInput
                            label="Blog name or URL"
                            value={tumblrBlog}
                            onChange={(event) => setTumblrBlog(event.currentTarget.value)}
                            error={tumblrBlog && !normalizeTumblrBlog(tumblrBlog) ? "Use a Tumblr blog name or URL." : undefined}
                            placeholder="staff or staff.tumblr.com"
                          />
                        ) : null}
                        <TextInput
                          label={tumblrMode === "blog" ? "Optional tag" : "Tag override"}
                          value={tumblrTag}
                          onChange={(event) => setTumblrTag(event.currentTarget.value)}
                          placeholder={query || "digital art"}
                        />
                      </Group>
                    </Stack>
                  </Paper>
                ) : null}
              </Stack>
            </form>
          </Stack>
        </Paper>
      </div>

      <div className="search-results-container">
        <Stack gap="md">
          <ProviderStatusBar
            providerMap={providerMap}
            providerStates={state.providers}
          />
          {state.error ? (
            <Paper className="search-results-panel" withBorder p="md" role="alert">
              <Text c="red.4">{state.error}</Text>
            </Paper>
          ) : null}
          <Paper
            className="search-results-panel"
            component="section"
            aria-live="polite"
            withBorder
            p={{ base: "md", sm: "lg" }}
            radius="md"
          >
            <Stack gap="md">
              <Group justify="space-between" gap="sm">
                <Stack gap={2}>
                  <Text fw={700}>Universal results</Text>
                  <Text size="sm" c="gray.6">
                    {summaryText(state)}
                  </Text>
                </Stack>
                {state.polling ? <Badge variant="light">Updating</Badge> : null}
              </Group>

              {state.items.length ? (
                <div className="media-grid">
                  {state.items.map((item) => (
                    <UniversalMediaCard
                      key={`${item.provider}:${item.provider_item_id}`}
                      item={item}
                      compact={isMobile}
                      onOpen={preview.openPreview}
                    />
                  ))}
                </div>
              ) : (
                <Text size="sm" c="gray.6">
                  {state.status === "idle"
                    ? "Search results will appear here."
                    : "No Universal Search results yet."}
                </Text>
              )}
            </Stack>
          </Paper>
        </Stack>
      </div>

      <UniversalPreviewModal
        opened={preview.opened}
        item={preview.selectedItem}
        onClose={preview.closePreview}
      />
    </Stack>
  );
}

function normalizeTumblrBlog(value) {
  const raw = value.trim();
  if (!raw || hasControlCharacter(raw)) {
    return null;
  }
  try {
    if (/^https?:\/\//i.test(raw)) {
      const url = new URL(raw);
      if (url.hostname === "www.tumblr.com" || url.hostname === "tumblr.com") {
        return url.pathname.split("/").filter(Boolean)[0] || null;
      }
      if (url.hostname.endsWith(".tumblr.com")) {
        return url.hostname;
      }
      return null;
    }
  } catch {
    return null;
  }
  return /^[A-Za-z0-9][A-Za-z0-9-]{0,62}(\.tumblr\.com)?$/.test(raw) ? raw : null;
}

function hasControlCharacter(value) {
  return [...value].some((char) => char.charCodeAt(0) < 32);
}

function ProviderStatusBar({ providerMap, providerStates }) {
  return (
    <div className="universal-provider-status" aria-label="Provider status">
      {PROVIDER_ORDER.map((providerName) => {
        const provider = providerMap[providerName];
        const state = providerStates[providerName];
        const status = state?.status || provider?.health || "unavailable";
        return (
          <Paper key={providerName} className="universal-provider-card" withBorder p="sm" radius="md">
            <Group justify="space-between" gap="xs" wrap="nowrap">
              <Text fw={700}>{provider?.display_name || displayProvider(providerName)}</Text>
              <Badge color={statusColor(status)} variant="light">
                {statusLabel(status, state?.result_count)}
              </Badge>
            </Group>
            <Text size="xs" c="gray.6">
              {provider?.implementation_status === "planned"
                ? "Planned provider"
                : provider?.implementation_status === "configuration_required"
                  ? "Configuration required"
                  : "Available provider"}
            </Text>
          </Paper>
        );
      })}
    </div>
  );
}

function displayProvider(provider) {
  return {
    reddit: "Reddit",
    tumblr: "Tumblr",
    pinterest: "Pinterest",
    instagram: "Instagram"
  }[provider] || provider;
}

function statusLabel(status, resultCount) {
  if (status === "completed") {
    return `${resultCount || 0} results`;
  }
  if (status === "no_results") {
    return "No results";
  }
  if (status === "not_implemented") {
    return "Planned";
  }
  return {
    ready: "Ready",
    queued: "Queued",
    searching: "Searching",
    failed: "Failed",
    unavailable: "Unavailable",
    authentication_required: "Auth required",
    rate_limited: "Rate limited",
    degraded: "Degraded"
  }[status] || "Unavailable";
}

function statusColor(status) {
  if (status === "completed" || status === "ready") {
    return "teal";
  }
  if (status === "searching" || status === "queued") {
    return "blue";
  }
  if (status === "not_implemented") {
    return "gray";
  }
  return "red";
}

function summaryText(state) {
  if (state.status === "idle") {
    return "Reddit is available now; Tumblr is available when configured. Pinterest and Instagram are planned.";
  }
  if (state.status === "searching") {
    return "Searching selected sources.";
  }
  if (state.status === "completed_with_errors") {
    return `${state.items.length} result${state.items.length === 1 ? "" : "s"} with provider limitations.`;
  }
  if (state.status === "completed") {
    return `${state.items.length} result${state.items.length === 1 ? "" : "s"}.`;
  }
  if (state.status === "failed") {
    return "No selected provider could complete the search.";
  }
  return "Universal Search status is updating.";
}

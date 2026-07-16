import { Badge, Group, Image, Paper, SimpleGrid, Skeleton, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconUsers, IconUser } from "@tabler/icons-react";
import { useState } from "react";

function formatCount(value) {
  if (!Number.isFinite(value)) {
    return null;
  }
  return new Intl.NumberFormat(undefined, { notation: "compact" }).format(value);
}

function EntityImage({ src, type }) {
  const [failed, setFailed] = useState(false);
  const Icon = type === "user" ? IconUser : IconUsers;
  if (src && !failed) {
    return <Image className="entity-result-avatar" src={src} alt="" onError={() => setFailed(true)} />;
  }
  return (
    <ThemeIcon className="entity-result-avatar" variant="light" size="xl" aria-label={type === "user" ? "User" : "Subreddit"}>
      <Icon size={22} stroke={1.8} />
    </ThemeIcon>
  );
}

function ResultCard({ type, item, onOpen }) {
  const isUser = type === "user";
  const name = isUser ? item.username : item.name;
  const title = isUser ? item.display_name : item.title;
  const count = isUser
    ? [formatCount(item.link_karma), formatCount(item.comment_karma)].filter(Boolean).join(" / ")
    : formatCount(item.subscribers);
  const handleKeyDown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(type, name);
    }
  };
  return (
    <Paper
      className="entity-result-card"
      withBorder
      p="md"
      role="button"
      tabIndex={0}
      aria-label={`${isUser ? "Reddit user" : "Subreddit"} ${name}`}
      onClick={() => onOpen(type, name)}
      onKeyDown={handleKeyDown}
    >
      <Group gap="sm" align="flex-start" wrap="nowrap">
        <EntityImage src={isUser ? item.avatar_url : item.icon_url} type={type} />
        <Stack gap={4} miw={0}>
          <Group gap={6}>
            <Text fw={700}>{isUser ? `u/${name}` : `r/${name}`}</Text>
            {item.over_18 ? <Badge color="red" size="xs">NSFW</Badge> : null}
            {item.private || item.restricted || item.suspended ? (
              <Badge color="yellow" size="xs">{item.suspended ? "Unavailable" : item.private ? "Private" : "Restricted"}</Badge>
            ) : null}
          </Group>
          {title && title !== name ? <Text size="sm" lineClamp={1}>{title}</Text> : null}
          {item.description ? <Text size="sm" c="gray.6" lineClamp={2}>{item.description}</Text> : null}
          {count ? <Text size="xs" c="gray.6">{isUser ? `${count} karma` : `${count} subscribers`}</Text> : null}
        </Stack>
      </Group>
    </Paper>
  );
}

function LoadingResults() {
  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
      {Array.from({ length: 4 }).map((_, index) => (
        <Skeleton key={index} height={112} radius="md" />
      ))}
    </SimpleGrid>
  );
}

export function EntitySearchResults({ state, onOpenEntity }) {
  if (state.status === "idle") {
    return (
      <Paper withBorder p="lg" className="entity-search-empty">
        <Text fw={700}>Search results will appear here.</Text>
        <Text size="sm" c="gray.6">Find a subreddit or user to browse media posts only.</Text>
      </Paper>
    );
  }
  if (state.status === "loading") {
    return <LoadingResults />;
  }
  if (state.status === "error") {
    return (
      <Paper withBorder p="lg" className="entity-search-empty" role="alert">
        <Text fw={700}>Unable to search Reddit.</Text>
        <Text size="sm" c="gray.6">{state.error}</Text>
      </Paper>
    );
  }
  const hasSubreddits = state.subreddits.length > 0;
  const hasUsers = state.users.length > 0;
  if (!hasSubreddits && !hasUsers) {
    return (
      <Paper withBorder p="lg" className="entity-search-empty">
        <Text fw={700}>No matching subreddits or users found.</Text>
      </Paper>
    );
  }
  return (
    <SimpleGrid cols={{ base: 1, md: hasSubreddits && hasUsers ? 2 : 1 }} spacing="lg">
      {hasSubreddits ? (
        <Stack gap="sm">
          <Text fw={800}>Subreddits</Text>
          {state.subreddits.map((item) => (
            <ResultCard key={item.name} type="subreddit" item={item} onOpen={onOpenEntity} />
          ))}
        </Stack>
      ) : null}
      {hasUsers ? (
        <Stack gap="sm">
          <Text fw={800}>Users</Text>
          {state.users.map((item) => (
            <ResultCard key={item.username} type="user" item={item} onOpen={onOpenEntity} />
          ))}
        </Stack>
      ) : null}
    </SimpleGrid>
  );
}

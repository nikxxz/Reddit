import { Badge, Group, Image, Paper, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconUser, IconUsers } from "@tabler/icons-react";

function compact(value) {
  if (!Number.isFinite(value)) {
    return null;
  }
  return new Intl.NumberFormat(undefined, { notation: "compact" }).format(value);
}

export function EntityHeader({ entity, fallbackType, fallbackName }) {
  const type = entity?.type || fallbackType;
  const name = entity?.name || fallbackName;
  const isUser = type === "user";
  const image = isUser ? entity?.avatar_url : entity?.icon_url;
  const Icon = isUser ? IconUser : IconUsers;
  const count = isUser
    ? [compact(entity?.link_karma), compact(entity?.comment_karma)].filter(Boolean).join(" / ")
    : compact(entity?.subscribers);

  return (
    <Paper className="entity-header" withBorder p="md">
      <Group gap="sm" align="flex-start" wrap="nowrap">
        {image ? (
          <Image className="entity-header-image" src={image} alt="" />
        ) : (
          <ThemeIcon className="entity-header-image" variant="light" size="xl">
            <Icon size={22} stroke={1.8} />
          </ThemeIcon>
        )}
        <Stack gap={4} miw={0}>
          <Group gap={6}>
            <Title order={2} size="h4">{isUser ? `u/${name}` : `r/${name}`}</Title>
            {entity?.over_18 ? <Badge color="red">NSFW</Badge> : null}
            {entity?.private || entity?.restricted || entity?.suspended ? (
              <Badge color="yellow">{entity.suspended ? "Unavailable" : entity.private ? "Private" : "Restricted"}</Badge>
            ) : null}
          </Group>
          {entity?.title ? <Text size="sm">{entity.title}</Text> : null}
          {entity?.description ? <Text size="sm" c="gray.6" lineClamp={2}>{entity.description}</Text> : null}
          {count ? <Text size="xs" c="gray.6">{isUser ? `${count} karma` : `${count} subscribers`}</Text> : null}
        </Stack>
      </Group>
    </Paper>
  );
}

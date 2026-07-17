import { Badge, Button, FileInput, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { IconRefresh, IconTrash, IconUpload } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import {
  clearPinterestSession,
  importPinterestSession,
  listUniversalProviders,
  testPinterestSession
} from "../api/universalSearchApi";

export function SettingsPage() {
  const [providers, setProviders] = useState([]);
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState("");
  const pinterest = providers.find((provider) => provider.name === "pinterest");

  const loadProviders = () => {
    listUniversalProviders()
      .then((response) => setProviders(response.providers || []))
      .catch(() => setMessage("Unable to load provider status."));
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const handleImport = async (file) => {
    if (!file) {
      return;
    }
    try {
      const response = await importPinterestSession(file);
      setStatus(response);
      setMessage("Pinterest cookies imported.");
      loadProviders();
    } catch (error) {
      setMessage(error.message || "Pinterest cookie import failed.");
    }
  };

  const handleTest = async () => {
    try {
      const response = await testPinterestSession();
      setStatus(response);
      setMessage(response.valid ? "Pinterest session is ready." : "Pinterest session needs attention.");
      loadProviders();
    } catch {
      setMessage("Pinterest session test failed.");
    }
  };

  const handleClear = async () => {
    const response = await clearPinterestSession();
    setStatus(response);
    setMessage("Pinterest session cleared.");
    loadProviders();
  };

  return (
    <Stack className="search-page" gap="md">
      <Paper className="search-controls-panel" withBorder p={{ base: "md", sm: "lg" }} radius="md">
        <Stack gap="md">
          <Title order={2} size="h4">Settings</Title>
          <Paper className="universal-provider-options" withBorder p="md" radius="sm">
            <Stack gap="sm">
              <Group justify="space-between" gap="sm">
                <Stack gap={2}>
                  <Text fw={700}>Pinterest source</Text>
                  <Text size="sm" c="gray.6">Manual cookies.txt import for gallery-dl metadata extraction</Text>
                </Stack>
                <Badge color={statusColor(pinterest?.health)} variant="light">
                  {statusLabel(pinterest?.health)}
                </Badge>
              </Group>
              <Group gap="xs">
                <Badge variant="light">gallery-dl {pinterest?.rate_limit?.extractor_version || "unknown"}</Badge>
                <Badge variant="light">{status?.configured ?? pinterest?.rate_limit?.session_configured ? "Session configured" : "Session missing"}</Badge>
                {status?.valid === false ? <Badge color="red" variant="light">Invalid session</Badge> : null}
              </Group>
              <Group className="universal-filter-row" gap="sm" align="flex-end">
                <FileInput
                  label="Import cookies.txt"
                  placeholder="Select Netscape cookies.txt"
                  accept=".txt,text/plain"
                  leftSection={<IconUpload size={16} />}
                  onChange={handleImport}
                />
                <Button variant="light" leftSection={<IconRefresh size={16} />} onClick={handleTest}>
                  Test session
                </Button>
                <Button color="red" variant="subtle" leftSection={<IconTrash size={16} />} onClick={handleClear}>
                  Clear session
                </Button>
              </Group>
              {status?.last_checked_at ? (
                <Text size="xs" c="gray.6">Last checked {new Date(status.last_checked_at).toLocaleString()}</Text>
              ) : null}
              {message ? <Text size="sm" c={message.includes("failed") ? "red.4" : "gray.6"}>{message}</Text> : null}
            </Stack>
          </Paper>
        </Stack>
      </Paper>
    </Stack>
  );
}

function statusLabel(status) {
  return {
    ready: "Ready",
    session_required: "Session required",
    extractor_unavailable: "Extractor unavailable",
    unavailable: "Unavailable",
    failed: "Failed"
  }[status] || "Unknown";
}

function statusColor(status) {
  if (status === "ready") {
    return "teal";
  }
  if (status === "session_required") {
    return "yellow";
  }
  return "red";
}

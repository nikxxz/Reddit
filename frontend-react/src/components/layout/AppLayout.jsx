import { AppShell, Paper, Stack, Text, Title } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { useState } from "react";
import { AppHeader } from "./AppHeader";
import { AppSidebar } from "./AppSidebar";
import { ConnectionSummary } from "./ConnectionSummary";

export function AppLayout({ connections, isChecking, onRetryConnections }) {
  const isMobile = useMediaQuery("(max-width: 48em)");
  const [mobileOpened, { toggle: toggleMobile, close: closeMobile }] =
    useDisclosure(false);
  const [desktopOpened, { toggle: toggleDesktop }] = useDisclosure(true);
  const [activeSection, setActiveSection] = useState("search");

  const toggleNavbar = () => {
    if (isMobile) {
      toggleMobile();
      return;
    }

    toggleDesktop();
  };

  const handleSelectSection = (section) => {
    setActiveSection(section);

    if (isMobile) {
      closeMobile();
    }
  };

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{
        width: 240,
        breakpoint: "sm",
        collapsed: {
          mobile: !mobileOpened,
          desktop: !desktopOpened
        }
      }}
      padding="md"
    >
      <AppShell.Header>
        <AppHeader
          opened={isMobile ? mobileOpened : desktopOpened}
          onToggle={toggleNavbar}
        />
      </AppShell.Header>

      <AppShell.Navbar>
        <AppSidebar
          activeSection={activeSection}
          connections={connections}
          onSelectSection={handleSelectSection}
        />
      </AppShell.Navbar>

      <AppShell.Main className="app-main">
        <Paper
          className="migration-panel"
          component="section"
          aria-labelledby="migration-title"
          withBorder
          shadow="xs"
          p={{ base: "sm", sm: "lg" }}
          radius="md"
          style={{
            boxSizing: "border-box",
            maxWidth: "min(720px, calc(100vw - 48px))",
            width: "100%"
          }}
        >
          <Stack gap="md">
            <Stack gap={6}>
              <Title id="migration-title" order={2} size="h3">
                React UI migration
              </Title>
              <Text c="gray.7">
                Mantine application shell is active.
              </Text>
              <Text c="gray.7">
                Current milestone: responsive layout only.
              </Text>
            </Stack>

            <ConnectionSummary
              connections={connections}
              showRetry
              isChecking={isChecking}
              onRetryConnections={onRetryConnections}
            />
          </Stack>
        </Paper>
      </AppShell.Main>
    </AppShell>
  );
}

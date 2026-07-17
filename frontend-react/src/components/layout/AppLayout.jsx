import { AppShell } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { useState } from "react";
import { DownloadsPage } from "../../pages/DownloadsPage";
import { SearchPage } from "../../pages/SearchPage";
import { SettingsPage } from "../../pages/SettingsPage";
import { UniversalSearchPage } from "../../pages/UniversalSearchPage";
import { useDownloads } from "../../hooks/useDownloads";
import { DownloadTray } from "../downloads/DownloadTray";
import { AppHeader } from "./AppHeader";
import { AppSidebar } from "./AppSidebar";

export function AppLayout({
  connections,
  isChecking: _isChecking,
  onRetryConnections: _onRetryConnections,
  redditAuth
}) {
  const isMobile = useMediaQuery("(max-width: 48em)");
  const [mobileOpened, { toggle: toggleMobile, close: closeMobile }] =
    useDisclosure(false);
  const [desktopOpened, { toggle: toggleDesktop }] = useDisclosure(true);
  const [activeSection, setActiveSection] = useState("search");
  const { activeJobCount, jobs } = useDownloads();

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
        width: isMobile || desktopOpened ? 240 : 64,
        breakpoint: "sm",
        collapsed: {
          mobile: !mobileOpened,
          desktop: false
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
          collapsed={!isMobile && !desktopOpened}
          connections={connections}
          activeDownloadCount={activeJobCount}
          onSelectSection={handleSelectSection}
          redditAuth={redditAuth}
        />
      </AppShell.Navbar>

      <AppShell.Main className="app-main">
        <div hidden={activeSection !== "search"}>
          <SearchPage />
        </div>
        <div hidden={activeSection !== "universal-search"}>
          <UniversalSearchPage />
        </div>
        <div hidden={activeSection !== "downloads"}>
          <DownloadsPage />
        </div>
        <div hidden={activeSection !== "settings"}>
          <SettingsPage />
        </div>
      </AppShell.Main>

      <DownloadTray
        jobs={jobs}
        onOpenDownloads={() => handleSelectSection("downloads")}
      />
    </AppShell>
  );
}

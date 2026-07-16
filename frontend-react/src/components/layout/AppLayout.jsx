import { AppShell } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { useCallback, useEffect, useState } from "react";
import { DownloadsPage } from "../../pages/DownloadsPage";
import { EntityBrowserPage } from "../../pages/EntityBrowserPage";
import { SearchPage } from "../../pages/SearchPage";
import { SettingsPage } from "../../pages/SettingsPage";
import { useDownloads } from "../../hooks/useDownloads";
import { DownloadTray } from "../downloads/DownloadTray";
import { AppHeader } from "./AppHeader";
import { AppSidebar } from "./AppSidebar";

function parseRoute() {
  const path = window.location.pathname;
  const query = new URLSearchParams(window.location.search);
  const browseMatch = path.match(/^\/browse\/(subreddit|user)\/([^/]+)\/?$/);
  if (browseMatch) {
    return {
      activeSection: "browse",
      browseRoute: {
        entityType: browseMatch[1],
        entityName: decodeURIComponent(browseMatch[2]),
        query
      }
    };
  }
  if (path.startsWith("/browse")) {
    return { activeSection: "browse", browseRoute: { query } };
  }
  if (path.startsWith("/downloads")) {
    return { activeSection: "downloads", browseRoute: null };
  }
  if (path.startsWith("/settings")) {
    return { activeSection: "settings", browseRoute: null };
  }
  return { activeSection: "search", browseRoute: null };
}

const SECTION_PATHS = {
  search: "/",
  browse: "/browse",
  downloads: "/downloads",
  settings: "/settings"
};

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
  const [routeState, setRouteState] = useState(parseRoute);
  const { activeJobCount, jobs } = useDownloads();
  const { activeSection, browseRoute } = routeState;

  useEffect(() => {
    const handlePopState = () => setRouteState(parseRoute());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const pushPath = useCallback((path) => {
    if (`${window.location.pathname}${window.location.search}` !== path) {
      window.history.pushState({}, "", path);
    }
    setRouteState(parseRoute());
  }, []);

  const toggleNavbar = () => {
    if (isMobile) {
      toggleMobile();
      return;
    }

    toggleDesktop();
  };

  const handleSelectSection = (section) => {
    pushPath(SECTION_PATHS[section] || "/");

    if (isMobile) {
      closeMobile();
    }
  };

  const handleNavigateEntity = useCallback((type, name) => {
    pushPath(`/browse/${type}/${encodeURIComponent(name)}`);
  }, [pushPath]);

  const handleNavigateBrowse = useCallback(() => {
    pushPath("/browse");
  }, [pushPath]);

  const handleReplaceEntityQuery = useCallback((query) => {
    if (!browseRoute?.entityType || !browseRoute?.entityName) {
      return;
    }
    const path = `/browse/${browseRoute.entityType}/${encodeURIComponent(browseRoute.entityName)}${query ? `?${query}` : ""}`;
    if (`${window.location.pathname}${window.location.search}` !== path) {
      window.history.replaceState({}, "", path);
      setRouteState(parseRoute());
    }
  }, [browseRoute?.entityName, browseRoute?.entityType]);

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
        <div hidden={activeSection !== "browse"}>
          <EntityBrowserPage
            route={browseRoute}
            onNavigateEntity={handleNavigateEntity}
            onNavigateBrowse={handleNavigateBrowse}
            onReplaceEntityQuery={handleReplaceEntityQuery}
          />
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

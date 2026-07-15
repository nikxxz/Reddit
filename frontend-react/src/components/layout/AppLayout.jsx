import { AppShell } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { useState } from "react";
import { SearchPage } from "../../pages/SearchPage";
import { AppHeader } from "./AppHeader";
import { AppSidebar } from "./AppSidebar";

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
        <SearchPage />
      </AppShell.Main>
    </AppShell>
  );
}

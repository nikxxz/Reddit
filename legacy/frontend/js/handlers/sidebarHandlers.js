import { setCurrentPage, state } from "../state.js";


export function initializeSidebar(elements, renderPage) {
  state.sidebarCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
  applySidebarState(elements);

  elements.sidebarToggle.addEventListener("click", () => toggleSidebar(elements));
  elements.mobileSidebarToggle.addEventListener("click", () => toggleSidebar(elements));
  elements.navItems.forEach((button) => {
    button.addEventListener("click", () => {
      setCurrentPage(button.dataset.pageTarget);
      renderPage();
    });
  });
}


function toggleSidebar(elements) {
  state.sidebarCollapsed = !state.sidebarCollapsed;
  localStorage.setItem("sidebarCollapsed", String(state.sidebarCollapsed));
  applySidebarState(elements);
}


function applySidebarState(elements) {
  elements.appShell.classList.toggle("sidebar-collapsed", state.sidebarCollapsed);
  const action = state.sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar";
  elements.sidebarToggle.setAttribute("aria-label", action);
  elements.sidebarToggle.setAttribute("title", action);
}


export function renderActivePage(elements) {
  elements.pageSections.forEach((section) => {
    section.hidden = section.dataset.page !== state.currentPage;
  });
  elements.navItems.forEach((button) => {
    const isActive = button.dataset.pageTarget === state.currentPage;
    button.classList.toggle("active", isActive);
    if (isActive) {
      button.setAttribute("aria-current", "page");
    } else {
      button.removeAttribute("aria-current");
    }
  });
}

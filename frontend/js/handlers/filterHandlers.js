export function bindFilterHandlers(elements, actions) {
  elements.filterButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.classList.contains("active")));
    button.addEventListener("click", () => actions.onMediaFilter(button.dataset.filter));
  });

  elements.sortSelect.addEventListener("change", actions.onSortChange);
}


export function renderActiveFilter(elements, filter) {
  elements.filterButtons.forEach((button) => {
    const isActive = button.dataset.filter === filter;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

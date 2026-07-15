import { state } from "../state.js";
import { createMediaCard } from "./mediaCard.js";


export function renderMediaGrid(items, onSelectionChange) {
  const cards = items.map((item) =>
    createMediaCard(item, {
      selectedIds: state.selectedIds,
      onSelectionChange,
    }),
  );
  return cards;
}


export function uniqueById(existingItems, incomingItems) {
  const existingIds = new Set(existingItems.map((item) => item.id));
  return incomingItems.filter((item) => {
    if (!item.id || existingIds.has(item.id)) {
      return false;
    }
    existingIds.add(item.id);
    return true;
  });
}

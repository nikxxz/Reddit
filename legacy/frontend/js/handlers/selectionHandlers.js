import { state } from "../state.js";


export function toggleSelection(itemId, selected) {
  if (selected) {
    state.selectedIds.add(itemId);
  } else {
    state.selectedIds.delete(itemId);
  }
}


export function clearSelection() {
  state.selectedIds.clear();
}

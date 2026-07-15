import { useCallback, useState } from "react";

export function useMediaPreview() {
  const [previewState, setPreviewState] = useState({
    opened: false,
    selectedItem: null
  });

  const openPreview = useCallback((item) => {
    setPreviewState({
      opened: true,
      selectedItem: item
    });
  }, []);

  const closePreview = useCallback(() => {
    setPreviewState({
      opened: false,
      selectedItem: null
    });
  }, []);

  return {
    opened: previewState.opened,
    selectedItem: previewState.selectedItem,
    openPreview,
    closePreview
  };
}

import { useState, useCallback } from "react";

export interface ModalState {
  showSettings: boolean;
  openSettings: () => void;
  closeSettings: () => void;

  graphEditing: boolean;
  openGraphEditor: () => void;
  closeGraphEditor: () => void;

  pendingSiteChange: string | null;
  setPendingSiteChange: (site: string | null) => void;
  clearPendingSiteChange: () => void;
}

export function useModalState(): ModalState {
  const [showSettings, setShowSettings] = useState(false);
  const [graphEditing, setGraphEditing] = useState(false);
  const [pendingSiteChange, setPendingSiteChange] = useState<string | null>(null);

  const openSettings = useCallback(() => setShowSettings(true), []);
  const closeSettings = useCallback(() => setShowSettings(false), []);
  const openGraphEditor = useCallback(() => setGraphEditing(true), []);
  const closeGraphEditor = useCallback(() => setGraphEditing(false), []);
  const clearPendingSiteChange = useCallback(() => setPendingSiteChange(null), []);

  return {
    showSettings,
    openSettings,
    closeSettings,
    graphEditing,
    openGraphEditor,
    closeGraphEditor,
    pendingSiteChange,
    setPendingSiteChange,
    clearPendingSiteChange,
  };
}

import { useCallback } from "react";
import { useEventListener } from "usehooks-ts";

export function useUndoRedoHotkeys(args: {
  enabled: boolean;
  tryUndoLocal: () => boolean;
  tryRedoLocal: () => boolean;
  canUndoGlobal: () => boolean;
  canRedoGlobal: () => boolean;
  undoGlobal: () => void;
  redoGlobal: () => void;
}) {
  const {
    enabled,
    tryUndoLocal,
    tryRedoLocal,
    canUndoGlobal,
    canRedoGlobal,
    undoGlobal,
    redoGlobal,
  } = args;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)
      ) {
        return;
      }

      if (!(event.ctrlKey || event.metaKey)) return;
      const key = event.key.toLowerCase();
      if (key !== "z" && key !== "y") return;

      event.preventDefault();

      if (key === "y" || event.shiftKey) {
        if (tryRedoLocal()) return;
        if (canRedoGlobal()) redoGlobal();
        return;
      }

      if (tryUndoLocal()) return;
      if (canUndoGlobal()) undoGlobal();
    },
    [
      enabled,
      tryUndoLocal,
      tryRedoLocal,
      canUndoGlobal,
      canRedoGlobal,
      undoGlobal,
      redoGlobal,
    ],
  );

  useEventListener("keydown", handleKeyDown);
}

import { useCallback } from "react";
import { useEventListener } from "usehooks-ts";

export function useBeforeUnloadUnsaved(isUnsaved: boolean) {
  const handleBeforeUnload = useCallback(
    (event: BeforeUnloadEvent) => {
      if (!isUnsaved) return;
      event.preventDefault();
      event.returnValue = "";
    },
    [isUnsaved],
  );

  useEventListener("beforeunload", handleBeforeUnload);
}

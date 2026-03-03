import { useEffect } from "react";
import { DEFAULT_STREAM_NAME } from "@pathfinder/shared";

export function useDraftDetailsInputs(args: {
  isDraftView: boolean;
  draftName: string | undefined | null;
  draftDescription: string | undefined | null;
  setNameValue: (value: string) => void;
  setDescriptionValue: (value: string) => void;
}) {
  const {
    isDraftView,
    draftName,
    draftDescription,
    setNameValue,
    setDescriptionValue,
  } = args;

  useEffect(() => {
    if (!isDraftView) return;
    setNameValue(draftName || DEFAULT_STREAM_NAME);
    setDescriptionValue(draftDescription || "");
  }, [isDraftView, draftName, draftDescription, setNameValue, setDescriptionValue]);
}

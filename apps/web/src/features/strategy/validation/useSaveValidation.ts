import { useEffect, useMemo } from "react";
import { useDebouncedCallback } from "use-debounce";
import type { Step } from "@pathfinder/shared";

export function useSaveValidation(args: {
  steps: Step[];
  buildStepSignature: (step: Step) => string;
  debounceMs?: number;
  validate: () => Promise<boolean>;
}) {
  const { steps, buildStepSignature, debounceMs = 500, validate } = args;

  const validationInputKey = useMemo(() => {
    if (steps.length === 0) return "";
    return steps
      .map((step) => `${step.id}:${buildStepSignature(step)}`)
      .sort()
      .join("|");
  }, [steps, buildStepSignature]);

  const debouncedValidate = useDebouncedCallback(() => {
    void validate();
  }, debounceMs);

  useEffect(() => {
    if (steps.length === 0) return;
    debouncedValidate();
  }, [steps, validationInputKey, debouncedValidate]);
}

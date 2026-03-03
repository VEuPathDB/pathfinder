import { useEffect } from "react";
import type { StrategyStep, StrategyWithMeta } from "@pathfinder/shared";
import { usePrevious } from "@/lib/hooks/usePrevious";

export function useSavedSnapshotSync(args: {
  strategy: StrategyWithMeta | null;
  setLastSavedSteps: (value: Map<string, string>) => void;
  buildStepSignature: (step: StrategyStep) => string;
  bumpLastSavedStepsVersion: () => void;
}) {
  const { strategy, setLastSavedSteps, buildStepSignature, bumpLastSavedStepsVersion } =
    args;

  const snapshotId = strategy?.id || null;
  const prevSnapshotId = usePrevious(snapshotId);

  useEffect(() => {
    if (!snapshotId || snapshotId === prevSnapshotId) return;
    if (strategy?.steps) {
      setLastSavedSteps(
        new Map(strategy.steps.map((step) => [step.id, buildStepSignature(step)])),
      );
      bumpLastSavedStepsVersion();
    }
  }, [
    snapshotId,
    prevSnapshotId,
    strategy?.steps,
    buildStepSignature,
    setLastSavedSteps,
    bumpLastSavedStepsVersion,
  ]);
}

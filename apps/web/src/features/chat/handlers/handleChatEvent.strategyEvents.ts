import type { Step } from "@pathfinder/shared";
import type { ChatEventContext } from "./handleChatEvent.types";

/**
 * Resolve the target graph ID from event candidates, falling back to
 * `ctx.strategyIdAtStart`. Returns null when the event should be
 * skipped (no valid target, or target doesn't match the active strategy).
 */
function resolveTargetGraph(
  ctx: ChatEventContext,
  ...candidates: (string | undefined | null)[]
): string | null {
  const id = candidates.find(Boolean) || ctx.strategyIdAtStart || null;
  if (!id) return null;
  if (ctx.strategyIdAtStart && id !== ctx.strategyIdAtStart) return null;
  return id;
}

export function handleStrategyUpdateEvent(ctx: ChatEventContext, data: unknown) {
  const { step, graphId } = data as {
    graphId?: string;
    step: {
      stepId: string;
      kind?: string;
      displayName: string;
      searchName?: string;
      transformName?: string;
      operator?: string;
      primaryInputStepId?: string;
      secondaryInputStepId?: string;
      parameters?: Record<string, unknown>;
      name?: string | null;
      description?: string | null;
      recordType?: string;
      graphId?: string;
      graphName?: string;
    };
  };
  if (!step) return;
  const targetGraphId = resolveTargetGraph(ctx, graphId, step.graphId);
  if (!targetGraphId) return;

  ctx.session.captureUndoSnapshot(targetGraphId);
  if (step.name || step.description || step.recordType) {
    ctx.setStrategyMeta({
      name: step.graphName ?? step.name ?? undefined,
      description: step.description ?? undefined,
      recordType: step.recordType ?? undefined,
    });
  }
  ctx.addStep({
    id: step.stepId,
    kind: (step.kind ?? "search") as Step["kind"],
    displayName: step.displayName || step.kind || "Untitled step",
    recordType: step.recordType ?? undefined,
    searchName: step.searchName,
    operator: (step.operator as Step["operator"]) ?? undefined,
    primaryInputStepId: step.primaryInputStepId,
    secondaryInputStepId: step.secondaryInputStepId,
    parameters: step.parameters,
  });
  ctx.session.markSnapshotApplied();
}

export function handleGraphSnapshotEvent(ctx: ChatEventContext, data: unknown) {
  const { graphSnapshot } = data as {
    graphSnapshot?: Record<string, unknown>;
  };
  if (graphSnapshot) ctx.applyGraphSnapshot(graphSnapshot);
}

export function handleStrategyLinkEvent(ctx: ChatEventContext, data: unknown) {
  const { graphId, wdkStrategyId, wdkUrl, name, description, strategySnapshotId } =
    data as {
      graphId?: string;
      wdkStrategyId?: number;
      wdkUrl?: string;
      name?: string;
      description?: string;
      strategySnapshotId?: string;
    };
  const targetGraphId = resolveTargetGraph(ctx, graphId, strategySnapshotId);
  if (!targetGraphId) return;

  if (wdkStrategyId) ctx.setWdkInfo(wdkStrategyId, wdkUrl, name, description);
  ctx.setStrategyMeta({
    name: name ?? undefined,
    description: description ?? undefined,
  });
  if (ctx.currentStrategy) {
    ctx.addExecutedStrategy({
      ...ctx.currentStrategy,
      name: name ?? ctx.currentStrategy.name,
      description: description ?? ctx.currentStrategy.description,
      wdkStrategyId: wdkStrategyId ?? ctx.currentStrategy.wdkStrategyId,
      wdkUrl: wdkUrl ?? ctx.currentStrategy.wdkUrl,
      updatedAt: new Date().toISOString(),
    });
  } else {
    ctx
      .getStrategy(targetGraphId)
      .then((full) => ctx.addExecutedStrategy(full))
      .catch((err) =>
        console.error("[handleStrategyLinkEvent] Failed to fetch strategy:", err),
      );
  }
}

export function handleStrategyMetaEvent(ctx: ChatEventContext, data: unknown) {
  const { graphId, name, description, recordType, graphName } = data as {
    graphId?: string;
    name?: string;
    description?: string;
    recordType?: string | null;
    graphName?: string;
  };
  if (!resolveTargetGraph(ctx, graphId)) return;
  ctx.setStrategyMeta({
    name: name ?? graphName ?? undefined,
    description: description ?? undefined,
    recordType: recordType ?? undefined,
  });
}

export function handleStrategyClearedEvent(ctx: ChatEventContext, data: unknown) {
  const { graphId } = data as { graphId?: string };
  if (!resolveTargetGraph(ctx, graphId)) return;
  ctx.clearStrategy();
}

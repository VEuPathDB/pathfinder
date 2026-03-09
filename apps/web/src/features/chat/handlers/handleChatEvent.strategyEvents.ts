import type { Step } from "@pathfinder/shared";
import type { ChatEventContext } from "./handleChatEvent.types";
import type {
  StrategyUpdateData,
  GraphSnapshotData,
  StrategyLinkData,
  StrategyMetaData,
  GraphPlanData,
  ExecutorBuildRequestData,
  GraphClearedData,
} from "@/features/chat/sse_events";

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

export function handleStrategyUpdateEvent(
  ctx: ChatEventContext,
  data: StrategyUpdateData,
) {
  const { step, graphId } = data;
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

export function handleGraphSnapshotEvent(
  ctx: ChatEventContext,
  data: GraphSnapshotData,
) {
  const { graphSnapshot } = data;
  if (graphSnapshot) ctx.applyGraphSnapshot(graphSnapshot);
}

export function handleStrategyLinkEvent(ctx: ChatEventContext, data: StrategyLinkData) {
  const { graphId, wdkStrategyId, wdkUrl, name, description } = data;
  const targetGraphId = resolveTargetGraph(ctx, graphId);
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

export function handleStrategyMetaEvent(ctx: ChatEventContext, data: StrategyMetaData) {
  const { graphId, name, description, recordType, graphName } = data;
  if (!resolveTargetGraph(ctx, graphId)) return;
  ctx.setStrategyMeta({
    name: name ?? graphName ?? undefined,
    description: description ?? undefined,
    recordType: recordType ?? undefined,
  });
}

export function handleGraphPlanEvent(ctx: ChatEventContext, data: GraphPlanData) {
  const { graphId, name, description, recordType } = data;
  if (!resolveTargetGraph(ctx, graphId)) return;
  // Update strategy metadata from the plan event.
  ctx.setStrategyMeta({
    name: name ?? undefined,
    description: description ?? undefined,
    recordType: recordType ?? undefined,
  });
}

export function handleExecutorBuildRequestEvent(
  _ctx: ChatEventContext,
  _data: ExecutorBuildRequestData,
) {
  // executor_build_request is an informational event emitted when the backend
  // begins a build request.  No frontend action is needed — the subsequent
  // strategy_link / graph_plan events carry the actual results.
}

export function handleStrategyClearedEvent(
  ctx: ChatEventContext,
  data: GraphClearedData,
) {
  const { graphId } = data;
  if (!resolveTargetGraph(ctx, graphId)) return;
  ctx.clearStrategy();
}

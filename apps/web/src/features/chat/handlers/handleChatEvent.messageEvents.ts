import type {
  Citation,
  Message,
  OptimizationProgressData,
  OptimizationTrial,
  PlanningArtifact,
  ToolCall,
  Strategy,
} from "@pathfinder/shared";
import { DEFAULT_STREAM_NAME } from "@pathfinder/shared";
import type { ChatEventContext } from "./handleChatEvent.types";

/**
 * Resolve the current streaming assistant message index with fallback.
 *
 * If the tracked index is stale (null or negative), falls back to the
 * last message if it's an assistant message. Returns null when no valid
 * index can be resolved.
 */
function resolveAssistantIndex(
  streamingIndex: number | null,
  messages: readonly Message[],
): number | null {
  let idx = streamingIndex;
  if (
    (idx === null || idx < 0) &&
    messages[messages.length - 1]?.role === "assistant"
  ) {
    idx = messages.length - 1;
  }
  if (idx === null || idx < 0 || idx >= messages.length) return null;
  return idx;
}

export function snapshotSubKaniActivityFromBuffers(
  calls: Record<string, ToolCall[]>,
  status: Record<string, string>,
) {
  if (Object.keys(calls).length === 0) return undefined;
  return { calls: { ...calls }, status: { ...status } };
}

/**
 * Handle `user_message` events from the Redis stream catch-up.
 *
 * During normal streaming the user message is added locally by
 * `handleSendMessage` before the stream starts.  But during
 * **operation recovery** (page refresh / reconnect), the catch-up
 * replays events from Redis — including the user_message — and
 * we must append it so `mergeMessages` sees a complete conversation.
 */
export function handleUserMessageEvent(ctx: ChatEventContext, data: unknown) {
  const raw = data as { content?: string; messageId?: string };
  const content = typeof raw.content === "string" ? raw.content : "";
  if (!content) return;

  ctx.setMessages((prev) => {
    // De-duplicate: skip if the last user message has the same content
    // (can happen if data-loading and recovery both add it).
    for (let i = prev.length - 1; i >= 0; i--) {
      if (prev[i].role !== "user") continue;
      if (prev[i].content === content) return prev;
      break; // Only check the most recent user message
    }
    return [
      ...prev,
      {
        role: "user" as const,
        content,
        messageId: raw.messageId,
        timestamp: new Date().toISOString(),
      },
    ];
  });
}

export function handleMessageStartEvent(ctx: ChatEventContext, data: unknown) {
  const { strategyId, strategy } = data as {
    strategyId?: string;
    strategy?: Strategy;
  };

  if (strategyId) {
    ctx.setStrategyId(strategyId);
    ctx.addStrategy({
      id: strategyId,
      name: strategy?.name || DEFAULT_STREAM_NAME,
      title: strategy?.title || strategy?.name || DEFAULT_STREAM_NAME,
      siteId: ctx.siteId,
      recordType: strategy?.recordType ?? null,
      steps: strategy?.steps ?? [],
      rootStepId: strategy?.rootStepId ?? null,
      stepCount: strategy?.steps?.length ?? 0,
      wdkStrategyId: strategy?.wdkStrategyId,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
    ctx.loadGraph(strategyId);
  }

  if (strategy) {
    ctx.setStrategy(strategy);
    ctx.setStrategyMeta({
      name: strategy.name,
      recordType: strategy.recordType ?? undefined,
      siteId: strategy.siteId,
    });
  }
}

export function handleAssistantDeltaEvent(ctx: ChatEventContext, data: unknown) {
  const raw = data as { messageId?: string; delta?: unknown };
  const messageId = raw.messageId;
  const delta =
    typeof raw.delta === "string"
      ? raw.delta
      : Array.isArray(raw.delta)
        ? raw.delta.join("")
        : raw.delta
          ? String(raw.delta)
          : "";
  if (!delta) return;

  if (
    ctx.streamState.streamingAssistantIndex === null ||
    (messageId && ctx.streamState.streamingAssistantMessageId !== messageId)
  ) {
    ctx.streamState.streamingAssistantIndex = -1;
    ctx.streamState.streamingAssistantMessageId = messageId || null;

    const assistantMessage: Message = {
      role: "assistant",
      content: delta,
      optimizationProgress: ctx.streamState.optimizationProgress ?? undefined,
      timestamp: new Date().toISOString(),
    };
    ctx.setMessages((prev) => {
      const next = [...prev, assistantMessage];
      const resolvedIdx = next.length - 1;
      // Only resolve the sentinel; in batched delivery assistant_message may
      // have already finalized and cleared this ref.
      if (ctx.streamState.streamingAssistantIndex === -1) {
        ctx.streamState.streamingAssistantIndex = resolvedIdx;
      }
      // Always track the turn-level owner so optimization_progress events
      // can find the message even after streamingAssistantIndex is cleared.
      ctx.streamState.turnAssistantIndex = resolvedIdx;
      return next;
    });
    return;
  }

  ctx.setMessages((prev) => {
    const idx = resolveAssistantIndex(ctx.streamState.streamingAssistantIndex, prev);
    if (idx === null) return prev;
    const next = [...prev];
    const existing = next[idx];
    if (!existing || existing.role !== "assistant") return prev;
    next[idx] = { ...existing, content: (existing.content || "") + delta };
    return next;
  });
}

export function handleAssistantMessageEvent(ctx: ChatEventContext, data: unknown) {
  const raw = data as { messageId?: string; content?: unknown };
  const messageId = raw.messageId;
  const finalContent =
    typeof raw.content === "string"
      ? raw.content
      : Array.isArray(raw.content)
        ? raw.content.join("")
        : raw.content
          ? String(raw.content)
          : "";
  const subKaniActivity = snapshotSubKaniActivityFromBuffers(
    ctx.subKaniCallsBuffer,
    ctx.subKaniStatusBuffer,
  );

  const finalToolCalls =
    ctx.toolCallsBuffer.length > 0 ? [...ctx.toolCallsBuffer] : undefined;
  const finalCitations =
    ctx.citationsBuffer.length > 0 ? [...ctx.citationsBuffer] : undefined;
  const finalArtifacts =
    ctx.planningArtifactsBuffer.length > 0
      ? [...ctx.planningArtifactsBuffer]
      : undefined;
  const finalReasoning = ctx.streamState.reasoning ?? undefined;
  const finalOptimization = ctx.streamState.optimizationProgress ?? undefined;

  if (
    ctx.streamState.streamingAssistantIndex !== null &&
    (!messageId || ctx.streamState.streamingAssistantMessageId === messageId)
  ) {
    ctx.session.consumeUndoSnapshot();
    ctx.setMessages((prev) => {
      const idx = resolveAssistantIndex(ctx.streamState.streamingAssistantIndex, prev);
      if (idx === null) return prev;
      const next = [...prev];
      const existing = next[idx];
      if (!existing || existing.role !== "assistant") return prev;
      next[idx] = {
        ...existing,
        content: finalContent || existing.content,
        toolCalls: finalToolCalls ?? existing.toolCalls,
        subKaniActivity,
        citations: finalCitations ?? existing.citations,
        planningArtifacts: finalArtifacts ?? existing.planningArtifacts,
        reasoning: finalReasoning || existing.reasoning || undefined,
        optimizationProgress:
          finalOptimization ?? existing.optimizationProgress ?? undefined,
      };
      return next;
    });
  } else if (finalContent) {
    const assistantMessage: Message = {
      role: "assistant",
      content: finalContent,
      toolCalls: finalToolCalls,
      subKaniActivity,
      citations: finalCitations,
      planningArtifacts: finalArtifacts,
      reasoning: finalReasoning || undefined,
      optimizationProgress: finalOptimization,
      timestamp: new Date().toISOString(),
    };
    const snapshot = ctx.session.consumeUndoSnapshot();
    ctx.setMessages((prev) => {
      const next = [...prev, assistantMessage];
      ctx.streamState.turnAssistantIndex = next.length - 1;
      if (snapshot) {
        ctx.setUndoSnapshots((prevSnapshots) => ({
          ...prevSnapshots,
          [next.length - 1]: snapshot,
        }));
      }
      return next;
    });
  } else {
    ctx.session.consumeUndoSnapshot();
  }
  // Clear streaming refs after assistant_message finalize.  Late turn-level
  // events (e.g. optimization_progress) use turnAssistantIndex instead.
  ctx.streamState.streamingAssistantIndex = null;
  ctx.streamState.streamingAssistantMessageId = null;
  ctx.streamState.reasoning = null;
  ctx.toolCallsBuffer.length = 0;
  ctx.citationsBuffer.length = 0;
  ctx.planningArtifactsBuffer.length = 0;
}

export function handleCitationsEvent(ctx: ChatEventContext, data: unknown) {
  const citations = (data as { citations?: unknown }).citations;
  if (!Array.isArray(citations)) return;
  for (const c of citations) {
    if (c && typeof c === "object" && !Array.isArray(c)) {
      ctx.citationsBuffer.push(c as Citation);
    }
  }
}

export function handlePlanningArtifactEvent(ctx: ChatEventContext, data: unknown) {
  const artifact = (data as { planningArtifact?: unknown }).planningArtifact;
  if (!artifact || typeof artifact !== "object" || Array.isArray(artifact)) return;
  ctx.planningArtifactsBuffer.push(artifact as PlanningArtifact);
}

export function handleReasoningEvent(ctx: ChatEventContext, data: unknown) {
  const reasoning = (data as { reasoning?: string })?.reasoning;
  if (typeof reasoning !== "string") return;
  ctx.thinking.updateReasoning(reasoning);
  ctx.streamState.reasoning = reasoning;
}

export function handleOptimizationProgressEvent(ctx: ChatEventContext, data: unknown) {
  const progressData = data as OptimizationProgressData;
  const previous = ctx.streamState.optimizationProgress;

  const mergedTrialsByNumber = new Map<number, OptimizationTrial>();
  for (const t of previous?.allTrials ?? previous?.recentTrials ?? []) {
    mergedTrialsByNumber.set(t.trialNumber, t);
  }
  for (const t of progressData.allTrials ?? progressData.recentTrials ?? []) {
    mergedTrialsByNumber.set(t.trialNumber, t);
  }
  const mergedAllTrials = Array.from(mergedTrialsByNumber.values()).sort(
    (a, b) => a.trialNumber - b.trialNumber,
  );

  const normalizedProgress: OptimizationProgressData = {
    ...progressData,
    allTrials:
      mergedAllTrials.length > 0
        ? mergedAllTrials
        : (progressData.allTrials ?? progressData.recentTrials),
  };

  ctx.streamState.optimizationProgress = normalizedProgress;
  ctx.setOptimizationProgress(normalizedProgress);

  // Write optimization data only to the current turn's assistant message.
  // Never fall back to a generic "last assistant" scan, which would leak
  // live progress into a previous conversation turn.
  ctx.setMessages((prev) => {
    let idx: number | null = ctx.streamState.streamingAssistantIndex;
    if (idx == null || idx < 0) {
      idx = ctx.streamState.turnAssistantIndex ?? null;
    }
    if (
      idx == null ||
      idx < 0 ||
      idx >= prev.length ||
      prev[idx]?.role !== "assistant"
    ) {
      return prev;
    }
    const next = [...prev];
    next[idx] = { ...prev[idx], optimizationProgress: normalizedProgress };
    return next;
  });
}

export function handleErrorEvent(ctx: ChatEventContext, data: unknown) {
  const { error } = data as { error: string };
  const assistantMessage: Message = {
    role: "assistant",
    content: `⚠️ Error: ${error}`,
    timestamp: new Date().toISOString(),
  };
  ctx.setMessages((prev) => [...prev, assistantMessage]);
  ctx.onApiError?.(error);
}

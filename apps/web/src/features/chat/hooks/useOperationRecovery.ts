/**
 * Recover active chat operations on page load / strategy change.
 *
 * When the user refreshes while a chat operation is in-flight, this hook
 * discovers the active operation and re-subscribes to its SSE stream so
 * the UI resumes where it left off.
 */

import { useEffect, useRef } from "react";
import type { Message, ToolCall, StrategyWithMeta } from "@pathfinder/shared";
import type { Dispatch, SetStateAction } from "react";
import {
  fetchActiveOperations,
  subscribeToOperation,
  type OperationSubscription,
} from "@/lib/operationSubscribe";
import { parseChatSSEEvent } from "@/features/chat/sse_events";
import type { ChatSSEEvent } from "@/features/chat/sse_events";
import { handleChatEvent } from "@/features/chat/handlers/handleChatEvent";
import type { ChatEventContext } from "@/features/chat/handlers/handleChatEvent";
import type { useThinkingState } from "@/features/chat/hooks/useThinkingState";
import { StreamingSession } from "@/features/chat/streaming/StreamingSession";
import { snapshotSubKaniActivityFromBuffers } from "@/features/chat/handlers/handleChatEvent.messageEvents";

interface UseOperationRecoveryArgs {
  strategyId: string | null;
  siteId: string;
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;
  setMessages: Dispatch<SetStateAction<Message[]>>;
  setUndoSnapshots: Dispatch<SetStateAction<Record<number, StrategyWithMeta>>>;
  thinking: ReturnType<typeof useThinkingState>;
  currentStrategy: StrategyWithMeta | null;
  setStrategyId: (id: string | null) => void;
  addStrategy: ChatEventContext["addStrategy"];
  addExecutedStrategy: (s: StrategyWithMeta) => void;
  setWdkInfo: ChatEventContext["setWdkInfo"];
  setStrategy: (s: StrategyWithMeta | null) => void;
  setStrategyMeta: ChatEventContext["setStrategyMeta"];
  clearStrategy: () => void;
  addStep: ChatEventContext["addStep"];
  loadGraph: (id: string) => void;
  parseToolArguments: ChatEventContext["parseToolArguments"];
  parseToolResult: ChatEventContext["parseToolResult"];
  applyGraphSnapshot: ChatEventContext["applyGraphSnapshot"];
  getStrategy: (id: string) => Promise<StrategyWithMeta>;
  attachThinkingToLastAssistant: (
    calls: ToolCall[],
    activity?: { calls: Record<string, ToolCall[]>; status: Record<string, string> },
  ) => void;
  onApiError?: (msg: string) => void;
  setOptimizationProgress: ChatEventContext["setOptimizationProgress"];
}

/**
 * On mount (or when strategyId changes), check for active chat operations
 * and re-subscribe to resume streaming.
 */
export function useOperationRecovery({
  strategyId,
  siteId,
  isStreaming,
  setIsStreaming,
  setMessages,
  setUndoSnapshots,
  thinking,
  currentStrategy,
  setStrategyId,
  addStrategy,
  addExecutedStrategy,
  setWdkInfo,
  setStrategy,
  setStrategyMeta,
  clearStrategy,
  addStep,
  loadGraph,
  parseToolArguments,
  parseToolResult,
  applyGraphSnapshot,
  getStrategy,
  attachThinkingToLastAssistant,
  onApiError,
  setOptimizationProgress,
}: UseOperationRecoveryArgs) {
  const recoveredRef = useRef<string | null>(null);
  const subscriptionRef = useRef<OperationSubscription | null>(null);

  useEffect(() => {
    if (!strategyId) return;
    if (isStreaming) return;
    // Only recover once per strategyId to avoid re-subscribing loops.
    if (recoveredRef.current === strategyId) return;
    recoveredRef.current = strategyId;

    let cancelled = false;

    fetchActiveOperations({ type: "chat", streamId: strategyId })
      .then((ops) => {
        if (cancelled || ops.length === 0) return;
        // Pick the most recent active operation.
        const op = ops[0];

        setIsStreaming(true);
        thinking.reset();

        const session = new StreamingSession(currentStrategy);
        const streamState: ChatEventContext["streamState"] = {
          streamingAssistantIndex: null,
          streamingAssistantMessageId: null,
          turnAssistantIndex: null,
          reasoning: null,
          optimizationProgress: null,
        };
        const toolCalls: ToolCall[] = [];
        const citationsBuffer: import("@pathfinder/shared").Citation[] = [];
        const planningArtifactsBuffer: import("@pathfinder/shared").PlanningArtifact[] =
          [];
        const subKaniCallsBuffer: Record<string, ToolCall[]> = {};
        const subKaniStatusBuffer: Record<string, string> = {};

        const sub = subscribeToOperation<Record<string, unknown>>(op.operationId, {
          onEvent: ({ type, data }) => {
            const event: ChatSSEEvent = parseChatSSEEvent({ type, data });
            handleChatEvent(
              {
                siteId,
                strategyIdAtStart: strategyId,
                toolCallsBuffer: toolCalls,
                citationsBuffer,
                planningArtifactsBuffer,
                subKaniCallsBuffer,
                subKaniStatusBuffer,
                thinking,
                setStrategyId,
                addStrategy,
                addExecutedStrategy,
                setWdkInfo,
                setStrategy,
                setStrategyMeta,
                clearStrategy,
                addStep,
                loadGraph,
                session,
                currentStrategy,
                setMessages,
                setUndoSnapshots,
                parseToolArguments,
                parseToolResult,
                applyGraphSnapshot,
                getStrategy,
                streamState,
                setOptimizationProgress,
                onApiError,
              },
              event,
            );
          },
          onComplete: () => {
            setIsStreaming(false);
            subscriptionRef.current = null;
            thinking.finalizeToolCalls(toolCalls.length > 0 ? [...toolCalls] : []);
            const activity = snapshotSubKaniActivityFromBuffers(
              subKaniCallsBuffer,
              subKaniStatusBuffer,
            );
            attachThinkingToLastAssistant(
              toolCalls.length > 0 ? [...toolCalls] : [],
              activity,
            );
          },
          onError: () => {
            setIsStreaming(false);
            subscriptionRef.current = null;
          },
          endEventTypes: new Set(["message_end"]),
        });

        subscriptionRef.current = sub;
      })
      .catch(() => {
        // Discovery failed — not critical, user can still interact.
      });

    return () => {
      cancelled = true;
      subscriptionRef.current?.unsubscribe();
      subscriptionRef.current = null;
      // Reset so returning to this strategy (A→B→A) triggers recovery again.
      recoveredRef.current = null;
    };
    // Only run on strategyId changes, not on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategyId]);
}

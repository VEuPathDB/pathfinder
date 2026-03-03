import { useCallback, useState } from "react";
import type {
  ChatMention,
  Message,
  ToolCall,
  Citation,
  ModelSelection,
  OptimizationProgressData,
  PlanningArtifact,
  StrategyStep,
  StrategyWithMeta,
} from "@pathfinder/shared";
import type { ChatSSEEvent } from "@/features/chat/sse_events";
import { streamChat } from "@/features/chat/stream";
import type { StreamChatResult } from "@/features/chat/stream";
import { handleChatEvent } from "@/features/chat/handlers/handleChatEvent";
import type { ChatEventContext } from "@/features/chat/handlers/handleChatEvent";
import { snapshotSubKaniActivityFromBuffers } from "@/features/chat/handlers/handleChatEvent.messageEvents";
import { encodeNodeSelection } from "@/features/chat/node_selection";
import { useSessionStore } from "@/state/useSessionStore";
import { cancelOperation, type OperationSubscription } from "@/lib/operationSubscribe";
import type { GraphSnapshotInput } from "@/features/chat/utils/graphSnapshot";
import type { useThinkingState } from "@/features/chat/hooks/useThinkingState";
import type { StreamingSession } from "@/features/chat/streaming/StreamingSession";

type Thinking = ReturnType<typeof useThinkingState>;
type AddStrategyInput = Parameters<ChatEventContext["addStrategy"]>[0];

interface UseChatStreamingArgs {
  siteId: string;
  strategyId: string | null;
  draftSelection: Record<string, unknown> | null;
  setDraftSelection: (selection: Record<string, unknown> | null) => void;
  thinking: Thinking;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  setUndoSnapshots: React.Dispatch<
    React.SetStateAction<Record<number, StrategyWithMeta>>
  >;
  sessionRef: { current: StreamingSession | null };
  createSession: () => StreamingSession;
  loadGraph: (graphId: string) => void;
  addStrategy: (strategy: AddStrategyInput) => void;
  addExecutedStrategy: (strategy: StrategyWithMeta) => void;
  setStrategyId: (id: string | null) => void;
  setWdkInfo: ChatEventContext["setWdkInfo"];
  setStrategy: (strategy: StrategyWithMeta | null) => void;
  setStrategyMeta: ChatEventContext["setStrategyMeta"];
  clearStrategy: () => void;
  addStep: (step: StrategyStep) => void;
  parseToolArguments: ChatEventContext["parseToolArguments"];
  parseToolResult: ChatEventContext["parseToolResult"];
  applyGraphSnapshot: (graphSnapshot: GraphSnapshotInput) => void;
  getStrategy: (id: string) => Promise<StrategyWithMeta>;
  currentStrategy: StrategyWithMeta | null;
  attachThinkingToLastAssistant: (
    calls: ToolCall[],
    activity?: { calls: Record<string, ToolCall[]>; status: Record<string, string> },
  ) => void;
  /** Per-request model/provider/reasoning selection. */
  modelSelection?: ModelSelection | null;
  onApiError?: (message: string) => void;
  /** Called after streaming completes successfully. */
  onStreamComplete?: () => void;
  /** Called after streaming errors out (in addition to the default error handling). */
  onStreamError?: (error: Error) => void;
}

export function useChatStreaming({
  siteId,
  strategyId,
  draftSelection,
  setDraftSelection,
  thinking,
  setMessages,
  setUndoSnapshots,
  sessionRef,
  createSession,
  loadGraph,
  addStrategy,
  addExecutedStrategy,
  setStrategyId,
  setWdkInfo,
  setStrategy,
  setStrategyMeta,
  clearStrategy,
  addStep,
  parseToolArguments,
  parseToolResult,
  applyGraphSnapshot,
  getStrategy,
  currentStrategy,
  attachThinkingToLastAssistant,
  modelSelection,
  onApiError,
  onStreamComplete,
  onStreamError,
}: UseChatStreamingArgs) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [optimizationProgress, setOptimizationProgress] =
    useState<OptimizationProgressData | null>(null);
  const [subscription, setSubscription] = useState<OperationSubscription | null>(null);
  const [operationId, setOperationId] = useState<string | null>(null);

  const stopStreaming = useCallback(() => {
    if (operationId) {
      void cancelOperation(operationId);
    }
    subscription?.unsubscribe();
    setSubscription(null);
    setOperationId(null);
    setIsStreaming(false);
  }, [subscription, operationId]);

  /**
   * Shared stream setup -- resets state, wires event handling, and calls
   * ``streamChat``.  Used by both ``handleSendMessage`` (user-initiated)
   * and ``handleAutoExecute`` (system-initiated, no visible user message).
   */
  const executeStream = useCallback(
    async (
      content: string,
      streamContext: {
        strategyId?: string;
        mentions?: ChatMention[];
      },
    ) => {
      setIsStreaming(true);
      setApiError(null);
      thinking.reset();
      setOptimizationProgress(null);

      const session = createSession();
      sessionRef.current = session;

      const streamState: ChatEventContext["streamState"] = {
        streamingAssistantIndex: null,
        streamingAssistantMessageId: null,
        turnAssistantIndex: null,
        reasoning: null,
        optimizationProgress: null,
      };

      const toolCalls: ToolCall[] = [];
      const citationsBuffer: Citation[] = [];
      const planningArtifactsBuffer: PlanningArtifact[] = [];
      const subKaniCallsBuffer: Record<string, ToolCall[]> = {};
      const subKaniStatusBuffer: Record<string, string> = {};

      const effectiveStrategyId = streamContext.strategyId ?? strategyId;

      let result: StreamChatResult;
      try {
        result = await streamChat(
          content,
          siteId,
          {
            onMessage: (event: ChatSSEEvent) => {
              handleChatEvent(
                {
                  siteId,
                  strategyIdAtStart: effectiveStrategyId ?? null,
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
              setSubscription(null);
              setOperationId(null);
              thinking.finalizeToolCalls(toolCalls.length > 0 ? [...toolCalls] : []);
              const subKaniActivity = snapshotSubKaniActivityFromBuffers(
                subKaniCallsBuffer,
                subKaniStatusBuffer,
              );
              attachThinkingToLastAssistant(
                toolCalls.length > 0 ? [...toolCalls] : [],
                subKaniActivity,
              );

              // Persist reasoning to the last assistant message.
              const savedReasoning = streamState.reasoning;
              if (savedReasoning) {
                setMessages((prev) => {
                  for (let i = prev.length - 1; i >= 0; i -= 1) {
                    if (prev[i].role !== "assistant") continue;
                    const msg = prev[i];
                    if (msg.reasoning) return prev;
                    const next = [...prev];
                    next[i] = { ...msg, reasoning: savedReasoning };
                    return next;
                  }
                  return prev;
                });
              }

              // Force-write optimization data to the last assistant message.
              const savedOptimization = streamState.optimizationProgress;
              if (savedOptimization) {
                setMessages((prev) => {
                  for (let i = prev.length - 1; i >= 0; i -= 1) {
                    if (prev[i].role !== "assistant") continue;
                    const next = [...prev];
                    next[i] = {
                      ...prev[i],
                      optimizationProgress: savedOptimization,
                    };
                    return next;
                  }
                  return prev;
                });
              }

              if (effectiveStrategyId && !session.snapshotApplied) {
                getStrategy(effectiveStrategyId)
                  .then((full) => {
                    // Guard against race: only apply if the user hasn't
                    // switched to a different strategy while awaiting.
                    const currentId = useSessionStore.getState().strategyId;
                    if (currentId !== effectiveStrategyId) return;
                    setStrategy(full);
                    setStrategyMeta({
                      name: full.name,
                      recordType: full.recordType ?? undefined,
                      siteId: full.siteId,
                    });
                  })
                  .catch((err) =>
                    console.error(
                      "[useChatStreaming] Failed to refresh strategy after stream:",
                      err,
                    ),
                  );
              }
              onStreamComplete?.();
            },

            onError: (error) => {
              setIsStreaming(false);
              setSubscription(null);
              setOperationId(null);
              thinking.finalizeToolCalls(toolCalls.length > 0 ? [...toolCalls] : []);

              const isAbort =
                error.name === "AbortError" ||
                (error.message && /abort/i.test(error.message));
              if (isAbort) return;

              console.error("Chat error:", error);
              setApiError(error.message || "Unable to reach the API.");
              onStreamError?.(error);
            },
          },
          streamContext,
          undefined, // signal — subscription handles cleanup via unsubscribe
          modelSelection ?? undefined,
        );
      } catch (e) {
        // streamChat can throw if no onError handler catches the health check
        // failure, or if requestJson throws (network error, 4xx/5xx).
        setIsStreaming(false);
        const error = e instanceof Error ? e : new Error(String(e));
        console.error("Chat error:", error);
        setApiError(error.message || "Unable to reach the API.");
        onStreamError?.(error);
        return;
      }

      setSubscription(result.subscription);
      setOperationId(result.operationId);

      // Use the strategyId from the response if we didn't have one.
      if (!streamContext.strategyId && result.strategyId) {
        setStrategyId(result.strategyId);
      }
    },
    [
      setMessages,
      thinking,
      sessionRef,
      createSession,
      siteId,
      strategyId,
      setStrategyId,
      addStrategy,
      addExecutedStrategy,
      setWdkInfo,
      setStrategy,
      setStrategyMeta,
      clearStrategy,
      addStep,
      loadGraph,
      currentStrategy,
      setUndoSnapshots,
      parseToolArguments,
      parseToolResult,
      applyGraphSnapshot,
      getStrategy,
      attachThinkingToLastAssistant,
      modelSelection,
      onApiError,
      onStreamComplete,
      onStreamError,
    ],
  );

  /** User-initiated send -- appends a visible user message then streams. */
  const handleSendMessage = useCallback(
    async (content: string, mentions?: ChatMention[]) => {
      const finalContent = encodeNodeSelection(draftSelection, content);
      const userMessage: Message = {
        role: "user",
        content: finalContent,
        mentions: mentions?.length ? mentions : undefined,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      if (draftSelection) {
        setDraftSelection(null);
      }

      const streamContext = {
        strategyId: strategyId ?? undefined,
        mentions,
      };

      await executeStream(finalContent, streamContext);
    },
    [draftSelection, setMessages, setDraftSelection, strategyId, executeStream],
  );

  /**
   * System-initiated execution -- sends the prompt to the model without
   * adding a visible user message.  Used for auto-handoff scenarios.
   */
  const handleAutoExecute = useCallback(
    async (prompt: string, targetStrategyId: string) => {
      await executeStream(prompt, { strategyId: targetStrategyId });
    },
    [executeStream],
  );

  return {
    handleSendMessage,
    handleAutoExecute,
    stopStreaming,
    isStreaming,
    apiError,
    setIsStreaming,
    optimizationProgress,
    setOptimizationProgress,
  };
}

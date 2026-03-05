import type { Dispatch, SetStateAction } from "react";
import type { Message, ToolCall, Strategy } from "@pathfinder/shared";
import type { useThinkingState } from "@/features/chat/hooks/useThinkingState";
import type { GraphSnapshotInput } from "@/features/chat/utils/graphSnapshot";
import type { StreamingSession } from "@/features/chat/streaming/StreamingSession";

type ThinkingState = ReturnType<typeof useThinkingState>;

interface BuildUnifiedChatStreamingArgsParams {
  siteId: string;
  strategyId: string | null;
  draftSelection: Record<string, unknown> | null;
  setDraftSelection: Dispatch<SetStateAction<Record<string, unknown> | null>>;
  thinking: ThinkingState;
  setMessages: Dispatch<SetStateAction<Message[]>>;
  setUndoSnapshots: Dispatch<SetStateAction<Record<number, Strategy>>>;
  sessionRef: { current: StreamingSession | null };
  createSession: () => StreamingSession;
  loadGraph: (graphId: string) => void;
  addStrategy: (s: Strategy) => void;
  addExecutedStrategy: (s: Strategy) => void;
  setStrategyIdGlobal: (id: string | null) => void;
  setWdkInfo: (
    wdkStrategyId: number,
    wdkUrl?: string | null,
    name?: string | null,
    description?: string | null,
  ) => void;
  setStrategy: (strategy: Strategy | null) => void;
  setStrategyMeta: (meta: Partial<Strategy>) => void;
  clearStrategy: () => void;
  addStep: (step: Strategy["steps"][number]) => void;
  parseToolArguments: (args: unknown) => Record<string, unknown>;
  parseToolResult: (
    result?: string | null,
  ) => { graphSnapshot?: Record<string, unknown> } | null;
  applyGraphSnapshot: (graphSnapshot: GraphSnapshotInput) => void;
  getStrategy: (id: string) => Promise<Strategy>;
  currentStrategy: Strategy | null;
  attachThinkingToLastAssistant: (
    calls: ToolCall[],
    activity?: {
      calls: Record<string, ToolCall[]>;
      status: Record<string, string>;
    },
  ) => void;
  currentModelSelection: ReturnType<
    typeof import("@/features/chat/components/MessageComposer").buildModelSelection
  >;
  setChatIsStreaming: (value: boolean) => void;
  handleError: (error: unknown, fallback: string) => void;
}

export function useUnifiedChatStreamingArgs({
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
  setStrategyIdGlobal,
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
  currentModelSelection,
  setChatIsStreaming,
  handleError,
}: BuildUnifiedChatStreamingArgsParams) {
  return {
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
    setStrategyId: setStrategyIdGlobal,
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
    modelSelection: currentModelSelection,
    onStreamComplete: () => setChatIsStreaming(false),
    onStreamError: (error: Error) => {
      setChatIsStreaming(false);
      handleError(error, "Unable to reach the API.");
    },
  };
}

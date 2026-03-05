import type { Dispatch, SetStateAction } from "react";
import type {
  Message,
  ToolCall,
  Citation,
  PlanningArtifact,
  OptimizationProgressData,
  Step,
  Strategy,
} from "@pathfinder/shared";
import type { useThinkingState } from "@/features/chat/hooks/useThinkingState";
import type { StreamingSession } from "@/features/chat/streaming/StreamingSession";

type Thinking = ReturnType<typeof useThinkingState>;

export type StreamSessionState = {
  streamingAssistantIndex: number | null;
  streamingAssistantMessageId: string | null;
  /** Owner assistant message for the current stream turn. */
  turnAssistantIndex?: number | null;
  reasoning: string | null;
  optimizationProgress: OptimizationProgressData | null;
};

export type ChatEventContext = {
  siteId: string;
  strategyIdAtStart: string | null;
  toolCallsBuffer: ToolCall[];
  citationsBuffer: Citation[];
  planningArtifactsBuffer: PlanningArtifact[];
  subKaniCallsBuffer: Record<string, ToolCall[]>;
  subKaniStatusBuffer: Record<string, string>;
  thinking: Thinking;

  // Strategy/session actions
  setStrategyId: (id: string | null) => void;
  addStrategy: (s: Strategy) => void;
  addExecutedStrategy: (s: Strategy) => void;
  setWdkInfo: (
    wdkStrategyId: number,
    wdkUrl?: string | null,
    name?: string | null,
    description?: string | null,
  ) => void;
  setStrategy: (s: Strategy | null) => void;
  setStrategyMeta: (u: Partial<Strategy>) => void;
  clearStrategy: () => void;
  addStep: (s: Step) => void;
  loadGraph: (graphId: string) => void;

  /** Mutable streaming session scoped to this stream. */
  session: StreamingSession;
  currentStrategy: Strategy | null;

  // UI state setters
  setMessages: Dispatch<SetStateAction<Message[]>>;
  setUndoSnapshots: Dispatch<SetStateAction<Record<number, Strategy>>>;

  // Helpers
  parseToolArguments: (args: unknown) => Record<string, unknown>;
  parseToolResult: (
    result?: string | null,
  ) => { graphSnapshot?: Record<string, unknown> } | null;
  applyGraphSnapshot: (graphSnapshot: Record<string, unknown>) => void;
  getStrategy: (id: string) => Promise<Strategy>;
  streamState: StreamSessionState;

  setOptimizationProgress: Dispatch<SetStateAction<OptimizationProgressData | null>>;

  onApiError?: (message: string) => void;
};

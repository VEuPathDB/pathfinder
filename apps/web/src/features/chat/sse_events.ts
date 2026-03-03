import type {
  Citation,
  PlanningArtifact,
  OptimizationProgressData,
  StrategyWithMeta,
} from "@pathfinder/shared";
import type { RawSSEEvent } from "@/lib/sse";
import { isRecord } from "@/lib/utils/isRecord";

export type ChatSSEEvent =
  | {
      type: "message_start";
      data: {
        strategyId?: string;
        strategy?: StrategyWithMeta;
        authToken?: string;
      };
    }
  | { type: "user_message"; data: { messageId?: string; content?: string } }
  | { type: "assistant_delta"; data: { messageId?: string; delta?: string } }
  | { type: "assistant_message"; data: { messageId?: string; content?: string } }
  | { type: "citations"; data: { citations?: Citation[] } }
  | { type: "planning_artifact"; data: { planningArtifact?: PlanningArtifact } }
  | { type: "reasoning"; data: { reasoning?: string } }
  | { type: "tool_call_start"; data: { id: string; name: string; arguments?: string } }
  | { type: "tool_call_end"; data: { id: string; result: string } }
  | { type: "subkani_task_start"; data: { task?: string } }
  | {
      type: "subkani_tool_call_start";
      data: { task?: string; id: string; name: string; arguments?: string };
    }
  | {
      type: "subkani_tool_call_end";
      data: { task?: string; id: string; result: string };
    }
  | { type: "subkani_task_end"; data: { task?: string; status?: string } }
  | { type: "strategy_update"; data: Record<string, unknown> }
  | { type: "graph_snapshot"; data: { graphSnapshot?: Record<string, unknown> } }
  | {
      type: "strategy_link";
      data: {
        graphId?: string;
        strategySnapshotId?: string;
        wdkStrategyId?: number;
        wdkUrl?: string;
        name?: string;
        description?: string;
      };
    }
  | {
      type: "strategy_meta";
      data: {
        graphId?: string;
        graphName?: string;
        name?: string;
        description?: string;
        recordType?: string | null;
      };
    }
  | { type: "graph_cleared"; data: { graphId?: string } }
  | {
      type: "optimization_progress";
      data: OptimizationProgressData;
    }
  | { type: "error"; data: { error: string } }
  | { type: "unknown"; data: Record<string, unknown> | string; rawType: string };

function safeJsonParse(text: string): Record<string, unknown> | string {
  try {
    const parsed = JSON.parse(text);
    return isRecord(parsed) ? parsed : text;
  } catch {
    return text;
  }
}

export function parseChatSSEEvent(
  event: RawSSEEvent | { type: string; data: Record<string, unknown> },
): ChatSSEEvent {
  const data = typeof event.data === "string" ? safeJsonParse(event.data) : event.data;
  const type = event.type;

  switch (type) {
    case "message_start":
    case "user_message":
    case "assistant_delta":
    case "assistant_message":
    case "citations":
    case "planning_artifact":
    case "reasoning":
    case "tool_call_start":
    case "tool_call_end":
    case "subkani_task_start":
    case "subkani_tool_call_start":
    case "subkani_tool_call_end":
    case "subkani_task_end":
    case "strategy_update":
    case "graph_snapshot":
    case "strategy_link":
    case "strategy_meta":
    case "graph_cleared":
    case "optimization_progress":
    case "error":
      return { type, data } as ChatSSEEvent;
    default:
      return {
        type: "unknown",
        rawType: type,
        data,
      };
  }
}

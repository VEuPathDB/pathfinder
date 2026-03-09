/**
 * Shared streaming API functions — used by both workbench and analysis features.
 */

import { streamSSEParsed } from "@/lib/sse";
import type { StepParameters } from "@/lib/strategyGraph/types";

// ---------------------------------------------------------------------------
// AI Assist stream
// ---------------------------------------------------------------------------

export type WizardStep =
  | "search"
  | "parameters"
  | "controls"
  | "run"
  | "results"
  | "analysis";

export interface AiAssistMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AiAssistHandlers {
  onDelta?: (delta: string) => void;
  onToolCall?: (name: string, status: "start" | "end") => void;
  onComplete?: (fullText: string) => void;
  onError?: (error: string) => void;
}

/** SSE data shapes for AI assist events. */
type AiAssistSSEData =
  | { delta: string }
  | { content: string }
  | { name: string }
  | { error: string };

/** Contextual data sent with an AI assist request. */
export interface AiAssistContext {
  experimentId?: string;
  searchName?: string;
  recordType?: string;
  mode?: string;
  strategySummary?: string;
  parameters?: StepParameters;
  positiveControls?: string[];
  negativeControls?: string[];
  geneListsSummary?: string;
  [key: string]: unknown;
}

export function streamAiAssist(
  params: {
    siteId: string;
    step: WizardStep;
    message: string;
    context: AiAssistContext;
    history: AiAssistMessage[];
    model?: string;
  },
  handlers: AiAssistHandlers,
): AbortController {
  const controller = new AbortController();
  let fullText = "";
  let completed = false;

  streamSSEParsed<AiAssistSSEData>(
    "/api/v1/experiments/ai-assist",
    {
      body: {
        siteId: params.siteId,
        step: params.step,
        message: params.message,
        context: params.context,
        history: params.history,
        model: params.model ?? null,
      },
      signal: controller.signal,
    },
    {
      onError: (err) => handlers.onError?.(err.message),
      onFrame: ({ event, data }) => {
        if (event === "assistant_delta" && "delta" in data) {
          const delta = typeof data.delta === "string" ? data.delta : "";
          fullText += delta;
          handlers.onDelta?.(delta);
        } else if (event === "assistant_message" && "content" in data) {
          const content = typeof data.content === "string" ? data.content : "";
          if (content && content !== fullText) {
            const missing = content.slice(fullText.length);
            if (missing) handlers.onDelta?.(missing);
            fullText = content;
          }
        } else if (event === "tool_call_start" && "name" in data) {
          handlers.onToolCall?.(
            typeof data.name === "string" ? data.name : "tool",
            "start",
          );
        } else if (event === "tool_call_end" && "name" in data) {
          handlers.onToolCall?.(
            typeof data.name === "string" ? data.name : "tool",
            "end",
          );
        } else if (event === "error" && "error" in data) {
          handlers.onError?.(
            typeof data.error === "string" ? data.error : "Unknown error",
          );
        } else if (event === "message_end" && !completed) {
          completed = true;
          handlers.onComplete?.(fullText);
        }
      },
    },
  ).catch((err) => console.error("[experiment.stream]", err));

  return controller;
}

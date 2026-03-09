import { isRecord } from "@/lib/utils/isRecord";
import type { StepParameters } from "@/lib/strategyGraph/types";

/**
 * Parsed tool arguments — matches the dynamic key/value shape of WDK
 * step parameters since tool calls typically carry search parameters.
 */
export type ToolArguments = StepParameters;

export function parseToolArguments(args: unknown): ToolArguments {
  if (!args) return {};
  if (isRecord(args)) return args;
  if (typeof args !== "string") return {};
  try {
    const parsed = JSON.parse(args);
    if (isRecord(parsed)) return parsed;
    return {};
  } catch {
    return {};
  }
}

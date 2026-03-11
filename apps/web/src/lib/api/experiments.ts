/**
 * Shared experiment API functions -- used by both workbench and chat features.
 */

import type { ExperimentSummary } from "@pathfinder/shared";
import {
  APIError,
  buildUrl,
  getAuthHeaders,
  requestJsonValidated,
} from "@/lib/api/http";
import { ExperimentSummaryListSchema } from "./schemas/experiment";

/** List experiments, optionally filtered by site. */
export async function listExperiments(
  siteId?: string | null,
): Promise<ExperimentSummary[]> {
  return (await requestJsonValidated(
    ExperimentSummaryListSchema,
    "/api/v1/experiments",
    { query: siteId ? { siteId } : undefined },
  )) as ExperimentSummary[];
}

/**
 * Seed demo strategies via SSE. Calls `onMessage` for each progress event
 * and resolves when the stream ends.
 */
export async function seedExperiments(
  onMessage: (message: string) => void,
  siteId?: string,
): Promise<void> {
  const params = siteId ? `?site_id=${siteId}` : "";
  const url = buildUrl(`/api/v1/experiments/seed${params}`);
  const headers = getAuthHeaders({ accept: "text/event-stream" });

  const response = await fetch(url, {
    method: "POST",
    headers,
    credentials: "include",
  });

  if (!response.ok || !response.body) {
    throw new APIError(`Seed failed: HTTP ${response.status}`, {
      status: response.status,
      statusText: response.statusText,
      url,
      data: null,
    });
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data:")) continue;
      try {
        const data = JSON.parse(line.slice(5).trim());
        if (data.message) onMessage(data.message);
      } catch {
        /* skip malformed SSE frames */
      }
    }
  }
}

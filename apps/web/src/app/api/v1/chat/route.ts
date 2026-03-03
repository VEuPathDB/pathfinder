/**
 * Proxy for the /api/v1/chat endpoint.
 *
 * The backend returns 202 JSON {operationId, strategyId}.
 * The client subscribes to /operations/{id}/subscribe for SSE events.
 */

import { type NextRequest } from "next/server";

import { proxyJsonRequest } from "../_proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  return proxyJsonRequest(req, "/api/v1/chat", { includeBody: true });
}

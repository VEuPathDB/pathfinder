/**
 * Proxy for /api/v1/experiments/batch — returns 202 JSON {operationId}.
 */

import { type NextRequest } from "next/server";

import { proxyJsonRequest } from "../../_proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  return proxyJsonRequest(req, "/api/v1/experiments/batch", { includeBody: true });
}

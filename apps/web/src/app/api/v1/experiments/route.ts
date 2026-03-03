/**
 * Route handler for /api/v1/experiments.
 *
 * - GET: plain JSON proxy (list experiments).
 * - POST: JSON proxy (create experiment, returns 202 {operationId}).
 * - DELETE: plain JSON proxy (delete experiment).
 */

import { type NextRequest } from "next/server";

import { proxyJsonRequest } from "../_proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  const path = `/api/v1/experiments${qs ? `?${qs}` : ""}`;
  return proxyJsonRequest(req, path);
}

export async function POST(req: NextRequest) {
  return proxyJsonRequest(req, "/api/v1/experiments", { includeBody: true });
}

export async function DELETE(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  const path = `/api/v1/experiments${qs ? `?${qs}` : ""}`;
  return proxyJsonRequest(req, path, { method: "DELETE" });
}

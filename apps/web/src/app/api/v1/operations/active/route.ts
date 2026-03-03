import { type NextRequest } from "next/server";

import { proxyJsonRequest } from "@/app/api/v1/_proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  return proxyJsonRequest(req, `/api/v1/operations/active${qs ? `?${qs}` : ""}`);
}

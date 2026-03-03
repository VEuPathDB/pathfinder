import { type NextRequest } from "next/server";

import { proxySSEGet } from "@/app/api/v1/_proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  return proxySSEGet(req, `/api/v1/operations/${id}/subscribe${qs ? `?${qs}` : ""}`);
}

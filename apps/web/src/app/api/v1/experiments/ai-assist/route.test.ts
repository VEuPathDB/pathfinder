import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../_proxy", () => ({
  proxySSEPost: vi.fn(async () => new Response("data: ok\n\n", { status: 200 })),
}));

import { NextRequest } from "next/server";

import { proxySSEPost } from "../../_proxy";
import { POST } from "./route";

const proxyMock = vi.mocked(proxySSEPost);

function makeReq(
  path: string,
  init?: { method?: string; body?: string; headers?: Record<string, string> },
): NextRequest {
  return new NextRequest(new URL(path, "http://localhost:3000"), init);
}

describe("POST /api/v1/experiments/ai-assist", () => {
  beforeEach(() => proxyMock.mockClear());

  it("proxies SSE POST to /api/v1/experiments/ai-assist", async () => {
    const req = makeReq("/api/v1/experiments/ai-assist", {
      method: "POST",
      body: '{"prompt":"analyze"}',
      headers: { "content-type": "application/json" },
    });
    await POST(req);

    expect(proxyMock).toHaveBeenCalledOnce();
    const [passedReq, path] = proxyMock.mock.calls[0];
    expect(passedReq).toBe(req);
    expect(path).toBe("/api/v1/experiments/ai-assist");
  });
});

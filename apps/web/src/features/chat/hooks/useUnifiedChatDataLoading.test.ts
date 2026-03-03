/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { Message, StrategyWithMeta } from "@pathfinder/shared";
import { useUnifiedChatDataLoading } from "./useUnifiedChatDataLoading";

// --- Mocks ---

const mockStrategy: StrategyWithMeta = {
  id: "strategy-1",
  name: "Test Strategy",
  siteId: "plasmodb",
  steps: [],
  rootStepId: null,
  recordType: null,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  messages: [
    { role: "user", content: "hello", timestamp: new Date().toISOString() },
    { role: "assistant", content: "hi there", timestamp: new Date().toISOString() },
  ],
};

let mockGetStrategy: ReturnType<typeof vi.fn>;

vi.mock("@/lib/api/client", () => ({
  APIError: class APIError extends Error {
    status: number;
    constructor(message: string, args: { status: number }) {
      super(message);
      this.name = "APIError";
      this.status = args.status;
    }
  },
  get getStrategy() {
    return mockGetStrategy;
  },
}));

// Mock useSessionStore to control authToken
let mockAuthToken: string | null = "valid-token";
vi.mock("@/state/useSessionStore", () => ({
  useSessionStore: (selector: (s: { authToken: string | null }) => unknown) =>
    selector({ authToken: mockAuthToken }),
}));

function makeArgs(
  overrides?: Partial<Parameters<typeof useUnifiedChatDataLoading>[0]>,
) {
  return {
    strategyId: "strategy-1" as string | null,
    sessionRef: { current: null },
    setMessages: vi.fn((updater: Message[] | ((prev: Message[]) => Message[])) => {
      // Simulate React setState: if updater is a function, call it with []
      if (typeof updater === "function") updater([]);
    }),
    setApiError: vi.fn(),
    setSelectedModelId: vi.fn(),
    thinking: {
      applyThinkingPayload: vi.fn(),
      reset: vi.fn(),
      thinkingBudget: null,
      currentThinking: null,
      finalizeToolCalls: vi.fn(),
    } as unknown as ReturnType<typeof import("./useThinkingState").useThinkingState>,
    loadGraph: vi.fn(),
    onStrategyNotFound: vi.fn(),
    ...overrides,
  };
}

describe("useUnifiedChatDataLoading", () => {
  beforeEach(() => {
    mockGetStrategy = vi.fn();
    mockAuthToken = "valid-token";
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads messages on mount when strategyId is set", async () => {
    mockGetStrategy.mockResolvedValueOnce(mockStrategy);
    const args = makeArgs();

    renderHook(() => useUnifiedChatDataLoading(args));

    await waitFor(() => {
      expect(mockGetStrategy).toHaveBeenCalledWith("strategy-1");
      expect(args.setMessages).toHaveBeenCalled();
    });
  });

  it("clears messages when strategyId is null", () => {
    const args = makeArgs({ strategyId: null });

    renderHook(() => useUnifiedChatDataLoading(args));

    expect(args.setMessages).toHaveBeenCalledWith([]);
    expect(mockGetStrategy).not.toHaveBeenCalled();
  });

  it("calls onStrategyNotFound on 404", async () => {
    const { APIError } = await import("@/lib/api/client");
    mockGetStrategy.mockRejectedValueOnce(
      new APIError("Not found", {
        status: 404,
        statusText: "",
        url: "",
        data: undefined,
      }),
    );
    const args = makeArgs();

    renderHook(() => useUnifiedChatDataLoading(args));

    await waitFor(() => {
      expect(args.onStrategyNotFound).toHaveBeenCalled();
    });
  });

  it("surfaces API error to UI on failed load", async () => {
    const { APIError } = await import("@/lib/api/client");
    // Both attempts fail
    mockGetStrategy.mockRejectedValue(
      new APIError("Unauthorized", {
        status: 401,
        statusText: "",
        url: "",
        data: undefined,
      }),
    );
    const args = makeArgs();

    renderHook(() => useUnifiedChatDataLoading(args));

    await waitFor(() => {
      expect(args.setApiError).toHaveBeenCalledWith(
        expect.stringContaining("Could not load conversation"),
      );
    });
  });

  it("retries loading when auth token changes after a failed load", async () => {
    const { APIError } = await import("@/lib/api/client");

    // First two calls fail (initial + retry)
    mockGetStrategy
      .mockRejectedValueOnce(
        new APIError("Unauthorized", {
          status: 401,
          statusText: "",
          url: "",
          data: undefined,
        }),
      )
      .mockRejectedValueOnce(
        new APIError("Unauthorized", {
          status: 401,
          statusText: "",
          url: "",
          data: undefined,
        }),
      );

    const args = makeArgs();
    const { rerender } = renderHook(() => useUnifiedChatDataLoading(args));

    // Wait for both attempts to fail
    await waitFor(() => {
      expect(mockGetStrategy).toHaveBeenCalledTimes(2);
      expect(args.setApiError).toHaveBeenCalledWith(
        expect.stringContaining("Could not load conversation"),
      );
    });

    // Simulate auth token refresh
    mockAuthToken = "fresh-token";
    mockGetStrategy.mockResolvedValueOnce(mockStrategy);

    // Re-render to trigger the auth token change detection
    await act(async () => {
      rerender();
    });

    await waitFor(() => {
      // The hook should have retried with the new token
      expect(mockGetStrategy).toHaveBeenCalledTimes(3);
      // Error should be cleared
      expect(args.setApiError).toHaveBeenCalledWith(null);
    });
  });

  it("does NOT retry when auth token changes if the load succeeded", async () => {
    // Successful load
    mockGetStrategy.mockResolvedValueOnce(mockStrategy);
    const args = makeArgs();

    const { rerender } = renderHook(() => useUnifiedChatDataLoading(args));

    await waitFor(() => {
      expect(mockGetStrategy).toHaveBeenCalledTimes(1);
    });

    // Change auth token — should NOT trigger a retry since load succeeded
    mockAuthToken = "different-token";

    await act(async () => {
      rerender();
    });

    // Give it time to settle — should still be only 1 call
    await new Promise((r) => setTimeout(r, 50));
    expect(mockGetStrategy).toHaveBeenCalledTimes(1);
  });
});

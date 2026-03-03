import { describe, expect, it } from "vitest";
import { resolveActiveConversation } from "./resolveActiveConversation";

const item = (id: string, minutesAgo = 0) => ({
  id,
  updatedAt: new Date(Date.now() - minutesAgo * 60_000).toISOString(),
});

describe("resolveActiveConversation", () => {
  // === Core invariant: never switch when strategyId is set ===

  it("keeps current strategy when strategyId is set and list is empty", () => {
    const result = resolveActiveConversation({
      strategyId: "abc",
      hasAuth: true,
      strategyItems: [],
      hasFetched: false,
    });
    expect(result).toEqual({ type: "keep" });
  });

  it("keeps current strategy when strategyId is set but not in list", () => {
    const result = resolveActiveConversation({
      strategyId: "abc",
      hasAuth: true,
      strategyItems: [item("xyz", 1), item("def", 2)],
      hasFetched: true,
    });
    expect(result).toEqual({ type: "keep" });
  });

  it("keeps current strategy when strategyId is set and IS in list", () => {
    const result = resolveActiveConversation({
      strategyId: "abc",
      hasAuth: true,
      strategyItems: [item("abc", 1), item("def", 2)],
      hasFetched: true,
    });
    expect(result).toEqual({ type: "keep" });
  });

  it("keeps current strategy even when fetch hasn't completed", () => {
    const result = resolveActiveConversation({
      strategyId: "abc",
      hasAuth: true,
      strategyItems: [],
      hasFetched: false,
    });
    expect(result).toEqual({ type: "keep" });
  });

  // === No auth ===

  it("waits when not authenticated", () => {
    const result = resolveActiveConversation({
      strategyId: null,
      hasAuth: false,
      strategyItems: [],
      hasFetched: false,
    });
    expect(result).toEqual({ type: "wait" });
  });

  it("waits even with strategyId when not authenticated", () => {
    // No auth trumps everything — can't make API calls.
    // Actually, we still keep because the user might have a cached token.
    // Let me re-check the logic...
    const result = resolveActiveConversation({
      strategyId: "abc",
      hasAuth: false,
      strategyItems: [],
      hasFetched: false,
    });
    expect(result).toEqual({ type: "wait" });
  });

  // === No strategyId: pick or create ===

  it("waits when no strategyId and list hasn't loaded yet", () => {
    const result = resolveActiveConversation({
      strategyId: null,
      hasAuth: true,
      strategyItems: [],
      hasFetched: false,
    });
    expect(result).toEqual({ type: "wait" });
  });

  it("creates when no strategyId and list is empty after fetch", () => {
    const result = resolveActiveConversation({
      strategyId: null,
      hasAuth: true,
      strategyItems: [],
      hasFetched: true,
    });
    expect(result).toEqual({ type: "create" });
  });

  it("picks most recent when no strategyId and list has items", () => {
    const result = resolveActiveConversation({
      strategyId: null,
      hasAuth: true,
      strategyItems: [item("old", 10), item("recent", 1)],
      hasFetched: true,
    });
    expect(result).toEqual({ type: "pick", strategyId: "recent" });
  });

  it("picks most recent from list regardless of fetch order", () => {
    const result = resolveActiveConversation({
      strategyId: null,
      hasAuth: true,
      strategyItems: [item("c", 5), item("a", 1), item("b", 10)],
      hasFetched: true,
    });
    expect(result).toEqual({ type: "pick", strategyId: "a" });
  });

  // === Spam-refresh regression tests ===

  it("does NOT auto-create when strategyId is set and list is empty after fetch", () => {
    // This is the exact race condition that caused chats to "disappear":
    // hasFetched=true + items=[] + strategyId set → old code auto-created.
    const result = resolveActiveConversation({
      strategyId: "my-chat",
      hasAuth: true,
      strategyItems: [],
      hasFetched: true,
    });
    expect(result).toEqual({ type: "keep" });
    expect(result.type).not.toBe("create");
  });

  it("does NOT switch to most-recent when strategyId is set but missing from list", () => {
    // Another race: strategyId not yet in list → old code switched.
    const result = resolveActiveConversation({
      strategyId: "my-chat",
      hasAuth: true,
      strategyItems: [item("other", 1)],
      hasFetched: true,
    });
    expect(result).toEqual({ type: "keep" });
    expect(result.type).not.toBe("pick");
  });
});

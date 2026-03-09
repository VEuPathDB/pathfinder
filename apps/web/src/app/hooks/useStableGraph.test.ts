/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";
import { useStableGraph } from "./useStableGraph";
import type { Strategy } from "@pathfinder/shared";

const makeStrategy = (steps: number): Strategy => ({
  id: "s1",
  name: "Test",
  siteId: "plasmodb",
  recordType: "gene",
  steps: Array.from({ length: steps }, (_, i) => ({
    id: `step-${i}`,
    kind: "search" as const,
    displayName: `Step ${i}`,
    searchName: "GeneByTextSearch",
  })),
  rootStepId: "step-0",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
});

describe("useStableGraph", () => {
  it("returns the strategy and hasGraph=true when strategy has steps", () => {
    const strategy = makeStrategy(2);
    const { result } = renderHook(() => useStableGraph(strategy, false));
    expect(result.current.hasGraph).toBe(true);
    expect(result.current.displayStrategy).toBe(strategy);
  });

  it("returns null and hasGraph=false when no strategy and not streaming", () => {
    const { result } = renderHook(() => useStableGraph(null, false));
    expect(result.current.hasGraph).toBe(false);
    expect(result.current.displayStrategy).toBeNull();
  });

  it("returns null and hasGraph=false when strategy has empty steps and not streaming", () => {
    const strategy = makeStrategy(0);
    const { result } = renderHook(() => useStableGraph(strategy, false));
    expect(result.current.hasGraph).toBe(false);
    expect(result.current.displayStrategy).toBeNull();
  });

  it("keeps the last known strategy when streaming and strategy becomes null", () => {
    const strategy = makeStrategy(2);
    const { result, rerender } = renderHook(
      ({ s, streaming }) => useStableGraph(s, streaming),
      { initialProps: { s: strategy as Strategy | null, streaming: false } },
    );

    expect(result.current.hasGraph).toBe(true);
    expect(result.current.displayStrategy).toBe(strategy);

    // Start streaming, then strategy becomes null (graph_cleared event)
    rerender({ s: null, streaming: true });

    expect(result.current.hasGraph).toBe(true);
    expect(result.current.displayStrategy).toBe(strategy);
  });

  it("keeps the last known strategy when streaming and steps become empty", () => {
    const strategy = makeStrategy(3);
    const emptyStrategy = makeStrategy(0);
    const { result, rerender } = renderHook(
      ({ s, streaming }) => useStableGraph(s, streaming),
      { initialProps: { s: strategy as Strategy | null, streaming: false } },
    );

    rerender({ s: emptyStrategy, streaming: true });

    expect(result.current.hasGraph).toBe(true);
    expect(result.current.displayStrategy).toBe(strategy);
  });

  it("updates to new strategy when streaming and new strategy has steps", () => {
    const strategy1 = makeStrategy(2);
    const strategy2 = makeStrategy(4);
    const { result, rerender } = renderHook(
      ({ s, streaming }) => useStableGraph(s, streaming),
      { initialProps: { s: strategy1 as Strategy | null, streaming: true } },
    );

    rerender({ s: strategy2, streaming: true });

    expect(result.current.hasGraph).toBe(true);
    expect(result.current.displayStrategy).toBe(strategy2);
  });

  it("clears after streaming ends with no strategy", () => {
    const strategy = makeStrategy(2);
    const { result, rerender } = renderHook(
      ({ s, streaming }) => useStableGraph(s, streaming),
      { initialProps: { s: strategy as Strategy | null, streaming: false } },
    );

    // Start streaming, strategy cleared
    rerender({ s: null, streaming: true });
    expect(result.current.hasGraph).toBe(true); // still showing cached

    // Streaming ends, strategy still null
    rerender({ s: null, streaming: false });
    expect(result.current.hasGraph).toBe(false);
    expect(result.current.displayStrategy).toBeNull();
  });

  it("updates cached strategy when a new valid strategy arrives during streaming", () => {
    const strategy1 = makeStrategy(1);
    const strategy2 = makeStrategy(3);
    const { result, rerender } = renderHook(
      ({ s, streaming }) => useStableGraph(s, streaming),
      { initialProps: { s: strategy1 as Strategy | null, streaming: true } },
    );

    // Strategy cleared during streaming
    rerender({ s: null, streaming: true });
    expect(result.current.displayStrategy).toBe(strategy1);

    // New strategy arrives via graph_snapshot
    rerender({ s: strategy2, streaming: true });
    expect(result.current.displayStrategy).toBe(strategy2);
    expect(result.current.hasGraph).toBe(true);
  });
});

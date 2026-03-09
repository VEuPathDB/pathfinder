import { useEffect, useState } from "react";
import type { Strategy } from "@pathfinder/shared";

/**
 * Returns a stable strategy for display purposes.
 *
 * During streaming, the backend may temporarily clear the strategy
 * (via `graph_cleared` events) before rebuilding it. This hook caches
 * the last known valid strategy so the graph view doesn't flash.
 */
export function useStableGraph(
  strategy: Strategy | null,
  isStreaming: boolean,
): { displayStrategy: Strategy | null; hasGraph: boolean } {
  const [cached, setCached] = useState<Strategy | null>(null);

  const hasSteps = !!(strategy && strategy.steps.length > 0);

  // Compute the target cache value during render.
  // When strategy has steps, cache it. When streaming without steps,
  // keep the previous cache. When idle without steps, clear.
  const nextCached = hasSteps ? strategy : isStreaming ? cached : null;

  // Sync to state (same pattern as usePrevious).
  useEffect(() => {
    setCached(nextCached);
  }, [nextCached]);

  const displayStrategy = hasSteps ? strategy : cached;
  const hasGraph = !!(displayStrategy && displayStrategy.steps.length > 0);

  return { displayStrategy, hasGraph };
}

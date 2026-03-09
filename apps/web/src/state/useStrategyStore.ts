/**
 * Re-export shim — all logic now lives in state/strategy/.
 * Existing `import { useStrategyStore } from "@/state/useStrategyStore"` continues to work.
 */

export { useStrategyStore } from "./strategy/store";
export type { StrategyState } from "./strategy/types";

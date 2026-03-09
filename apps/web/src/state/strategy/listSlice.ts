/**
 * List slice — sidebar strategy list and executed strategies tracking.
 */

import type { StateCreator } from "zustand";
import type { StrategyState, ListSlice } from "./types";
import { normalizeStrategyId } from "./helpers";

export const createListSlice: StateCreator<StrategyState, [], [], ListSlice> = (
  set,
) => ({
  strategies: [],
  executedStrategies: [],

  setStrategies: (items) => set({ strategies: items }),

  addStrategyToList: (item) =>
    set((state) => {
      const existing = state.strategies.find((c) => c.id === item.id);
      if (existing) {
        return {
          strategies: state.strategies.map((c) =>
            c.id === item.id ? { ...c, ...item } : c,
          ),
        };
      }
      return { strategies: [item, ...state.strategies] };
    }),

  removeStrategyFromList: (id) =>
    set((state) => ({
      strategies: state.strategies.filter((c) => c.id !== id),
    })),

  addExecutedStrategy: (strategy) =>
    set((state) => {
      const id = normalizeStrategyId(strategy);
      const existingIndex = state.executedStrategies.findIndex((s) => s.id === id);
      const nextStrategy = {
        ...strategy,
        id,
        updatedAt: new Date().toISOString(),
      };
      if (existingIndex >= 0) {
        const updated = [...state.executedStrategies];
        updated[existingIndex] = nextStrategy;
        return { executedStrategies: updated };
      }
      return {
        executedStrategies: [nextStrategy, ...state.executedStrategies],
      };
    }),
});

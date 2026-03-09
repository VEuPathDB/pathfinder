/**
 * Meta slice — graph validation status and other cross-cutting metadata.
 */

import type { StateCreator } from "zustand";
import type { StrategyState, MetaSlice } from "./types";

export const createMetaSlice: StateCreator<StrategyState, [], [], MetaSlice> = (
  set,
) => ({
  graphValidationStatus: {},

  setGraphValidationStatus: (id, hasErrors) =>
    set((state) => ({
      graphValidationStatus: {
        ...state.graphValidationStatus,
        [id]: hasErrors,
      },
    })),
});

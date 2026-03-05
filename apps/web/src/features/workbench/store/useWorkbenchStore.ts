/**
 * Workbench state store — manages gene sets and analysis panel UI state.
 */

import { create } from "zustand";
import type { Experiment, GeneSet } from "@pathfinder/shared";

export type { GeneSet } from "@pathfinder/shared";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PanelId =
  | "enrichment"
  | "distributions"
  | "evaluate"
  | "sweep"
  | "results-table"
  | "step-analysis"
  | "ai-insights"
  | "custom-enrichment"
  | "ai-interpretation";

// ---------------------------------------------------------------------------
// Store shape
// ---------------------------------------------------------------------------

interface WorkbenchState {
  geneSets: GeneSet[];
  activeSetId: string | null;
  selectedSetIds: string[];
  expandedPanels: Set<PanelId>;
  lastExperiment: Experiment | null;
  lastExperimentSetId: string | null;

  // Actions — gene sets
  addGeneSet: (geneSet: GeneSet) => void;
  removeGeneSet: (id: string) => void;
  updateGeneSet: (id: string, patch: Partial<GeneSet>) => void;
  setActiveSet: (id: string | null) => void;
  toggleSetSelection: (id: string) => void;
  clearSelection: () => void;

  // Actions — panels
  togglePanel: (panelId: PanelId) => void;
  expandPanel: (panelId: PanelId) => void;
  collapsePanel: (panelId: PanelId) => void;

  // Actions — experiment
  setLastExperiment: (experiment: Experiment | null, setId: string | null) => void;
  clearLastExperiment: () => void;

  // Actions — global
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Initial state (extracted so `reset` can reuse it)
// ---------------------------------------------------------------------------

const initialState = {
  geneSets: [] as GeneSet[],
  activeSetId: null as string | null,
  selectedSetIds: [] as string[],
  expandedPanels: new Set<PanelId>(),
  lastExperiment: null as Experiment | null,
  lastExperimentSetId: null as string | null,
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useWorkbenchStore = create<WorkbenchState>()((set) => ({
  ...initialState,

  // -- Gene set actions -----------------------------------------------------

  addGeneSet: (geneSet) =>
    set((s) => ({
      geneSets: [...s.geneSets, geneSet],
      // Auto-activate when no set is active yet
      activeSetId: s.activeSetId ?? geneSet.id,
    })),

  removeGeneSet: (id) =>
    set((s) => {
      const geneSets = s.geneSets.filter((gs) => gs.id !== id);
      const activeSetId =
        s.activeSetId === id ? (geneSets[0]?.id ?? null) : s.activeSetId;
      const selectedSetIds = s.selectedSetIds.filter((sid) => sid !== id);
      return { geneSets, activeSetId, selectedSetIds };
    }),

  updateGeneSet: (id, patch) =>
    set((s) => ({
      geneSets: s.geneSets.map((gs) => (gs.id === id ? { ...gs, ...patch } : gs)),
    })),

  setActiveSet: (id) => set({ activeSetId: id }),

  toggleSetSelection: (id) =>
    set((s) => ({
      selectedSetIds: s.selectedSetIds.includes(id)
        ? s.selectedSetIds.filter((sid) => sid !== id)
        : [...s.selectedSetIds, id],
    })),

  clearSelection: () => set({ selectedSetIds: [] }),

  // -- Panel actions --------------------------------------------------------

  togglePanel: (panelId) =>
    set((s) => {
      const next = new Set(s.expandedPanels);
      if (next.has(panelId)) {
        next.delete(panelId);
      } else {
        next.add(panelId);
      }
      return { expandedPanels: next };
    }),

  expandPanel: (panelId) =>
    set((s) => {
      if (s.expandedPanels.has(panelId)) return s;
      const next = new Set(s.expandedPanels);
      next.add(panelId);
      return { expandedPanels: next };
    }),

  collapsePanel: (panelId) =>
    set((s) => {
      if (!s.expandedPanels.has(panelId)) return s;
      const next = new Set(s.expandedPanels);
      next.delete(panelId);
      return { expandedPanels: next };
    }),

  // -- Experiment actions ----------------------------------------------------

  setLastExperiment: (experiment, setId) =>
    set({ lastExperiment: experiment, lastExperimentSetId: setId }),

  clearLastExperiment: () => set({ lastExperiment: null, lastExperimentSetId: null }),

  // -- Global ---------------------------------------------------------------

  reset: () =>
    set({
      geneSets: [],
      activeSetId: null,
      selectedSetIds: [],
      expandedPanels: new Set<PanelId>(),
      lastExperiment: null,
      lastExperimentSetId: null,
    }),
}));

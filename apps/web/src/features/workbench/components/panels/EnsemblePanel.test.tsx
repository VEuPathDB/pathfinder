// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import type { GeneSet } from "@pathfinder/shared";

// ---------------------------------------------------------------------------
// Mock the workbench store so AnalysisPanelContainer renders children
// ---------------------------------------------------------------------------

function makeGeneSet(id: string, geneIds: string[]): GeneSet {
  return {
    id,
    name: `Set ${id}`,
    siteId: "PlasmoDB",
    geneIds,
    source: "paste",
    geneCount: geneIds.length,
    createdAt: "2026-03-09T00:00:00Z",
    stepCount: 1,
    parentSetIds: [],
  };
}

const storeState: Record<string, unknown> = {
  geneSets: [] as GeneSet[],
  selectedSetIds: [] as string[],
  expandedPanels: new Set(["ensemble"]),
  togglePanel: vi.fn(),
  toggleSetSelection: vi.fn(),
};

const mockStore = (selector: (s: Record<string, unknown>) => unknown) =>
  selector(storeState);

vi.mock("../../store", () => ({
  useWorkbenchStore: (selector: (s: Record<string, unknown>) => unknown) =>
    mockStore(selector),
}));

vi.mock("../../store/useWorkbenchStore", () => ({
  useWorkbenchStore: (selector: (s: Record<string, unknown>) => unknown) =>
    mockStore(selector),
}));

// Mock the API call
const mockRequestJson = vi.fn();
vi.mock("@/lib/api/http", () => ({
  requestJson: (...args: unknown[]) => mockRequestJson(...args),
}));

// Mock GeneChipInput's dependencies
vi.mock("@/lib/api/genes", () => ({
  resolveGeneIds: vi.fn().mockResolvedValue({ resolved: [], unresolved: [] }),
  searchGenes: vi.fn().mockResolvedValue([]),
}));

// ---------------------------------------------------------------------------
// Import after mocks
// ---------------------------------------------------------------------------

import { EnsemblePanel } from "./EnsemblePanel";

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("EnsemblePanel", () => {
  afterEach(() => {
    cleanup();
    mockRequestJson.mockReset();
  });

  beforeEach(() => {
    storeState.geneSets = [];
    storeState.selectedSetIds = [];
    storeState.expandedPanels = new Set(["ensemble"]);
  });

  it("shows disabled state when fewer than 2 gene sets exist", () => {
    storeState.geneSets = [makeGeneSet("s1", ["G1"])];
    render(<EnsemblePanel />);
    expect(screen.getByText("Ensemble Scoring")).toBeTruthy();
    // Panel header shows but content should not render (disabled)
    expect(screen.queryByText("Compute")).toBeNull();
  });

  it("renders gene set selector when 2+ gene sets exist", () => {
    storeState.geneSets = [
      makeGeneSet("s1", ["G1", "G2"]),
      makeGeneSet("s2", ["G2", "G3"]),
    ];
    storeState.selectedSetIds = ["s1", "s2"];

    render(<EnsemblePanel />);
    expect(screen.getByText("Set s1")).toBeTruthy();
    expect(screen.getByText("Set s2")).toBeTruthy();
  });

  it("disables compute button when fewer than 2 sets are selected", () => {
    storeState.geneSets = [makeGeneSet("s1", ["G1"]), makeGeneSet("s2", ["G2"])];
    storeState.selectedSetIds = ["s1"];

    render(<EnsemblePanel />);
    const button = screen.getByRole("button", { name: /compute/i });
    expect(button).toBeTruthy();
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows ranked table after computation", async () => {
    storeState.geneSets = [
      makeGeneSet("s1", ["G1", "G2"]),
      makeGeneSet("s2", ["G2", "G3"]),
    ];
    storeState.selectedSetIds = ["s1", "s2"];

    mockRequestJson.mockResolvedValueOnce([
      { geneId: "G2", frequency: 1.0, count: 2, total: 2, inPositives: false },
      { geneId: "G1", frequency: 0.5, count: 1, total: 2, inPositives: false },
      { geneId: "G3", frequency: 0.5, count: 1, total: 2, inPositives: false },
    ]);

    render(<EnsemblePanel />);
    const button = screen.getByRole("button", { name: /compute/i });
    fireEvent.click(button);

    // Wait for results to render
    const g2Row = await screen.findByText("G2");
    expect(g2Row).toBeTruthy();
    expect(screen.getByText("100.0%")).toBeTruthy();
    expect(screen.getByText("G1")).toBeTruthy();
    expect(screen.getByText("G3")).toBeTruthy();
  });

  it("sends correct request body to the API", async () => {
    storeState.geneSets = [
      makeGeneSet("s1", ["G1"]),
      makeGeneSet("s2", ["G2"]),
      makeGeneSet("s3", ["G3"]),
    ];
    storeState.selectedSetIds = ["s1", "s3"];

    mockRequestJson.mockResolvedValueOnce([]);

    render(<EnsemblePanel />);
    fireEvent.click(screen.getByRole("button", { name: /compute/i }));

    expect(mockRequestJson).toHaveBeenCalledWith("/api/v1/gene-sets/ensemble", {
      method: "POST",
      body: { geneSetIds: ["s1", "s3"], positiveControls: undefined },
    });
  });
});

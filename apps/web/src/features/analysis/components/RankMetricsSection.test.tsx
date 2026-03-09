// @vitest-environment jsdom
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import type { RankMetrics } from "@pathfinder/shared";
import { RankMetricsSection } from "./RankMetricsSection";

// Mock Recharts to avoid SVG rendering issues in jsdom
vi.mock("recharts", () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => null,
  ReferenceLine: () => null,
}));

import { vi } from "vitest";

function makeRankMetrics(overrides: Partial<RankMetrics> = {}): RankMetrics {
  return {
    precisionAtK: { "10": 0.9, "25": 0.72, "50": 0.56, "100": 0.35, "250": 0.2 },
    recallAtK: { "10": 0.3, "25": 0.5, "50": 0.7, "100": 0.85, "250": 0.95 },
    enrichmentAtK: { "10": 4.5, "25": 3.6, "50": 2.8, "100": 1.75, "250": 1.0 },
    prCurve: [
      [0.9, 0.1],
      [0.7, 0.5],
      [0.5, 0.8],
    ],
    listSizeVsRecall: [
      [50, 0.7],
      [100, 0.85],
      [250, 0.95],
    ],
    totalResults: 1000,
    ...overrides,
  };
}

describe("RankMetricsSection", () => {
  afterEach(cleanup);

  it("renders the section header", () => {
    render(<RankMetricsSection rankMetrics={makeRankMetrics()} />);
    expect(screen.getByText("Rank-Based Metrics")).toBeTruthy();
  });

  it("renders Precision@K table with K rows", () => {
    render(<RankMetricsSection rankMetrics={makeRankMetrics()} />);
    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    // header + 5 rows (K=10,25,50,100,250)
    expect(rows.length).toBe(6);
  });

  it("displays precision values as percentages", () => {
    render(<RankMetricsSection rankMetrics={makeRankMetrics()} />);
    // K=10 precision 0.9 => "90.0%"
    expect(screen.getAllByText("90.0%").length).toBeGreaterThanOrEqual(1);
  });

  it("displays enrichment values with fold suffix", () => {
    render(<RankMetricsSection rankMetrics={makeRankMetrics()} />);
    // K=10 enrichment 4.5 => "4.500x"
    expect(screen.getByText("4.500x")).toBeTruthy();
  });

  it("returns null when no K rows have precision data", () => {
    const { container } = render(
      <RankMetricsSection rankMetrics={makeRankMetrics({ precisionAtK: {} })} />,
    );
    expect(container.innerHTML).toBe("");
  });
});

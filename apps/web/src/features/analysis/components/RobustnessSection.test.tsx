// @vitest-environment jsdom
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import type {
  BootstrapResult,
  ConfidenceInterval,
  RankMetrics,
} from "@pathfinder/shared";
import { RobustnessSection } from "./RobustnessSection";

function makeCI(mean: number, lower: number, upper: number): ConfidenceInterval {
  return { lower, mean, upper, std: (upper - lower) / 4 };
}

function makeRankMetrics(): RankMetrics {
  return {
    precisionAtK: { "10": 0.8, "25": 0.6, "50": 0.5 },
    recallAtK: { "10": 0.3, "25": 0.5, "50": 0.7 },
    enrichmentAtK: { "10": 4.0, "25": 3.0, "50": 2.5 },
    prCurve: [],
    listSizeVsRecall: [],
    totalResults: 500,
  };
}

function makeBootstrap(overrides: Partial<BootstrapResult> = {}): BootstrapResult {
  return {
    nIterations: 200,
    metricCis: {
      sensitivity: makeCI(0.85, 0.78, 0.91),
      specificity: makeCI(0.9, 0.85, 0.94),
      f1_score: makeCI(0.82, 0.75, 0.88),
    },
    rankMetricCis: {
      precision_at_50: makeCI(0.5, 0.4, 0.6),
    },
    topKStability: 0.88,
    negativeSetSensitivity: [],
    ...overrides,
  };
}

describe("RobustnessSection", () => {
  afterEach(cleanup);

  it("renders the section header", () => {
    render(<RobustnessSection robustness={makeBootstrap()} />);
    expect(screen.getByText("Robustness & Uncertainty")).toBeTruthy();
  });

  it("displays stability score when rank CIs present", () => {
    render(<RobustnessSection robustness={makeBootstrap()} />);
    expect(screen.getByText(/Stable/)).toBeTruthy();
  });

  it("displays bootstrap iteration count", () => {
    render(<RobustnessSection robustness={makeBootstrap()} />);
    expect(screen.getByText(/200 bootstrap iterations/)).toBeTruthy();
  });

  it("renders CI table with metric rows", () => {
    render(<RobustnessSection robustness={makeBootstrap()} />);
    expect(screen.getByText("Sensitivity")).toBeTruthy();
    expect(screen.getByText("Specificity")).toBeTruthy();
    expect(screen.getByText("F1 Score")).toBeTruthy();
  });

  it("displays mean values as percentages", () => {
    render(<RobustnessSection robustness={makeBootstrap()} />);
    expect(screen.getByText("85.0%")).toBeTruthy();
  });

  it("renders negative set sensitivity when present", () => {
    const bootstrap = makeBootstrap({
      negativeSetSensitivity: [
        { label: "Random 500", negativeCount: 500, rankMetrics: makeRankMetrics() },
      ],
    });
    render(<RobustnessSection robustness={bootstrap} />);
    expect(screen.getByText("Negative Set Sensitivity")).toBeTruthy();
    expect(screen.getByText("Random 500")).toBeTruthy();
  });

  it("hides stability badge when no rank CIs", () => {
    const bootstrap = makeBootstrap({ rankMetricCis: {} });
    render(<RobustnessSection robustness={bootstrap} />);
    expect(screen.queryByText(/Top-50 Stability/)).toBeNull();
  });
});

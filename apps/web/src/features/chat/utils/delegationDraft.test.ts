import { describe, expect, it } from "vitest";
import type { PlanningArtifact } from "@pathfinder/shared";
import type { StepParameters } from "@/lib/strategyGraph/types";
import {
  buildDelegationExecutorMessage,
  getDelegationDraft,
} from "@/features/chat/utils/delegationDraft";

function makeArtifact(
  overrides: Partial<PlanningArtifact> & { id: string },
): PlanningArtifact {
  return {
    title: "",
    summaryMarkdown: "",
    assumptions: [],
    parameters: {},
    createdAt: "t",
    ...overrides,
  };
}

describe("delegationDraft", () => {
  it("returns null when no delegation_draft artifact", () => {
    expect(getDelegationDraft([])).toBeNull();
  });

  it("extracts goal/plan from record parameters", () => {
    const artifacts: PlanningArtifact[] = [
      makeArtifact({
        id: "delegation_draft",
        parameters: { delegationGoal: "G", delegationPlan: { a: 1 } },
      }),
    ];
    expect(getDelegationDraft(artifacts)).toEqual({ goal: "G", plan: { a: 1 } });
  });

  it("ignores non-record parameters and non-string goal", () => {
    const artifacts: PlanningArtifact[] = [
      makeArtifact({
        id: "delegation_draft",
        parameters: "nope" as unknown as StepParameters,
      }),
      makeArtifact({ id: "delegation_draft", parameters: { delegationGoal: 123 } }),
    ];
    expect(getDelegationDraft(artifacts.slice(0, 1))).toEqual({
      goal: undefined,
      plan: undefined,
    });
    expect(getDelegationDraft(artifacts.slice(1, 2))).toEqual({
      goal: undefined,
      plan: undefined,
    });
  });

  it("builds executor message with JSON fenced block", () => {
    const msg = buildDelegationExecutorMessage({ goal: "Goal", plan: { x: 1 } });
    expect(msg).toMatch(/delegate_strategy_subtasks/);
    expect(msg).toMatch(/```/);
    expect(msg).toMatch(/"x": 1/);
  });
});

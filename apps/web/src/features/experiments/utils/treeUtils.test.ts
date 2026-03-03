import { describe, it, expect } from "vitest";
import { flattenTree, flattenLeaves, planStepChildren } from "./treeUtils";
import type { PlanStepNode } from "@pathfinder/shared";

// ---------------------------------------------------------------------------
// Generic tree helpers -- use a minimal node type for isolation
// ---------------------------------------------------------------------------

interface SimpleNode {
  value: string;
  children: SimpleNode[];
}

function simpleChildren(n: SimpleNode): SimpleNode[] {
  return n.children;
}

describe("flattenTree", () => {
  it("flattens a single-node tree", () => {
    const root: SimpleNode = { value: "root", children: [] };
    const result = flattenTree(root, simpleChildren);
    expect(result).toEqual([root]);
  });

  it("returns nodes in pre-order (parent before children)", () => {
    const leaf1: SimpleNode = { value: "leaf1", children: [] };
    const leaf2: SimpleNode = { value: "leaf2", children: [] };
    const mid: SimpleNode = { value: "mid", children: [leaf1] };
    const root: SimpleNode = { value: "root", children: [mid, leaf2] };

    const result = flattenTree(root, simpleChildren);
    expect(result.map((n) => n.value)).toEqual(["root", "mid", "leaf1", "leaf2"]);
  });

  it("applies an optional transform to each node", () => {
    const leaf: SimpleNode = { value: "leaf", children: [] };
    const root: SimpleNode = { value: "root", children: [leaf] };

    const result = flattenTree(root, simpleChildren, (n) => n.value.toUpperCase());
    expect(result).toEqual(["ROOT", "LEAF"]);
  });
});

describe("flattenLeaves", () => {
  it("returns only the single node when the tree is a leaf", () => {
    const root: SimpleNode = { value: "only", children: [] };
    const result = flattenLeaves(root, simpleChildren);
    expect(result).toEqual([root]);
  });

  it("skips interior nodes and collects leaves left-to-right", () => {
    const a: SimpleNode = { value: "a", children: [] };
    const b: SimpleNode = { value: "b", children: [] };
    const c: SimpleNode = { value: "c", children: [] };
    const mid: SimpleNode = { value: "mid", children: [a, b] };
    const root: SimpleNode = { value: "root", children: [mid, c] };

    const result = flattenLeaves(root, simpleChildren);
    expect(result.map((n) => n.value)).toEqual(["a", "b", "c"]);
  });

  it("applies an optional transform to each leaf", () => {
    const a: SimpleNode = { value: "a", children: [] };
    const b: SimpleNode = { value: "b", children: [] };
    const root: SimpleNode = { value: "root", children: [a, b] };

    const result = flattenLeaves(root, simpleChildren, (n) => n.value);
    expect(result).toEqual(["a", "b"]);
  });
});

// ---------------------------------------------------------------------------
// planStepChildren -- PlanStepNode-specific accessor
// ---------------------------------------------------------------------------

function makePlanNode(
  name: string,
  primary?: PlanStepNode,
  secondary?: PlanStepNode,
): PlanStepNode {
  return {
    searchName: name,
    primaryInput: primary,
    secondaryInput: secondary,
  };
}

describe("planStepChildren", () => {
  it("returns empty array for a leaf node", () => {
    const leaf = makePlanNode("search1");
    expect(planStepChildren(leaf)).toEqual([]);
  });

  it("returns [primary] for a transform node", () => {
    const child = makePlanNode("child");
    const transform = makePlanNode("transform", child);
    expect(planStepChildren(transform)).toEqual([child]);
  });

  it("returns [primary, secondary] for a combine node", () => {
    const left = makePlanNode("left");
    const right = makePlanNode("right");
    const combine = makePlanNode("combine", left, right);
    expect(planStepChildren(combine)).toEqual([left, right]);
  });
});

// ---------------------------------------------------------------------------
// Integration: flattenLeaves + planStepChildren (replaces flattenLeafSteps)
// ---------------------------------------------------------------------------

describe("flattenLeaves + planStepChildren (PlanStepNode integration)", () => {
  it("collects only leaf search steps from a binary plan tree", () => {
    const s1 = makePlanNode("GenesByTaxon");
    const s2 = makePlanNode("GenesByGOTerm");
    const s3 = makePlanNode("GenesByLocation");
    const combine1 = makePlanNode("intersect", s1, s2);
    const root = makePlanNode("union", combine1, s3);

    const leaves = flattenLeaves(root, planStepChildren);
    expect(leaves.map((n) => n.searchName)).toEqual([
      "GenesByTaxon",
      "GenesByGOTerm",
      "GenesByLocation",
    ]);
  });
});

import { describe, it, expect } from "vitest";
import {
  setIntersect,
  setUnion,
  setDifference,
  computeVennRegions,
} from "./setOperations";

describe("set operations", () => {
  const a = ["g1", "g2", "g3", "g4"];
  const b = ["g3", "g4", "g5", "g6"];

  it("intersect returns common elements", () => {
    expect(setIntersect(a, b)).toEqual(["g3", "g4"]);
  });

  it("union returns all unique elements in order", () => {
    expect(setUnion(a, b)).toEqual(["g1", "g2", "g3", "g4", "g5", "g6"]);
  });

  it("difference returns a - b", () => {
    expect(setDifference(a, b)).toEqual(["g1", "g2"]);
  });

  it("difference is order-dependent", () => {
    expect(setDifference(b, a)).toEqual(["g5", "g6"]);
  });

  it("handles empty arrays", () => {
    expect(setIntersect([], b)).toEqual([]);
    expect(setUnion([], b)).toEqual(b);
    expect(setDifference(a, [])).toEqual(a);
  });
});

describe("computeVennRegions (2 sets)", () => {
  const a = ["g1", "g2", "g3"];
  const b = ["g2", "g3", "g4", "g5"];

  it("computes onlyA, shared, onlyB", () => {
    const regions = computeVennRegions(a, b);
    expect(regions.onlyA).toEqual(["g1"]);
    expect(regions.shared).toEqual(["g2", "g3"]);
    expect(regions.onlyB).toEqual(["g4", "g5"]);
  });
});

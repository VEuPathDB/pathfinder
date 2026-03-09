import { describe, expect, it } from "vitest";
import { isFallbackDisplayName, normalizeName } from "./displayName";
import type { DisplayNameStep } from "./displayName";

describe("normalizeName", () => {
  it("trims and lowercases a string", () => {
    expect(normalizeName("  Hello World  ")).toBe("hello world");
  });

  it("returns empty string for null", () => {
    expect(normalizeName(null)).toBe("");
  });

  it("returns empty string for undefined", () => {
    expect(normalizeName(undefined)).toBe("");
  });

  it("returns empty string for empty string", () => {
    expect(normalizeName("")).toBe("");
  });

  it("handles string with only whitespace", () => {
    expect(normalizeName("   ")).toBe("");
  });
});

describe("isFallbackDisplayName", () => {
  const baseStep: DisplayNameStep = {
    searchName: "GenesByTaxon",
  };

  // ── Returns true for clearly fallback names ───────────────

  it("returns true for null name", () => {
    expect(isFallbackDisplayName(null, baseStep)).toBe(true);
  });

  it("returns true for undefined name", () => {
    expect(isFallbackDisplayName(undefined, baseStep)).toBe(true);
  });

  it("returns true for empty string name", () => {
    expect(isFallbackDisplayName("", baseStep)).toBe(true);
  });

  it("returns true for an http:// URL", () => {
    expect(isFallbackDisplayName("http://example.com/search", baseStep)).toBe(true);
  });

  it("returns true for an https:// URL", () => {
    expect(isFallbackDisplayName("https://example.com/search", baseStep)).toBe(true);
  });

  // ── Returns true when name matches searchName ─────────────

  it("returns true when name matches searchName (case insensitive)", () => {
    expect(isFallbackDisplayName("genesbytaxon", baseStep)).toBe(true);
  });

  it("returns true when name matches searchName with whitespace", () => {
    expect(isFallbackDisplayName("  GenesByTaxon  ", baseStep)).toBe(true);
  });

  // ── Returns true when name matches inferred step kind ─────

  it("returns true when name matches inferred kind 'search'", () => {
    const step: DisplayNameStep = { searchName: "MySearch" };
    // No inputs or operator -> kind = "search"
    expect(isFallbackDisplayName("search", step)).toBe(true);
  });

  it("returns true when name matches explicit kind", () => {
    const step: DisplayNameStep = { kind: "transform", searchName: "Q" };
    expect(isFallbackDisplayName("transform", step)).toBe(true);
  });

  it("returns true when name matches 'combine' for combine step", () => {
    const step: DisplayNameStep = {
      primaryInputStepId: "a",
      secondaryInputStepId: "b",
    };
    expect(isFallbackDisplayName("combine", step)).toBe(true);
  });

  // ── Returns true when name matches operator ───────────────

  it("returns true when name matches operator", () => {
    const step: DisplayNameStep = {
      operator: "INTERSECT",
      primaryInputStepId: "a",
      secondaryInputStepId: "b",
    };
    expect(isFallbackDisplayName("intersect", step)).toBe(true);
  });

  it("returns true when name matches 'operator combine' pattern", () => {
    const step: DisplayNameStep = {
      operator: "UNION",
      primaryInputStepId: "a",
      secondaryInputStepId: "b",
    };
    expect(isFallbackDisplayName("union combine", step)).toBe(true);
  });

  // ── Returns false for meaningful custom names ─────────────

  it("returns false for a custom display name", () => {
    expect(isFallbackDisplayName("My Custom Search Results", baseStep)).toBe(false);
  });

  it("returns false for a name that doesn't match any fallback candidate", () => {
    const step: DisplayNameStep = {
      searchName: "GenesByLocation",
      operator: "INTERSECT",
      primaryInputStepId: "a",
      secondaryInputStepId: "b",
    };
    expect(isFallbackDisplayName("Genes on Chromosome 3", step)).toBe(false);
  });

  it("returns false for a name that partially matches but is not exact", () => {
    expect(isFallbackDisplayName("GenesByTaxon results", baseStep)).toBe(false);
  });

  // ── Operator-only step (kind inferred as combine) ─────────

  it("infers combine kind for step with operator but no inputs", () => {
    const step: DisplayNameStep = { operator: "MINUS" };
    expect(isFallbackDisplayName("combine", step)).toBe(true);
    expect(isFallbackDisplayName("minus", step)).toBe(true);
    expect(isFallbackDisplayName("minus combine", step)).toBe(true);
  });

  // ── Transform step ────────────────────────────────────────

  it("infers transform kind for step with only primaryInputStepId", () => {
    const step: DisplayNameStep = {
      primaryInputStepId: "a",
      searchName: "TransformByWeight",
    };
    expect(isFallbackDisplayName("transform", step)).toBe(true);
  });
});

import { describe, expect, it } from "vitest";
import { parseToolArguments } from "./parseToolArguments";

describe("parseToolArguments", () => {
  // ─── Falsy / nullish inputs ────────────────────────────────────────

  it("returns empty object for null", () => {
    expect(parseToolArguments(null)).toEqual({});
  });

  it("returns empty object for undefined", () => {
    expect(parseToolArguments(undefined)).toEqual({});
  });

  it("returns empty object for empty string", () => {
    expect(parseToolArguments("")).toEqual({});
  });

  it("returns empty object for 0", () => {
    expect(parseToolArguments(0)).toEqual({});
  });

  it("returns empty object for false", () => {
    expect(parseToolArguments(false)).toEqual({});
  });

  // ─── Record inputs (already objects) ───────────────────────────────

  it("returns the record directly when given a plain object", () => {
    const obj = { key: "value", nested: { a: 1 } };
    const result = parseToolArguments(obj);
    expect(result).toBe(obj);
  });

  it("returns an empty object record as-is", () => {
    const obj = {};
    const result = parseToolArguments(obj);
    expect(result).toBe(obj);
  });

  it("returns object with various value types", () => {
    const obj = { str: "hello", num: 42, bool: true, arr: [1, 2, 3] };
    const result = parseToolArguments(obj);
    expect(result).toBe(obj);
  });

  // ─── Array inputs (not a record) ───────────────────────────────────

  it("returns empty object for an array", () => {
    expect(parseToolArguments([1, 2, 3])).toEqual({});
  });

  it("returns empty object for an empty array", () => {
    expect(parseToolArguments([])).toEqual({});
  });

  // ─── String inputs (JSON parsing) ─────────────────────────────────

  it("parses a valid JSON object string", () => {
    const result = parseToolArguments('{"key": "value", "num": 42}');
    expect(result).toEqual({ key: "value", num: 42 });
  });

  it("parses a JSON string with nested objects", () => {
    const result = parseToolArguments('{"outer": {"inner": true}, "list": [1,2]}');
    expect(result).toEqual({ outer: { inner: true }, list: [1, 2] });
  });

  it("returns empty object for a JSON string that parses to an array", () => {
    expect(parseToolArguments("[1, 2, 3]")).toEqual({});
  });

  it("returns empty object for a JSON string that parses to a primitive string", () => {
    expect(parseToolArguments('"just a string"')).toEqual({});
  });

  it("returns empty object for a JSON string that parses to a number", () => {
    expect(parseToolArguments("42")).toEqual({});
  });

  it("returns empty object for a JSON string that parses to null", () => {
    expect(parseToolArguments("null")).toEqual({});
  });

  it("returns empty object for a JSON string that parses to true", () => {
    expect(parseToolArguments("true")).toEqual({});
  });

  it("returns empty object for invalid JSON string", () => {
    expect(parseToolArguments("{invalid json}")).toEqual({});
  });

  it("returns empty object for a plain text string", () => {
    expect(parseToolArguments("hello world")).toEqual({});
  });

  it("returns empty object for a partial JSON string", () => {
    expect(parseToolArguments('{"key": ')).toEqual({});
  });

  // ─── Non-string, non-record, non-falsy inputs ────────────────────

  it("returns empty object for a number", () => {
    expect(parseToolArguments(123)).toEqual({});
  });

  it("returns empty object for true", () => {
    expect(parseToolArguments(true)).toEqual({});
  });

  it("returns empty object for a symbol", () => {
    expect(parseToolArguments(Symbol("test"))).toEqual({});
  });

  it("returns empty object for a function", () => {
    expect(parseToolArguments(() => {})).toEqual({});
  });

  // ─── Edge cases ───────────────────────────────────────────────────

  it("parses an empty JSON object string", () => {
    expect(parseToolArguments("{}")).toEqual({});
  });

  it("handles JSON with special characters in values", () => {
    const result = parseToolArguments('{"msg": "line1\\nline2", "tab": "a\\tb"}');
    expect(result).toEqual({ msg: "line1\nline2", tab: "a\tb" });
  });
});

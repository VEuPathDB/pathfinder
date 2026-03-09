/** Return elements present in both a and b, preserving a's order. */
export function setIntersect(a: string[], b: string[]): string[] {
  const bSet = new Set(b);
  return a.filter((id) => bSet.has(id));
}

/** Return all unique elements from a then b, preserving order. */
export function setUnion(a: string[], b: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const id of a) {
    if (!seen.has(id)) {
      seen.add(id);
      result.push(id);
    }
  }
  for (const id of b) {
    if (!seen.has(id)) {
      seen.add(id);
      result.push(id);
    }
  }
  return result;
}

/** Return elements in a that are not in b, preserving a's order. */
export function setDifference(a: string[], b: string[]): string[] {
  const bSet = new Set(b);
  return a.filter((id) => !bSet.has(id));
}

/** Compute the three Venn regions for two sets. */
export function computeVennRegions(a: string[], b: string[]) {
  const bSet = new Set(b);
  const aSet = new Set(a);
  return {
    onlyA: a.filter((id) => !bSet.has(id)),
    shared: a.filter((id) => bSet.has(id)),
    onlyB: b.filter((id) => !aSet.has(id)),
  };
}

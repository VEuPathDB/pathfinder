import type { PlanStepNode } from "@pathfinder/shared";

// ---------------------------------------------------------------------------
// Generic tree flattening utilities
// ---------------------------------------------------------------------------

/**
 * Flatten a tree into an array by recursively visiting every node.
 *
 * @param root      - The root node.
 * @param getChildren - Accessor that returns the direct children of a node.
 * @param transform - Optional mapping applied to each visited node.  When
 *                    omitted the node itself is returned.
 * @returns All nodes in pre-order (parent before children).
 */
export function flattenTree<TNode, TResult = TNode>(
  root: TNode,
  getChildren: (node: TNode) => TNode[],
  transform?: (node: TNode) => TResult,
): TResult[] {
  const out: TResult[] = [];
  function walk(node: TNode) {
    out.push(transform ? transform(node) : (node as unknown as TResult));
    for (const child of getChildren(node)) walk(child);
  }
  walk(root);
  return out;
}

/**
 * Flatten a tree but only collect *leaf* nodes (nodes with no children).
 *
 * @param root        - The root node.
 * @param getChildren - Accessor that returns the direct children of a node.
 * @param transform   - Optional mapping applied to each leaf node.
 * @returns Leaf nodes in left-to-right traversal order.
 */
export function flattenLeaves<TNode, TResult = TNode>(
  root: TNode,
  getChildren: (node: TNode) => TNode[],
  transform?: (node: TNode) => TResult,
): TResult[] {
  const out: TResult[] = [];
  function walk(node: TNode) {
    const children = getChildren(node);
    if (children.length === 0) {
      out.push(transform ? transform(node) : (node as unknown as TResult));
    } else {
      for (const child of children) walk(child);
    }
  }
  walk(root);
  return out;
}

// ---------------------------------------------------------------------------
// PlanStepNode-specific child accessor
// ---------------------------------------------------------------------------

/**
 * Return the direct children of a {@link PlanStepNode} as an array.
 *
 * The VEuPathDB plan tree uses `primaryInput` / `secondaryInput` rather than
 * a `children` array, so this accessor bridges the gap to the generic
 * utilities above.
 */
export function planStepChildren(node: PlanStepNode): PlanStepNode[] {
  const children: PlanStepNode[] = [];
  if (node.primaryInput) children.push(node.primaryInput);
  if (node.secondaryInput) children.push(node.secondaryInput);
  return children;
}

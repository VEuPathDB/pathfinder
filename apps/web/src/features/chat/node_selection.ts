import { isRecord } from "@/lib/utils/isRecord";
import { parseJsonRecord } from "@/features/chat/utils/parseJson";
import type {
  NodeSelection,
  NodeSelectionNode,
  NodeSelectionEdge,
} from "@/lib/types/nodeSelection";
import type { StepParameters } from "@/lib/strategyGraph/types";
export type { NodeSelection, NodeSelectionNode, NodeSelectionEdge };

const NODE_PREFIX = "__NODE__";

/** Raw node data as received from the backend before normalization. */
type RawNodeData = {
  id?: string;
  kind?: string;
  displayName?: string;
  searchName?: string;
  operator?: string;
  parameters?: unknown;
  recordType?: string;
  resultCount?: unknown;
  wdkStepId?: unknown;
  selected?: boolean;
};

/** Raw edge data as received from the backend before normalization. */
type RawEdgeData = {
  sourceId?: string;
  targetId?: string;
  kind?: string;
};

const asStringArray = (value: unknown): string[] =>
  Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];

export function normalizeNodeSelection(data: Record<string, unknown>): NodeSelection {
  const nodeIds = asStringArray(data.nodeIds);
  const selectedNodeIds = asStringArray(data.selectedNodeIds);
  const contextNodeIds = asStringArray(data.contextNodeIds);
  const rawNodes: RawNodeData[] = Array.isArray(data.nodes)
    ? (data.nodes as RawNodeData[])
    : [];
  const rawEdges: RawEdgeData[] = Array.isArray(data.edges)
    ? (data.edges as RawEdgeData[])
    : [];

  const fallbackNodeIds =
    nodeIds.length > 0 ? nodeIds : typeof data.id === "string" ? [data.id] : [];
  const normalizedSelected =
    selectedNodeIds.length > 0 ? selectedNodeIds : fallbackNodeIds;

  const baseNodes: NodeSelectionNode[] =
    rawNodes.length > 0
      ? rawNodes.map((n) => ({
          id: String(n.id ?? ""),
          kind: typeof n.kind === "string" ? n.kind : undefined,
          displayName: typeof n.displayName === "string" ? n.displayName : undefined,
          searchName: typeof n.searchName === "string" ? n.searchName : undefined,
          operator: typeof n.operator === "string" ? n.operator : undefined,
          parameters: isRecord(n.parameters)
            ? (n.parameters as StepParameters)
            : undefined,
          recordType: typeof n.recordType === "string" ? n.recordType : undefined,
          resultCount: typeof n.resultCount === "number" ? n.resultCount : undefined,
          wdkStepId: typeof n.wdkStepId === "number" ? n.wdkStepId : undefined,
        }))
      : fallbackNodeIds.map((id) => ({ id, displayName: id }));

  const nodes: NodeSelectionNode[] = baseNodes.map((node) => ({
    ...node,
    selected:
      typeof node.selected === "boolean"
        ? node.selected
        : node.id
          ? normalizedSelected.includes(node.id)
          : false,
  }));

  const edges: NodeSelectionEdge[] = rawEdges
    .filter(
      (e): e is Required<RawEdgeData> =>
        typeof e.sourceId === "string" &&
        typeof e.targetId === "string" &&
        typeof e.kind === "string",
    )
    .map((e) => ({
      sourceId: e.sourceId,
      targetId: e.targetId,
      kind: e.kind,
    }));

  return {
    graphId: typeof data.graphId === "string" ? data.graphId : undefined,
    nodeIds: fallbackNodeIds,
    selectedNodeIds: normalizedSelected,
    contextNodeIds,
    nodes,
    edges,
  };
}

export function decodeNodeSelection(content: string): {
  selection: NodeSelection | null;
  message: string;
} {
  if (!content.startsWith(NODE_PREFIX)) {
    return { selection: null, message: content };
  }
  const raw = content.slice(NODE_PREFIX.length);
  const newlineIndex = raw.indexOf("\n");
  const jsonPart = newlineIndex === -1 ? raw.trim() : raw.slice(0, newlineIndex).trim();
  const textPart = newlineIndex === -1 ? "" : raw.slice(newlineIndex + 1).trim();

  if (!jsonPart) {
    return { selection: null, message: textPart };
  }
  const data = parseJsonRecord(jsonPart);
  if (!data) return { selection: null, message: content };
  return {
    selection: normalizeNodeSelection(data),
    message: textPart,
  };
}

export function encodeNodeSelection(
  selection: NodeSelection | null | undefined,
  message: string,
): string {
  if (!selection) return message;
  const payload = JSON.stringify(selection);
  return message.trim().length > 0
    ? `${NODE_PREFIX}${payload}\n${message}`
    : `${NODE_PREFIX}${payload}`;
}

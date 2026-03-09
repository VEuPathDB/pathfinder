import type { NodeSelection } from "@/lib/types/nodeSelection";
import { NodeCard } from "./NodeCard";

export function DraftSelectionBar(props: {
  selection: NodeSelection;
  onRemove: () => void;
}) {
  const { selection, onRemove } = props;

  return (
    <div className="mb-3 flex items-start justify-between gap-3 rounded-lg border border-border bg-muted px-3 py-2">
      <div className="flex w-full gap-2 overflow-x-auto pb-1">
        {selection.nodes.map((node, idx) => (
          <div key={`draft-node-${idx}`} className="shrink-0 min-w-[220px]">
            <NodeCard node={node} />
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={onRemove}
        className="text-xs font-semibold uppercase tracking-wide text-muted-foreground transition-colors duration-150 hover:text-foreground"
      >
        Remove
      </button>
    </div>
  );
}

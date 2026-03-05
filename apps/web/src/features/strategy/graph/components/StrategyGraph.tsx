"use client";

/**
 * Full editable strategy graph with drag, edge editing, combine/ortholog
 * modals, step editing, save/undo, and multi-select.
 *
 * A simpler read-only variant exists at
 * `features/experiments/components/ResultsDashboard/shared/StrategyGraph.tsx`
 * for displaying an experiment's final strategy. The two share ReactFlow and
 * the `StepNode` component but differ significantly in interaction model and
 * state management, so they are kept separate.
 */
import { useCallback, useState } from "react";
import { CombineOperator, type Strategy } from "@pathfinder/shared";
import "reactflow/dist/style.css";
import { StepEditor } from "@/features/strategy/editor/StepEditor";
import { X } from "lucide-react";
import { EmptyGraphState } from "@/features/strategy/graph/components/EmptyGraphState";
import { CombineStepModal } from "@/features/strategy/graph/components/CombineStepModal";
import { EdgeContextMenu } from "@/features/strategy/graph/components/EdgeContextMenu";
import { StrategyGraphLayout } from "@/features/strategy/graph/components/StrategyGraphLayout";
import { OrthologTransformModal } from "@/features/strategy/graph/components/OrthologTransformModal";
import {
  useStrategyGraph,
  COMBINE_OPERATORS,
} from "@/features/strategy/graph/hooks/useStrategyGraph";
import { StrategyGraphProvider } from "@/features/strategy/graph/StrategyGraphContext";

interface StrategyGraphProps {
  strategy: Strategy | null;
  siteId: string;
  onReset?: () => void;
  onToast?: (toast: {
    type: "success" | "error" | "warning" | "info";
    message: string;
  }) => void;
  variant?: "full" | "compact";
  onSwitchToChat?: () => void;
}

export function StrategyGraph(props: StrategyGraphProps) {
  const { strategy, siteId, onToast, variant = "full", onSwitchToChat } = props;

  const g = useStrategyGraph({ strategy, siteId, onToast, variant });

  const HINTS_KEY = "pathfinder:graph-hints-dismissed";
  const [hintsDismissed, setHintsDismissed] = useState(() =>
    typeof window !== "undefined" ? !!localStorage.getItem(HINTS_KEY) : true,
  );
  const showHints =
    variant !== "compact" && !!strategy && strategy.steps.length > 0 && !hintsDismissed;

  const dismissHints = useCallback(() => {
    setHintsDismissed(true);
    localStorage.setItem(HINTS_KEY, "1");
  }, []);

  if (!strategy || strategy.steps.length === 0) {
    return <EmptyGraphState isCompact={g.isCompact} onSwitchToChat={onSwitchToChat} />;
  }

  return (
    <StrategyGraphProvider value={{ ...g, strategy, siteId, onToast }}>
      <div className="relative flex h-full w-full flex-col">
        {showHints && (
          <div className="absolute left-3 top-3 z-10 max-w-xs rounded-md border border-border bg-card p-3 text-sm shadow-md animate-fade-in">
            <div className="flex items-start justify-between gap-2">
              <p className="font-medium text-foreground">Quick tips</p>
              <button
                type="button"
                onClick={dismissHints}
                aria-label="Dismiss tips"
                className="rounded p-0.5 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <ul className="mt-1.5 space-y-1 text-xs text-muted-foreground">
              <li>Click a step node to edit its parameters</li>
              <li>Click an edge to change the combine operator</li>
              <li>Use the toolbar to switch between select and pan modes</li>
            </ul>
          </div>
        )}
        <StrategyGraphLayout />
        {!g.isCompact && g.edgeMenu && (
          <EdgeContextMenu
            edge={g.edgeMenu.edge}
            x={g.edgeMenu.x}
            y={g.edgeMenu.y}
            steps={g.editableSteps}
            onDeleteEdge={(edge) => {
              g.handleDeleteEdge(edge);
              g.setEdgeMenu(null);
            }}
            onChangeOperator={(stepId, operator) => {
              g.updateStep(stepId, { operator });
              g.setEdgeMenu(null);
            }}
            onClose={() => g.setEdgeMenu(null)}
          />
        )}
        {!g.isCompact && (
          <CombineStepModal
            pendingCombine={g.pendingCombine}
            operators={COMBINE_OPERATORS}
            onChoose={(operator) =>
              void g.handleCombineCreate(operator as CombineOperator)
            }
            onCancel={g.handleCombineCancel}
          />
        )}
        {!g.isCompact && g.orthologModalOpen && g.selectedNodeIds.length === 1 && (
          <OrthologTransformModal
            open={g.orthologModalOpen}
            siteId={siteId}
            recordType={(strategy?.recordType || "gene") as string}
            onCancel={() => g.setOrthologModalOpen(false)}
            onChoose={g.handleOrthologChoose}
          />
        )}
        {!g.isCompact && g.selectedStep && (
          <StepEditor
            step={g.selectedStep}
            siteId={siteId}
            recordType={strategy?.recordType || null}
            onClose={() => g.setSelectedStep(null)}
            onUpdate={(updates) => {
              g.updateStep(g.selectedStep!.id, updates);
            }}
          />
        )}
      </div>
    </StrategyGraphProvider>
  );
}

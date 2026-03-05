"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { GitBranch } from "lucide-react";
import type { PlanStepNode } from "@pathfinder/shared";
import { StepAnalysisPanel, StepContributionPanel } from "@/features/analysis";
import { getStrategy, type EntityRef } from "@/features/analysis/api/stepResults";
import type { StrategyNode } from "@/features/workbench/api";
import { AnalysisPanelContainer } from "../AnalysisPanelContainer";
import { useWorkbenchStore } from "../../store";

/**
 * Convert a WDK strategy step tree (recursive `stepTree` from `/strategy`
 * endpoint) into a PlanStepNode tree that StepContributionPanel expects.
 */
function wdkTreeToPlanNode(
  node: StrategyNode,
  steps: Record<
    string,
    {
      stepId: number;
      searchName: string;
      customName?: string;
      searchConfig?: { parameters: Record<string, string> };
    }
  >,
): PlanStepNode {
  const stepInfo = steps[String(node.stepId)] ?? {
    stepId: node.stepId,
    searchName: "",
  };
  const searchName = stepInfo.searchName ?? "";
  const customName = stepInfo.customName;

  const result: PlanStepNode = {
    id: String(node.stepId),
    searchName,
    displayName: customName,
    parameters: stepInfo.searchConfig?.parameters ?? {},
  };

  if (node.primaryInput) {
    result.primaryInput = wdkTreeToPlanNode(node.primaryInput, steps);
    if (node.secondaryInput) {
      result.secondaryInput = wdkTreeToPlanNode(node.secondaryInput, steps);
    }
  }

  return result;
}

/**
 * Fetch the strategy tree for a gene set. Returns null when unavailable.
 * The loading flag is managed via a ref + state callback to satisfy ESLint's
 * `set-state-in-effect` rule (no synchronous setState in useEffect body).
 */
function useGeneSetStepTree(geneSetId: string | null) {
  const [stepTree, setStepTree] = useState<PlanStepNode | null>(null);
  const [loading, setLoading] = useState(false);
  const activeIdRef = useRef(geneSetId);
  activeIdRef.current = geneSetId;

  const fetchTree = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const ref: EntityRef = { type: "gene-set", id };
      const strategy = await getStrategy(ref);
      if (activeIdRef.current !== id) return;
      if (strategy.stepTree) {
        setStepTree(wdkTreeToPlanNode(strategy.stepTree, strategy.steps));
      } else {
        setStepTree(null);
      }
    } catch {
      if (activeIdRef.current === id) setStepTree(null);
    } finally {
      if (activeIdRef.current === id) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!geneSetId) return;
    void fetchTree(geneSetId);
  }, [geneSetId, fetchTree]);

  // When geneSetId changes to null, treat tree as null.
  const effectiveTree = geneSetId ? stepTree : null;

  return { stepTree: effectiveTree, loading };
}

export function WorkbenchStepAnalysisPanel() {
  const geneSets = useWorkbenchStore((s) => s.geneSets);
  const activeSetId = useWorkbenchStore((s) => s.activeSetId);
  const activeSet = geneSets.find((gs) => gs.id === activeSetId);

  // Multi-step detection: the gene set was created from a strategy with > 1 step.
  const isMultiStep =
    activeSet?.source === "strategy" &&
    !!activeSet.wdkStepId &&
    (activeSet.stepCount ?? 1) > 1;

  const isDisabled = !activeSet?.wdkStepId || !isMultiStep;

  const fetchTargetId = isMultiStep ? (activeSet?.id ?? null) : null;
  const { stepTree, loading: treeLoading } = useGeneSetStepTree(fetchTargetId);

  return (
    <AnalysisPanelContainer
      panelId="step-analysis"
      title="Step Analysis"
      subtitle="Analyze individual search step contributions"
      icon={<GitBranch className="h-4 w-4" />}
      disabled={isDisabled}
      disabledReason="Requires a multi-step strategy-backed gene set"
    >
      {activeSet && !isDisabled && (
        <div className="space-y-6">
          <StepAnalysisPanel entityRef={{ type: "gene-set", id: activeSet.id }} />
          {treeLoading ? (
            <p className="text-xs text-muted-foreground">Loading strategy tree…</p>
          ) : (
            <StepContributionPanel geneSetId={activeSet.id} stepTree={stepTree} />
          )}
        </div>
      )}
    </AnalysisPanelContainer>
  );
}

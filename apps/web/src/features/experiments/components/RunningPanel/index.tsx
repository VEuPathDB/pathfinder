import { useEffect, useRef, useState } from "react";
import { BarChart3, Check, Circle, FlaskConical, Loader2, X } from "lucide-react";
import { Card, CardContent } from "@/lib/components/ui/Card";
import { Button } from "@/lib/components/ui/Button";
import { Badge } from "@/lib/components/ui/Badge";
import { Progress } from "@/lib/components/ui/Progress";
import { useExperimentRunStore } from "../../store";
import type { PlanStepNode } from "@pathfinder/shared";
import { PHASE_LABELS, STEP_ANALYSIS_PHASE_LABELS } from "./constants";
import { MiniTreeView } from "./MiniTreeView";
import { StepAnalysisDetailPanel } from "./StepAnalysisDetailPanel";
import { OptimizationChart } from "./OptimizationChart";

/* ── Phase stepper (shared between step-analysis and standard modes) ── */

function PhaseStepper<T extends string>({
  phases,
  activePhase,
  labels,
}: {
  phases: readonly T[];
  activePhase: T | string;
  labels: Record<string, string>;
}) {
  const activeIdx = phases.indexOf(activePhase as T);

  return (
    <div className="flex items-start gap-0">
      {phases.map((phase, i) => {
        const idx = phases.indexOf(phase);
        const isComplete = activeIdx > idx;
        const isActive = activeIdx === idx;
        const isPending = activeIdx < idx;
        return (
          <div key={phase} className="flex flex-1 flex-col items-center">
            <div className="flex w-full items-center">
              {i > 0 && (
                <div
                  className={`h-0.5 flex-1 transition-colors ${
                    isComplete || isActive ? "bg-primary" : "bg-border"
                  }`}
                />
              )}
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
                  isComplete
                    ? "border-primary bg-primary text-primary-foreground"
                    : isActive
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-muted text-muted-foreground"
                }`}
              >
                {isComplete ? (
                  <Check className="h-3.5 w-3.5" />
                ) : isActive ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Circle className="h-2.5 w-2.5" />
                )}
              </div>
              {i < phases.length - 1 && (
                <div
                  className={`h-0.5 flex-1 transition-colors ${
                    isComplete ? "bg-primary" : "bg-border"
                  }`}
                />
              )}
            </div>
            <span
              className={`mt-1.5 text-center text-[10px] leading-tight ${
                isActive
                  ? "font-semibold text-primary"
                  : isPending
                    ? "text-muted-foreground/60"
                    : "font-medium text-foreground"
              }`}
            >
              {labels[phase] ?? phase}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ── Elapsed timer ──────────────────────────────────────────────────── */

function ElapsedTimer() {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    startRef.current = Date.now();
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - (startRef.current ?? Date.now())) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <span className="tabular-nums text-xs text-muted-foreground">
      Running for {minutes > 0 ? `${minutes}m ` : ""}
      {seconds}s
    </span>
  );
}

/* ── Standard evaluation phases ─────────────────────────────────────── */

const STANDARD_PHASES = [
  "started",
  "evaluating",
  "cross_validating",
  "enriching",
  "completed",
] as const;

const STANDARD_PHASE_LABELS: Record<string, string> = {
  started: "Preparing",
  evaluating: "Executing Search",
  cross_validating: "Cross-Validation",
  enriching: "Enrichment",
  completed: "Finalizing",
};

/* ── RunningPanel ───────────────────────────────────────────────────── */

export function RunningPanel() {
  const {
    progress,
    trialHistory,
    hasOptimization,
    cancelExperiment,
    runningConfig,
    stepAnalysisItems,
  } = useExperimentRunStore();

  const tp = progress?.trialProgress;

  const totalTrials = tp?.totalTrials ?? 0;
  const currentTrial = tp?.currentTrial ?? 0;
  const isStepAnalysis =
    runningConfig?.enableStepAnalysis === true || progress?.phase === "step_analysis";
  const isOptimizing = progress?.phase === "optimizing" && totalTrials > 0;
  const bestScore = tp?.bestTrial?.score;

  const saProgress = progress?.stepAnalysisProgress;

  const SA_PHASES = [
    "step_evaluation",
    "operator_comparison",
    "contribution",
    "sensitivity",
  ] as const;

  // Step Analysis layout: full-width card with phase stepper + detail panel
  if (isStepAnalysis && progress?.phase === "step_analysis") {
    const saPhase = saProgress?.phase ?? "";
    const saCurrent = saProgress?.current ?? 0;
    const saTotal = saProgress?.total ?? 0;
    const saMessage = saProgress?.message ?? progress?.message ?? "Analyzing...";

    return (
      <div
        data-testid="running-panel"
        className="flex h-full min-h-0 flex-col p-6 animate-fade-in"
      >
        <Card className="flex min-h-0 w-full flex-1 flex-col overflow-hidden shadow-md">
          <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FlaskConical className="h-6 w-6 animate-pulse text-primary" />
                <h2
                  data-testid="phase-label"
                  className="text-base font-semibold text-foreground"
                >
                  Analyzing Strategy
                </h2>
                <ElapsedTimer />
              </div>
              <Button
                data-testid="cancel-experiment-btn"
                variant="outline"
                size="sm"
                onClick={cancelExperiment}
                className="hover:border-destructive hover:text-destructive"
              >
                <X className="h-3.5 w-3.5" />
                Cancel
              </Button>
            </div>

            {/* Phase stepper */}
            <div className="mt-5">
              <PhaseStepper
                phases={SA_PHASES}
                activePhase={saPhase}
                labels={STEP_ANALYSIS_PHASE_LABELS}
              />
            </div>

            {/* Sub-phase progress bar */}
            {saTotal > 0 && (
              <div className="mt-4">
                <Progress value={saCurrent} max={saTotal} />
                <div className="mt-1 flex justify-between text-xs text-muted-foreground">
                  <span>
                    {saCurrent} / {saTotal}
                  </span>
                  <span>{STEP_ANALYSIS_PHASE_LABELS[saPhase] ?? saPhase}</span>
                </div>
              </div>
            )}

            {/* Per-phase detail panel */}
            <div className="mt-4 flex min-h-0 flex-1 flex-col overflow-hidden">
              <StepAnalysisDetailPanel
                activePhase={saPhase}
                items={stepAnalysisItems}
                message={saMessage}
              />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Optimization layout
  if (isOptimizing) {
    return (
      <div
        data-testid="running-panel"
        className="flex h-full items-center justify-center p-6 animate-fade-in"
      >
        <Card className="w-full max-w-3xl shadow-md">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FlaskConical className="h-8 w-8 animate-pulse text-primary" />
                <div>
                  <h2 className="text-lg font-semibold text-foreground">
                    Running Experiment
                  </h2>
                  {progress && (
                    <Badge
                      data-testid="phase-label"
                      variant="secondary"
                      className="mt-1 text-xs"
                    >
                      {PHASE_LABELS[progress.phase] ?? progress.phase}
                    </Badge>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <ElapsedTimer />
                <Button
                  data-testid="cancel-experiment-btn"
                  variant="outline"
                  size="sm"
                  onClick={cancelExperiment}
                  className="hover:border-destructive hover:text-destructive"
                >
                  <X className="h-3.5 w-3.5" />
                  Cancel
                </Button>
              </div>
            </div>

            {runningConfig?.stepTree && (
              <div className="mt-4">
                <MiniTreeView tree={runningConfig.stepTree as PlanStepNode} />
              </div>
            )}

            <div className="mt-4 space-y-3">
              <div>
                <Progress value={currentTrial} max={totalTrials} />
                <div className="mt-1.5 flex justify-between text-xs text-muted-foreground">
                  <span>
                    Trial {currentTrial} / {totalTrials}
                  </span>
                  {bestScore != null && (
                    <span>
                      Best:{" "}
                      <span className="font-mono font-medium text-primary">
                        {bestScore.toFixed(4)}
                      </span>
                    </span>
                  )}
                </div>
              </div>
              {trialHistory.length > 1 && <OptimizationChart trials={trialHistory} />}
              {tp?.trial && (
                <div className="rounded-lg border border-border bg-muted/50 px-3 py-2 text-left text-xs text-muted-foreground">
                  <div className="mb-1 font-semibold text-foreground">
                    Latest trial #{tp.trial.trialNumber}
                  </div>
                  <div className="flex gap-4 font-mono">
                    <span>Score: {tp.trial.score.toFixed(4)}</span>
                    {tp.trial.recall != null && (
                      <span>Recall: {tp.trial.recall.toFixed(4)}</span>
                    )}
                    {tp.trial.resultCount != null && (
                      <span>Results: {tp.trial.resultCount}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Standard evaluation layout — now with phase stepper
  const currentPhase = progress?.phase ?? "started";

  return (
    <div
      data-testid="running-panel"
      className="flex h-full items-center justify-center p-6 animate-fade-in"
    >
      <Card className="w-full max-w-2xl shadow-md">
        <CardContent className="p-6">
          {/* Header with search info */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <BarChart3 className="h-8 w-8 animate-pulse text-primary" />
              <div>
                <h2 className="text-lg font-semibold text-foreground">
                  Evaluating Strategy
                </h2>
                {runningConfig?.searchName && (
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {runningConfig.searchName}
                    {runningConfig.recordType && (
                      <Badge variant="secondary" className="ml-2 text-[10px]">
                        {runningConfig.recordType}
                      </Badge>
                    )}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <ElapsedTimer />
              <Button
                data-testid="cancel-experiment-btn"
                variant="outline"
                size="sm"
                onClick={cancelExperiment}
                className="hover:border-destructive hover:text-destructive"
              >
                <X className="h-3.5 w-3.5" />
                Cancel
              </Button>
            </div>
          </div>

          {/* Phase stepper for standard evaluation */}
          <div className="mt-5">
            <PhaseStepper
              phases={STANDARD_PHASES}
              activePhase={currentPhase}
              labels={STANDARD_PHASE_LABELS}
            />
          </div>

          {progress?.message && (
            <div className="mt-4 text-center text-sm text-muted-foreground">
              {progress.message}
            </div>
          )}

          {runningConfig?.stepTree && (
            <div className="mt-4">
              <MiniTreeView tree={runningConfig.stepTree as PlanStepNode} />
            </div>
          )}

          {/* Cross-validation fold progress */}
          {progress?.cvFoldIndex != null && progress.cvTotalFolds != null && (
            <div className="mt-4">
              <div className="mb-1 text-center text-xs font-medium text-muted-foreground">
                Fold {progress.cvFoldIndex + 1} of {progress.cvTotalFolds}
              </div>
              <Progress value={progress.cvFoldIndex + 1} max={progress.cvTotalFolds} />
            </div>
          )}

          {/* Error display */}
          {progress?.error && (
            <div className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              <span className="font-semibold">Error: </span>
              {progress.error}
            </div>
          )}

          {!progress && (
            <div className="mt-4 flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Connecting...
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

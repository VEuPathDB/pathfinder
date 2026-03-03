import type { StepAnalysisPhase } from "@pathfinder/shared";
import { FlaskConical } from "lucide-react";
import { Checkbox } from "@/lib/components/ui/Checkbox";
import { Label } from "@/lib/components/ui/Label";

export interface StepAnalysisConfig {
  enabled: boolean;
  phases: Set<StepAnalysisPhase>;
}

const STEP_ANALYSIS_OPTIONS: {
  phase: StepAnalysisPhase;
  label: string;
  description: string;
}[] = [
  {
    phase: "step_evaluation",
    label: "Per-step evaluation",
    description: "Evaluate each search step independently against controls",
  },
  {
    phase: "operator_comparison",
    label: "Operator comparison",
    description: "Compare INTERSECT/UNION/MINUS at each combine node",
  },
  {
    phase: "contribution",
    label: "Step contribution",
    description: "Measure the impact of removing each step (ablation)",
  },
  {
    phase: "sensitivity",
    label: "Parameter sensitivity",
    description: "Sweep numeric parameters across their range",
  },
];

export interface StepAnalysisSectionProps {
  stepAnalysis: StepAnalysisConfig;
  onStepAnalysisChange: (v: StepAnalysisConfig) => void;
}

export function StepAnalysisSection({
  stepAnalysis,
  onStepAnalysisChange,
}: StepAnalysisSectionProps) {
  const togglePhase = (phase: StepAnalysisPhase) => {
    const next = new Set(stepAnalysis.phases);
    if (next.has(phase)) next.delete(phase);
    else next.add(phase);
    onStepAnalysisChange({ ...stepAnalysis, phases: next });
  };

  return (
    <div>
      <Label className="flex items-center gap-2 text-xs font-normal text-foreground">
        <Checkbox
          checked={stepAnalysis.enabled}
          onCheckedChange={(checked) =>
            onStepAnalysisChange({ ...stepAnalysis, enabled: checked === true })
          }
          className="h-3.5 w-3.5"
        />
        <FlaskConical className="h-3 w-3 text-primary" />
        Analyze Strategy
      </Label>
      <p className="mt-0.5 pl-5 text-[10px] text-muted-foreground">
        Evaluate each step, compare operators, measure contributions, and sweep
        parameters to understand your strategy.
      </p>

      {stepAnalysis.enabled && (
        <div className="mt-2 space-y-2 pl-5">
          {STEP_ANALYSIS_OPTIONS.map((opt) => (
            <Label
              key={opt.phase}
              className="flex items-start gap-2 text-xs font-normal text-foreground"
            >
              <Checkbox
                checked={stepAnalysis.phases.has(opt.phase)}
                onCheckedChange={() => togglePhase(opt.phase)}
                className="mt-0.5 h-3.5 w-3.5"
              />
              <div>
                <span>{opt.label}</span>
                <p className="text-[10px] text-muted-foreground">{opt.description}</p>
              </div>
            </Label>
          ))}
        </div>
      )}
    </div>
  );
}

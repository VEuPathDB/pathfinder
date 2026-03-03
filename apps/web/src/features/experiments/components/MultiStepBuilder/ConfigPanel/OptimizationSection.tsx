import { useState } from "react";
import type { ThresholdKnob, OperatorKnob } from "@pathfinder/shared";
import { SlidersHorizontal } from "lucide-react";
import { Checkbox } from "@/lib/components/ui/Checkbox";
import { Input } from "@/lib/components/ui/Input";
import { Label } from "@/lib/components/ui/Label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectGroup,
  SelectLabel as SelectGroupLabel,
  SelectTrigger,
  SelectValue,
} from "@/lib/components/ui/Select";

/* ── Constants ────────────────────────────────────────────────────── */

const AT_K_METRICS = [
  { base: "precision", label: "Precision" },
  { base: "recall", label: "Recall" },
  { base: "enrichment", label: "Enrichment" },
] as const;

const FIXED_METRICS = [
  { value: "f1", label: "F1 Score" },
  { value: "mcc", label: "MCC" },
  { value: "sensitivity", label: "Sensitivity" },
  { value: "specificity", label: "Specificity" },
  { value: "balanced_accuracy", label: "Balanced Accuracy" },
] as const;

const DEFAULT_K = 50;

/* ── Helpers ──────────────────────────────────────────────────────── */

function parseObjective(obj: string): { base: string; k: number | null } {
  const match = obj.match(/^(.+)_at_(\d+)$/);
  if (match) return { base: match[1], k: parseInt(match[2], 10) };
  return { base: obj, k: null };
}

/* ── ObjectivePicker ──────────────────────────────────────────────── */

function ObjectivePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const parsed = parseObjective(value);
  const isAtK = AT_K_METRICS.some((m) => m.base === parsed.base);
  const selectedBase = isAtK ? parsed.base : value;
  const kValue = parsed.k ?? DEFAULT_K;
  const [kDraft, setKDraft] = useState(String(kValue));

  const handleBaseChange = (base: string) => {
    if (AT_K_METRICS.some((m) => m.base === base)) {
      onChange(`${base}_at_${kValue}`);
    } else {
      onChange(base);
    }
  };

  const handleKChange = (raw: string) => {
    setKDraft(raw);
    const n = parseInt(raw, 10);
    if (n > 0 && AT_K_METRICS.some((m) => m.base === selectedBase)) {
      onChange(`${selectedBase}_at_${n}`);
    }
  };

  return (
    <div className="space-y-2">
      <Label className="text-[10px] text-muted-foreground">
        Optimization objective
      </Label>
      <Select value={selectedBase} onValueChange={handleBaseChange}>
        <SelectTrigger className="h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectGroupLabel>Rank-based (@K)</SelectGroupLabel>
            {AT_K_METRICS.map((m) => (
              <SelectItem key={m.base} value={m.base}>
                {m.label}@K
              </SelectItem>
            ))}
          </SelectGroup>
          <SelectGroup>
            <SelectGroupLabel>Classification</SelectGroupLabel>
            {FIXED_METRICS.map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      {AT_K_METRICS.some((m) => m.base === selectedBase) && (
        <div className="flex items-center gap-2">
          <Label className="text-[10px] text-muted-foreground whitespace-nowrap">
            K =
          </Label>
          <Input
            type="number"
            min={1}
            max={10000}
            className="h-7 w-20 font-mono text-xs tabular-nums"
            value={kDraft}
            onChange={(e) => handleKChange(e.target.value)}
          />
          <span className="text-[10px] text-muted-foreground">top list size</span>
        </div>
      )}
    </div>
  );
}

/* ── OptimizationSection ──────────────────────────────────────────── */

export interface OptimizationSectionProps {
  thresholdKnobs: ThresholdKnob[];
  onThresholdKnobsChange: (v: ThresholdKnob[]) => void;
  operatorKnobs: OperatorKnob[];
  onOperatorKnobsChange: (v: OperatorKnob[]) => void;
  treeOptObjective: string;
  onTreeOptObjectiveChange: (v: string) => void;
}

export function OptimizationSection({
  thresholdKnobs,
  onThresholdKnobsChange,
  operatorKnobs,
  onOperatorKnobsChange,
  treeOptObjective,
  onTreeOptObjectiveChange,
}: OptimizationSectionProps) {
  const [showKnobs, setShowKnobs] = useState(
    thresholdKnobs.length > 0 || operatorKnobs.length > 0,
  );

  return (
    <div className="space-y-2">
      <Label className="flex items-center gap-2 text-xs font-normal text-muted-foreground">
        <Checkbox
          checked={showKnobs}
          onCheckedChange={(checked) => {
            const val = checked === true;
            setShowKnobs(val);
            if (!val) {
              onThresholdKnobsChange([]);
              onOperatorKnobsChange([]);
            }
          }}
          className="h-3.5 w-3.5"
        />
        <SlidersHorizontal className="h-3 w-3" />
        Tree optimization knobs
      </Label>
      {showKnobs && (
        <div className="space-y-3 rounded-md border border-border bg-muted/30 p-3">
          <ObjectivePicker
            value={treeOptObjective}
            onChange={onTreeOptObjectiveChange}
          />
          <p className="text-[10px] text-muted-foreground">
            Mark numeric parameters and operators as tunable in the strategy graph, then
            this optimizer will search for the best combination.
            {thresholdKnobs.length > 0 && (
              <span className="ml-1 font-medium text-foreground">
                {thresholdKnobs.length} threshold knob(s) configured.
              </span>
            )}
            {operatorKnobs.length > 0 && (
              <span className="ml-1 font-medium text-foreground">
                {operatorKnobs.length} operator knob(s) configured.
              </span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}

import { useState, useEffect, useCallback } from "react";
import type { ControlSet, ResolvedGene } from "@pathfinder/shared";
import type { BenchmarkControlSetInput } from "../../../api/streaming";
import { listControlSets } from "../../../api/controlSets";
import { Button } from "@/lib/components/ui/Button";
import { Input } from "@/lib/components/ui/Input";
import { Label } from "@/lib/components/ui/Label";
import { Checkbox } from "@/lib/components/ui/Checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/lib/components/ui/Select";
import {
  ChevronDown,
  ChevronRight,
  Layers,
  Plus,
  Search,
  Star,
  Trash2,
  X,
} from "lucide-react";

/* ── GeneIdTextarea ──────────────────────────────────────────────── */

function parseGeneIds(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function GeneIdTextarea({
  ids,
  onIdsChange,
  placeholder,
}: {
  ids: string[];
  onIdsChange: (ids: string[]) => void;
  placeholder: string;
}) {
  const [text, setText] = useState(() => ids.join("\n"));
  const [prevIds, setPrevIds] = useState(ids);

  if (ids !== prevIds) {
    setPrevIds(ids);
    const currentIds = parseGeneIds(text);
    if (JSON.stringify(currentIds) !== JSON.stringify(ids)) {
      setText(ids.join("\n"));
    }
  }

  const handleBlur = () => {
    const parsed = parseGeneIds(text);
    setPrevIds(parsed);
    onIdsChange(parsed);
    setText(parsed.join("\n"));
  };

  return (
    <textarea
      rows={2}
      placeholder={placeholder}
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={handleBlur}
      className="w-full rounded border border-border bg-background px-2 py-1 text-[10px] font-mono placeholder:text-muted-foreground/60 focus:border-primary focus:outline-none"
    />
  );
}

export interface ControlsSectionProps {
  siteId: string;
  positiveGenes: ResolvedGene[];
  onPositiveGenesChange: (genes: ResolvedGene[]) => void;
  negativeGenes: ResolvedGene[];
  onNegativeGenesChange: (genes: ResolvedGene[]) => void;
  onOpenControlsModal: () => void;
  benchmarkMode: boolean;
  onBenchmarkModeChange: (v: boolean) => void;
  benchmarkControlSets: BenchmarkControlSetInput[];
  onBenchmarkControlSetsChange: (v: BenchmarkControlSetInput[]) => void;
}

/* ── SavedSetGeneList ─────────────────────────────────────────────── */

function SavedSetGeneList({
  positiveControls,
  negativeControls,
}: {
  positiveControls: string[];
  negativeControls: string[];
}) {
  const [expanded, setExpanded] = useState(false);
  const Icon = expanded ? ChevronDown : ChevronRight;

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"
      >
        <Icon className="h-3 w-3" />
        Saved set: {positiveControls.length} positive, {negativeControls.length}{" "}
        negative
      </button>
      {expanded && (
        <div className="space-y-1.5 pl-4">
          {positiveControls.length > 0 && (
            <div>
              <span className="text-[10px] font-medium text-green-700 dark:text-green-400">
                Positive ({positiveControls.length})
              </span>
              <div className="mt-0.5 flex flex-wrap gap-1">
                {positiveControls.map((id) => (
                  <span
                    key={id}
                    className="rounded bg-green-500/10 px-1 py-0.5 font-mono text-[9px] text-green-700 dark:text-green-400"
                  >
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}
          {negativeControls.length > 0 && (
            <div>
              <span className="text-[10px] font-medium text-red-700 dark:text-red-400">
                Negative ({negativeControls.length})
              </span>
              <div className="mt-0.5 flex flex-wrap gap-1">
                {negativeControls.map((id) => (
                  <span
                    key={id}
                    className="rounded bg-red-500/10 px-1 py-0.5 font-mono text-[9px] text-red-700 dark:text-red-400"
                  >
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── BenchmarkControlSetsEditor ───────────────────────────────────── */

function BenchmarkControlSetsEditor({
  controlSets,
  onChange,
  savedControlSets,
}: {
  controlSets: BenchmarkControlSetInput[];
  onChange: (v: BenchmarkControlSetInput[]) => void;
  savedControlSets: ControlSet[];
}) {
  const addInline = useCallback(() => {
    onChange([
      ...controlSets,
      {
        label: `Set ${controlSets.length + 1}`,
        positiveControls: [],
        negativeControls: [],
        isPrimary: controlSets.length === 0,
      },
    ]);
  }, [controlSets, onChange]);

  const addFromSaved = useCallback(
    (cs: ControlSet) => {
      if (controlSets.some((s) => s.controlSetId === cs.id)) return;
      onChange([
        ...controlSets,
        {
          label: cs.name,
          positiveControls: cs.positiveIds,
          negativeControls: cs.negativeIds,
          controlSetId: cs.id,
          isPrimary: controlSets.length === 0,
        },
      ]);
    },
    [controlSets, onChange],
  );

  const remove = useCallback(
    (idx: number) => {
      const next = controlSets.filter((_, i) => i !== idx);
      if (next.length > 0 && !next.some((s) => s.isPrimary)) {
        next[0] = { ...next[0], isPrimary: true };
      }
      onChange(next);
    },
    [controlSets, onChange],
  );

  const setPrimary = useCallback(
    (idx: number) => {
      onChange(controlSets.map((s, i) => ({ ...s, isPrimary: i === idx })));
    },
    [controlSets, onChange],
  );

  const updateLabel = useCallback(
    (idx: number, label: string) => {
      onChange(controlSets.map((s, i) => (i === idx ? { ...s, label } : s)));
    },
    [controlSets, onChange],
  );

  const updateIds = useCallback(
    (idx: number, field: "positiveControls" | "negativeControls", ids: string[]) => {
      onChange(controlSets.map((s, i) => (i === idx ? { ...s, [field]: ids } : s)));
    },
    [controlSets, onChange],
  );

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-muted-foreground">
        Add multiple control sets to benchmark your strategy. One must be marked as
        Primary for the main verdict.
      </p>

      {controlSets.map((cs, idx) => (
        <div
          key={idx}
          className={`relative space-y-1.5 rounded-md border p-2 ${
            cs.isPrimary
              ? "border-amber-400/50 bg-amber-50/50 dark:border-amber-600/30 dark:bg-amber-950/30"
              : "border-border bg-muted/30"
          }`}
        >
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setPrimary(idx)}
              title={cs.isPrimary ? "Primary benchmark" : "Set as primary"}
              className={`shrink-0 ${cs.isPrimary ? "text-amber-500" : "text-muted-foreground/40 hover:text-amber-400"}`}
            >
              <Star className={`h-3 w-3 ${cs.isPrimary ? "fill-current" : ""}`} />
            </button>
            <Input
              value={cs.label}
              onChange={(e) => updateLabel(idx, e.target.value)}
              className="h-6 flex-1 text-[11px]"
              placeholder="Label"
            />
            <button
              type="button"
              onClick={() => remove(idx)}
              className="shrink-0 text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
          {!cs.controlSetId && (
            <>
              <GeneIdTextarea
                ids={cs.positiveControls}
                onIdsChange={(ids) => updateIds(idx, "positiveControls", ids)}
                placeholder="Positive gene IDs (comma or newline separated)"
              />
              <GeneIdTextarea
                ids={cs.negativeControls}
                onIdsChange={(ids) => updateIds(idx, "negativeControls", ids)}
                placeholder="Negative gene IDs (comma or newline separated)"
              />
            </>
          )}
          {cs.controlSetId && (
            <SavedSetGeneList
              positiveControls={cs.positiveControls}
              negativeControls={cs.negativeControls}
            />
          )}
        </div>
      ))}

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className="flex-1 border-dashed text-[10px]"
          onClick={addInline}
        >
          <Plus className="h-3 w-3" />
          Add inline
        </Button>
        {savedControlSets.length > 0 && (
          <Select
            value=""
            onValueChange={(id) => {
              const cs = savedControlSets.find((s) => s.id === id);
              if (cs) addFromSaved(cs);
            }}
          >
            <SelectTrigger className="h-7 flex-1 border-dashed text-[10px]">
              <SelectValue placeholder="+ Add saved set" />
            </SelectTrigger>
            <SelectContent>
              {savedControlSets.map((cs) => (
                <SelectItem key={cs.id} value={cs.id}>
                  {cs.name} ({cs.positiveIds.length}+ / {cs.negativeIds.length}-)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
    </div>
  );
}

/* ── ControlsSection ──────────────────────────────────────────────── */

export function ControlsSection({
  siteId,
  positiveGenes,
  onPositiveGenesChange,
  negativeGenes,
  onNegativeGenesChange,
  onOpenControlsModal,
  benchmarkMode,
  onBenchmarkModeChange,
  benchmarkControlSets,
  onBenchmarkControlSetsChange,
}: ControlsSectionProps) {
  const [savedControlSets, setSavedControlSets] = useState<ControlSet[]>([]);

  useEffect(() => {
    if (benchmarkMode && siteId) {
      listControlSets(siteId)
        .then(setSavedControlSets)
        .catch((err) => console.error("[ControlsSection.listControlSets]", err));
    }
  }, [benchmarkMode, siteId]);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <Label className="flex items-center gap-1.5 text-[10px] font-medium text-muted-foreground">
          <Checkbox
            checked={benchmarkMode}
            onCheckedChange={(checked) => onBenchmarkModeChange(checked === true)}
            className="h-3.5 w-3.5"
          />
          <Layers className="h-3 w-3" />
          Benchmark suite
        </Label>
      </div>

      {!benchmarkMode ? (
        <>
          <Button
            variant="outline"
            size="sm"
            className="mb-2 w-full border-dashed"
            onClick={onOpenControlsModal}
          >
            <Search className="h-3 w-3" />
            {positiveGenes.length + negativeGenes.length > 0
              ? "Edit Control Genes"
              : "Find Control Genes"}
          </Button>

          {positiveGenes.length > 0 && (
            <div data-testid="positive-controls-input" className="mb-2">
              <Label className="mb-1 block text-[10px] text-muted-foreground">
                Positive ({positiveGenes.length})
              </Label>
              <div className="flex flex-wrap gap-1">
                {positiveGenes.slice(0, 8).map((g) => (
                  <span
                    key={g.geneId}
                    className="inline-flex items-center gap-1 rounded bg-green-500/10 px-1.5 py-0.5 text-[10px] text-green-700 dark:text-green-400"
                  >
                    {g.geneId}
                    <button
                      onClick={() =>
                        onPositiveGenesChange(
                          positiveGenes.filter((x) => x.geneId !== g.geneId),
                        )
                      }
                      className="hover:text-destructive"
                    >
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </span>
                ))}
                {positiveGenes.length > 8 && (
                  <span className="text-[10px] text-muted-foreground">
                    +{positiveGenes.length - 8} more
                  </span>
                )}
              </div>
            </div>
          )}

          {negativeGenes.length > 0 && (
            <div data-testid="negative-controls-input">
              <Label className="mb-1 block text-[10px] text-muted-foreground">
                Negative ({negativeGenes.length})
              </Label>
              <div className="flex flex-wrap gap-1">
                {negativeGenes.slice(0, 8).map((g) => (
                  <span
                    key={g.geneId}
                    className="inline-flex items-center gap-1 rounded bg-red-500/10 px-1.5 py-0.5 text-[10px] text-red-700 dark:text-red-400"
                  >
                    {g.geneId}
                    <button
                      onClick={() =>
                        onNegativeGenesChange(
                          negativeGenes.filter((x) => x.geneId !== g.geneId),
                        )
                      }
                      className="hover:text-destructive"
                    >
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </span>
                ))}
                {negativeGenes.length > 8 && (
                  <span className="text-[10px] text-muted-foreground">
                    +{negativeGenes.length - 8} more
                  </span>
                )}
              </div>
            </div>
          )}
        </>
      ) : (
        <BenchmarkControlSetsEditor
          controlSets={benchmarkControlSets}
          onChange={onBenchmarkControlSetsChange}
          savedControlSets={savedControlSets}
        />
      )}
    </div>
  );
}

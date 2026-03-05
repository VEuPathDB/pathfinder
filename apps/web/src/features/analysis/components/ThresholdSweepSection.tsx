import { useState, useMemo, useCallback, useRef } from "react";
import type { Experiment } from "@pathfinder/shared";
import { Play, Loader2, Square, TrendingUp, Target, AlertTriangle } from "lucide-react";
import { Button } from "@/lib/components/ui/Button";
import {
  streamThresholdSweep,
  type ThresholdSweepPoint,
  type ThresholdSweepResult,
  type SweepRequest,
} from "@/features/workbench/api";
import { CHART_COLORS } from "@/lib/utils/chartTheme";
import { pct } from "../utils/formatters";
import { useParamSpecs } from "../hooks/useParamSpecs";
import {
  isOptimizable,
  isNumericParam,
  isMultiPickParam,
  flattenVocab,
  type VocabEntry,
} from "../utils/paramUtils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SweepableParam {
  name: string;
  displayName: string;
  kind: "numeric" | "categorical";
  currentValue: string;
  /** Only for numeric params */
  numericValue?: number;
  /** Only for categorical params */
  vocab?: VocabEntry[];
}

const MAX_CATEGORICAL_CHOICES = 50;

interface ThresholdSweepSectionProps {
  experiment: Experiment;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ThresholdSweepSection({ experiment }: ThresholdSweepSectionProps) {
  const { siteId, recordType, searchName } = experiment.config;
  const { paramSpecs, isLoading: specsLoading } = useParamSpecs(
    siteId,
    recordType,
    searchName,
  );

  const [paramName, setParamName] = useState("");
  const [minVal, setMinVal] = useState("");
  const [maxVal, setMaxVal] = useState("");
  const [steps, setSteps] = useState("10");
  const [selectedValues, setSelectedValues] = useState<Set<string>>(new Set());

  // Progressive state
  const [livePoints, setLivePoints] = useState<ThresholdSweepPoint[]>([]);
  const [completedCount, setCompletedCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [finalResult, setFinalResult] = useState<ThresholdSweepResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Build sweepable params from ParamSpecs
  const sweepableParams = useMemo(() => {
    const configParams = experiment.config.parameters;
    if (!configParams || typeof configParams !== "object") return [];
    if (paramSpecs.length === 0) return [];

    const result: SweepableParam[] = [];
    for (const spec of paramSpecs) {
      // Skip non-optimizable, multi-pick, and params not in config
      if (!isOptimizable(spec)) continue;
      if (isMultiPickParam(spec)) continue;
      if (!(spec.name in configParams)) continue;

      const currentValue = String(configParams[spec.name] ?? "");

      if (isNumericParam(spec)) {
        result.push({
          name: spec.name,
          displayName: spec.displayName || spec.name,
          kind: "numeric",
          currentValue,
          numericValue: Number(currentValue),
        });
      } else {
        // Categorical: must have vocabulary with >1 entry
        const vocab = spec.vocabulary ? flattenVocab(spec.vocabulary) : [];
        if (vocab.length > 1) {
          result.push({
            name: spec.name,
            displayName: spec.displayName || spec.name,
            kind: "categorical",
            currentValue,
            vocab,
          });
        }
      }
    }
    return result;
  }, [paramSpecs, experiment.config.parameters]);

  const selectedParam = sweepableParams.find((p) => p.name === paramName) ?? null;
  const sweepType = selectedParam?.kind ?? "numeric";

  // Build vocab display map for the selected categorical param
  const vocabDisplayMap = useMemo(() => {
    if (!selectedParam?.vocab) return new Map<string, string>();
    return new Map(selectedParam.vocab.map((e) => [e.value, e.display]));
  }, [selectedParam]);

  const formatValue = useCallback(
    (v: number | string): string => {
      if (sweepType === "categorical") {
        return vocabDisplayMap.get(String(v)) ?? String(v);
      }
      return typeof v === "number" ? fmtNum(v) : v;
    },
    [sweepType, vocabDisplayMap],
  );

  const handleParamChange = useCallback(
    (name: string) => {
      setParamName(name);
      setFinalResult(null);
      setLivePoints([]);
      setError(null);

      const param = sweepableParams.find((p) => p.name === name);
      if (!param) return;

      if (param.kind === "numeric" && param.numericValue != null) {
        const cv = param.numericValue;
        setMinVal(String(Math.max(0, cv * 0.2)));
        setMaxVal(String(cv * 3));
      }

      if (param.kind === "categorical" && param.vocab) {
        // Select all by default
        setSelectedValues(new Set(param.vocab.map((e) => e.value)));
      }
    },
    [sweepableParams],
  );

  const handleRun = useCallback(async () => {
    if (!paramName || !selectedParam) return;

    let request: SweepRequest;
    if (selectedParam.kind === "numeric") {
      const mn = parseFloat(minVal);
      const mx = parseFloat(maxVal);
      const st = parseInt(steps);
      if (isNaN(mn) || isNaN(mx) || mn >= mx || isNaN(st)) return;
      request = {
        sweepType: "numeric",
        parameterName: paramName,
        minValue: mn,
        maxValue: mx,
        steps: Math.max(3, Math.min(50, st)),
      };
    } else {
      const values = Array.from(selectedValues);
      if (values.length < 2) return;
      request = {
        sweepType: "categorical",
        parameterName: paramName,
        values,
      };
    }

    // Reset state
    setLivePoints([]);
    setCompletedCount(0);
    setTotalCount(0);
    setFinalResult(null);
    setError(null);
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamThresholdSweep(
        experiment.id,
        request,
        {
          onPoint: (progress) => {
            setLivePoints((prev) => {
              const next = [...prev, progress.point];
              if (selectedParam.kind === "numeric") {
                next.sort((a, b) => Number(a.value) - Number(b.value));
              }
              return next;
            });
            setCompletedCount(progress.completedCount);
            setTotalCount(progress.totalCount);
          },
          onComplete: (result) => {
            setFinalResult(result);
          },
          onError: (err) => {
            setError(err.message);
          },
        },
        controller.signal,
      );
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [experiment.id, paramName, selectedParam, minVal, maxVal, steps, selectedValues]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // Use final result points if available, otherwise live points
  const displayPoints = finalResult?.points ?? livePoints;
  const validPoints = displayPoints.filter((p) => p.metrics != null);
  const failedPoints = displayPoints.filter((p) => p.metrics == null);
  const activeSweepType = finalResult?.sweepType ?? sweepType;

  if (specsLoading) {
    return (
      <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading parameter specifications...
      </div>
    );
  }

  if (sweepableParams.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-muted/30 px-5 py-8 text-center text-sm text-muted-foreground">
        No sweepable parameters detected in this experiment&apos;s configuration.
      </div>
    );
  }

  const canRun =
    selectedParam &&
    (selectedParam.kind === "numeric"
      ? paramName && minVal && maxVal
      : selectedValues.size >= 2);

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Sweep a parameter across a range (numeric) or set of values (categorical) to
        visualize the sensitivity/specificity trade-off.
      </p>

      {/* Parameter selector */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">
          Parameter
        </label>
        <select
          value={paramName}
          onChange={(e) => handleParamChange(e.target.value)}
          className="h-8 w-full max-w-sm rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">Select...</option>
          <optgroup label="Numeric">
            {sweepableParams
              .filter((p) => p.kind === "numeric")
              .map((p) => (
                <option key={p.name} value={p.name}>
                  {p.displayName} (current: {p.currentValue})
                </option>
              ))}
          </optgroup>
          <optgroup label="Categorical">
            {sweepableParams
              .filter((p) => p.kind === "categorical")
              .map((p) => (
                <option key={p.name} value={p.name}>
                  {p.displayName} (current: {formatValue(p.currentValue)})
                </option>
              ))}
          </optgroup>
        </select>
      </div>

      {/* Numeric config */}
      {selectedParam?.kind === "numeric" && (
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Min
            </label>
            <input
              type="number"
              value={minVal}
              onChange={(e) => setMinVal(e.target.value)}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Max
            </label>
            <input
              type="number"
              value={maxVal}
              onChange={(e) => setMaxVal(e.target.value)}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Steps
            </label>
            <input
              type="number"
              min={3}
              max={50}
              value={steps}
              onChange={(e) => setSteps(e.target.value)}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>
      )}

      {/* Categorical config */}
      {selectedParam?.kind === "categorical" && selectedParam.vocab && (
        <CategoricalPicker
          vocab={selectedParam.vocab}
          selected={selectedValues}
          onChange={setSelectedValues}
        />
      )}

      {/* Run / Cancel */}
      <div className="flex items-center gap-2">
        {loading ? (
          <Button size="sm" variant="destructive" onClick={handleCancel}>
            <Square className="h-3.5 w-3.5" />
            Cancel
          </Button>
        ) : (
          <Button size="sm" onClick={handleRun} disabled={!canRun}>
            <Play className="h-3.5 w-3.5" />
            Run Sweep
          </Button>
        )}

        {loading && totalCount > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>
              {completedCount} / {totalCount} points
            </span>
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${(completedCount / totalCount) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      {validPoints.length >= 2 && (
        <SweepChart
          points={validPoints}
          parameter={finalResult?.parameter ?? paramName}
          sweepType={activeSweepType}
          formatValue={formatValue}
          isStreaming={loading}
        />
      )}

      {validPoints.length >= 2 && !loading && finalResult && (
        <SweepSummary
          points={validPoints}
          parameter={finalResult.parameter}
          sweepType={activeSweepType}
          formatValue={formatValue}
          currentValue={selectedParam?.currentValue}
          failedCount={failedPoints.length}
        />
      )}

      {validPoints.length > 0 && (
        <SweepTable
          points={validPoints}
          parameter={finalResult?.parameter ?? paramName}
          formatValue={formatValue}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Categorical value picker
// ---------------------------------------------------------------------------

function CategoricalPicker({
  vocab,
  selected,
  onChange,
}: {
  vocab: VocabEntry[];
  selected: Set<string>;
  onChange: (s: Set<string>) => void;
}) {
  const oversized = vocab.length > MAX_CATEGORICAL_CHOICES;
  const displayVocab = oversized ? vocab.slice(0, MAX_CATEGORICAL_CHOICES) : vocab;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">
          Values to sweep ({selected.size} selected)
        </span>
        <button
          type="button"
          onClick={() => onChange(new Set(displayVocab.map((e) => e.value)))}
          className="text-xs text-primary hover:underline"
        >
          Select all
        </button>
        <button
          type="button"
          onClick={() => onChange(new Set())}
          className="text-xs text-primary hover:underline"
        >
          Deselect all
        </button>
      </div>

      {oversized && (
        <p className="text-xs text-amber-500">
          <AlertTriangle className="mr-1 inline h-3 w-3" />
          This parameter has {vocab.length} values. Showing first{" "}
          {MAX_CATEGORICAL_CHOICES}.
        </p>
      )}

      <div className="max-h-48 overflow-y-auto rounded-md border border-border bg-card p-2">
        <div className="grid grid-cols-2 gap-1">
          {displayVocab.map((entry) => (
            <label
              key={entry.value}
              className="flex cursor-pointer items-center gap-1.5 rounded px-1.5 py-0.5 text-xs hover:bg-muted/50"
            >
              <input
                type="checkbox"
                checked={selected.has(entry.value)}
                onChange={(e) => {
                  const next = new Set(selected);
                  if (e.target.checked) next.add(entry.value);
                  else next.delete(entry.value);
                  onChange(next);
                }}
                className="h-3 w-3 rounded border-input"
              />
              <span className="truncate text-foreground" title={entry.display}>
                {entry.display}
              </span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Summary card with recommendations
// ---------------------------------------------------------------------------

function SweepSummary({
  points,
  parameter,
  sweepType,
  formatValue,
  currentValue,
  failedCount,
}: {
  points: ThresholdSweepPoint[];
  parameter: string;
  sweepType: "numeric" | "categorical";
  formatValue: (v: number | string) => string;
  currentValue?: string;
  failedCount: number;
}) {
  const bestF1 = points.reduce((best, p) =>
    (p.metrics?.f1Score ?? 0) > (best.metrics?.f1Score ?? 0) ? p : best,
  );
  const bestBalAcc = points.reduce((best, p) =>
    (p.metrics?.balancedAccuracy ?? 0) > (best.metrics?.balancedAccuracy ?? 0)
      ? p
      : best,
  );
  const bestSens = points.reduce((best, p) =>
    (p.metrics?.sensitivity ?? 0) > (best.metrics?.sensitivity ?? 0) ? p : best,
  );

  const currentPoint =
    currentValue != null
      ? sweepType === "numeric"
        ? points.reduce((closest, p) =>
            Math.abs(Number(p.value) - Number(currentValue)) <
            Math.abs(Number(closest.value) - Number(currentValue))
              ? p
              : closest,
          )
        : (points.find((p) => String(p.value) === currentValue) ?? null)
      : null;

  return (
    <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-3">
      <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <TrendingUp className="h-3.5 w-3.5" />
        Sweep Summary
      </h4>

      <div className="grid grid-cols-3 gap-4">
        <SummaryCard
          label="Best F1 Score"
          value={pct(bestF1.metrics?.f1Score)}
          detail={`at ${parameter} = ${formatValue(bestF1.value)}`}
        />
        <SummaryCard
          label="Best Balanced Accuracy"
          value={pct(bestBalAcc.metrics?.balancedAccuracy)}
          detail={`at ${parameter} = ${formatValue(bestBalAcc.value)}`}
        />
        <SummaryCard
          label="Best Sensitivity"
          value={pct(bestSens.metrics?.sensitivity)}
          detail={`at ${parameter} = ${formatValue(bestSens.value)}`}
        />
      </div>

      {currentPoint && currentValue != null && (
        <div className="flex items-start gap-2 rounded-md border border-border bg-card px-3 py-2">
          <Target className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <div className="text-xs">
            <span className="text-muted-foreground">Current value </span>
            <span className="font-mono font-medium text-foreground">
              {parameter} = {formatValue(currentValue)}
            </span>
            <span className="text-muted-foreground"> yields </span>
            <span className="font-medium text-foreground">
              F1 {pct(currentPoint.metrics?.f1Score)}
            </span>
            {bestF1.value !== currentPoint.value && (
              <>
                <span className="text-muted-foreground">. Consider </span>
                <span className="font-mono font-medium text-primary">
                  {formatValue(bestF1.value)}
                </span>
                <span className="text-muted-foreground"> for peak F1 </span>
                <span className="font-medium text-primary">
                  {pct(bestF1.metrics?.f1Score)}
                </span>
              </>
            )}
          </div>
        </div>
      )}

      {failedCount > 0 && (
        <div className="flex items-center gap-1.5 text-xs text-amber-500">
          <AlertTriangle className="h-3 w-3" />
          {failedCount} point{failedCount !== 1 ? "s" : ""} failed (timeout or WDK
          error)
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="text-lg font-semibold tabular-nums text-foreground">{value}</div>
      <div className="text-[10px] text-muted-foreground">{detail}</div>
    </div>
  );
}

function fmtNum(v: number): string {
  return Number.isInteger(v) ? String(v) : v.toFixed(2);
}

// ---------------------------------------------------------------------------
// SVG chart
// ---------------------------------------------------------------------------

function SweepChart({
  points,
  parameter,
  sweepType,
  formatValue,
  isStreaming,
}: {
  points: ThresholdSweepPoint[];
  parameter: string;
  sweepType: "numeric" | "categorical";
  formatValue: (v: number | string) => string;
  isStreaming: boolean;
}) {
  const W = 600;
  const H = 260;
  const PAD = { top: 20, right: 20, bottom: 40, left: 50 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const y = (v: number) => PAD.top + plotH - v * plotH;
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  if (sweepType === "categorical") {
    // Evenly-spaced x-axis for categorical values
    const spacing = points.length > 1 ? plotW / (points.length - 1) : plotW / 2;
    const xCat = (i: number) =>
      PAD.left + (points.length > 1 ? i * spacing : plotW / 2);

    const makeLineCat = (getter: (p: ThresholdSweepPoint) => number) =>
      points
        .map(
          (p, i) =>
            `${i === 0 ? "M" : "L"}${xCat(i).toFixed(1)},${y(getter(p)).toFixed(1)}`,
        )
        .join(" ");

    const sensLine = makeLineCat((p) => p.metrics!.sensitivity);
    const specLine = makeLineCat((p) => p.metrics!.specificity);
    const f1Line = makeLineCat((p) => p.metrics!.f1Score);

    return (
      <ChartWrapper parameter={parameter} isStreaming={isStreaming}>
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: H }}>
          {yTicks.map((v) => (
            <g key={v}>
              <line
                x1={PAD.left}
                y1={y(v)}
                x2={W - PAD.right}
                y2={y(v)}
                stroke="hsl(var(--border))"
                strokeWidth={0.5}
              />
              <text
                x={PAD.left - 6}
                y={y(v) + 3}
                textAnchor="end"
                className="fill-muted-foreground"
                style={{ fontSize: 9 }}
              >
                {(v * 100).toFixed(0)}%
              </text>
            </g>
          ))}
          {points.map((p, i) => (
            <text
              key={String(p.value)}
              x={xCat(i)}
              y={H - PAD.bottom + 16}
              textAnchor="middle"
              className="fill-muted-foreground"
              style={{ fontSize: 8 }}
            >
              {truncateLabel(formatValue(p.value), 12)}
            </text>
          ))}
          <text
            x={PAD.left + plotW / 2}
            y={H - 4}
            textAnchor="middle"
            className="fill-muted-foreground"
            style={{ fontSize: 10 }}
          >
            {parameter}
          </text>

          <path
            d={sensLine}
            fill="none"
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
          />
          <path
            d={specLine}
            fill="none"
            stroke={CHART_COLORS.destructive}
            strokeWidth={2}
          />
          <path
            d={f1Line}
            fill="none"
            stroke="hsl(var(--foreground))"
            strokeWidth={2}
            strokeDasharray="4 2"
          />

          {points.map((p, i) => (
            <g key={String(p.value)}>
              <circle
                cx={xCat(i)}
                cy={y(p.metrics!.sensitivity)}
                r={2.5}
                fill={CHART_COLORS.primary}
              />
              <circle
                cx={xCat(i)}
                cy={y(p.metrics!.specificity)}
                r={2.5}
                fill={CHART_COLORS.destructive}
              />
              <circle
                cx={xCat(i)}
                cy={y(p.metrics!.f1Score)}
                r={2}
                fill="hsl(var(--foreground))"
              />
            </g>
          ))}
        </svg>
        <ChartLegend />
      </ChartWrapper>
    );
  }

  // Numeric: continuous x-axis
  const numValues = points.map((p) => Number(p.value));
  const xMin = Math.min(...numValues);
  const xMax = Math.max(...numValues);
  const xRange = xMax - xMin || 1;
  const x = (v: number) => PAD.left + ((v - xMin) / xRange) * plotW;

  const makeLine = (getter: (p: ThresholdSweepPoint) => number) =>
    points
      .map(
        (p, i) =>
          `${i === 0 ? "M" : "L"}${x(Number(p.value)).toFixed(1)},${y(getter(p)).toFixed(1)}`,
      )
      .join(" ");

  const sensLine = makeLine((p) => p.metrics!.sensitivity);
  const specLine = makeLine((p) => p.metrics!.specificity);
  const f1Line = makeLine((p) => p.metrics!.f1Score);

  const xTicks = points.filter(
    (_, i) =>
      i === 0 || i === points.length - 1 || i % Math.ceil(points.length / 6) === 0,
  );

  return (
    <ChartWrapper parameter={parameter} isStreaming={isStreaming}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: H }}>
        {yTicks.map((v) => (
          <g key={v}>
            <line
              x1={PAD.left}
              y1={y(v)}
              x2={W - PAD.right}
              y2={y(v)}
              stroke="hsl(var(--border))"
              strokeWidth={0.5}
            />
            <text
              x={PAD.left - 6}
              y={y(v) + 3}
              textAnchor="end"
              className="fill-muted-foreground"
              style={{ fontSize: 9 }}
            >
              {(v * 100).toFixed(0)}%
            </text>
          </g>
        ))}
        {xTicks.map((p) => (
          <text
            key={String(p.value)}
            x={x(Number(p.value))}
            y={H - PAD.bottom + 16}
            textAnchor="middle"
            className="fill-muted-foreground"
            style={{ fontSize: 9 }}
          >
            {fmtNum(Number(p.value))}
          </text>
        ))}
        <text
          x={PAD.left + plotW / 2}
          y={H - 4}
          textAnchor="middle"
          className="fill-muted-foreground"
          style={{ fontSize: 10 }}
        >
          {parameter}
        </text>

        <path d={sensLine} fill="none" stroke={CHART_COLORS.primary} strokeWidth={2} />
        <path
          d={specLine}
          fill="none"
          stroke={CHART_COLORS.destructive}
          strokeWidth={2}
        />
        <path
          d={f1Line}
          fill="none"
          stroke="hsl(var(--foreground))"
          strokeWidth={2}
          strokeDasharray="4 2"
        />

        {points.map((p) => (
          <g key={String(p.value)}>
            <circle
              cx={x(Number(p.value))}
              cy={y(p.metrics!.sensitivity)}
              r={2.5}
              fill={CHART_COLORS.primary}
            />
            <circle
              cx={x(Number(p.value))}
              cy={y(p.metrics!.specificity)}
              r={2.5}
              fill={CHART_COLORS.destructive}
            />
            <circle
              cx={x(Number(p.value))}
              cy={y(p.metrics!.f1Score)}
              r={2}
              fill="hsl(var(--foreground))"
            />
          </g>
        ))}
      </svg>
      <ChartLegend />
    </ChartWrapper>
  );
}

function ChartWrapper({
  parameter,
  isStreaming,
  children,
}: {
  parameter: string;
  isStreaming: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
        Metrics vs {parameter}
        {isStreaming && (
          <span className="flex items-center gap-1 text-primary">
            <Loader2 className="h-3 w-3 animate-spin" />
            streaming
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

function ChartLegend() {
  return (
    <div className="mt-2 flex justify-center gap-6 text-xs text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-0.5 w-4 rounded bg-[hsl(var(--chart-1))]" />
        Sensitivity
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-0.5 w-4 rounded bg-[hsl(var(--chart-4))]" />
        Specificity
      </span>
      <span className="flex items-center gap-1.5">
        <span
          className="inline-block h-0.5 w-4 rounded border-t border-dashed border-foreground bg-transparent"
          style={{ borderTopWidth: 2 }}
        />
        F1
      </span>
    </div>
  );
}

function truncateLabel(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "\u2026" : s;
}

// ---------------------------------------------------------------------------
// Data table
// ---------------------------------------------------------------------------

function SweepTable({
  points,
  parameter,
  formatValue,
}: {
  points: ThresholdSweepPoint[];
  parameter: string;
  formatValue: (v: number | string) => string;
}) {
  return (
    <div className="max-h-52 overflow-y-auto rounded-md border border-border">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-card">
          <tr className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground">
            <th className="px-3 py-2 font-medium">{parameter}</th>
            <th className="px-3 py-2 font-medium">Sensitivity</th>
            <th className="px-3 py-2 font-medium">Specificity</th>
            <th className="px-3 py-2 font-medium">F1</th>
            <th className="px-3 py-2 font-medium">MCC</th>
            <th className="px-3 py-2 font-medium">Bal. Acc.</th>
            <th className="px-3 py-2 font-medium">Results</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {points.map((p) => (
            <tr key={String(p.value)}>
              <td className="px-3 py-1.5 font-mono text-foreground">
                {formatValue(p.value)}
              </td>
              <td className="px-3 py-1.5 font-mono text-muted-foreground">
                {pct(p.metrics!.sensitivity)}
              </td>
              <td className="px-3 py-1.5 font-mono text-muted-foreground">
                {pct(p.metrics!.specificity)}
              </td>
              <td className="px-3 py-1.5 font-mono text-muted-foreground">
                {pct(p.metrics!.f1Score)}
              </td>
              <td className="px-3 py-1.5 font-mono text-muted-foreground">
                {pct(p.metrics!.mcc)}
              </td>
              <td className="px-3 py-1.5 font-mono text-muted-foreground">
                {pct(p.metrics!.balancedAccuracy)}
              </td>
              <td className="px-3 py-1.5 font-mono text-muted-foreground">
                {p.metrics!.totalResults}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

"use client";

import { useMemo, useCallback, useEffect, useState } from "react";
import { VennDiagram, VennSeries, VennArc } from "reaviz";
import {
  computeVennData,
  computeExclusiveRegions,
  logScaleVennData,
  type VennInput,
} from "@/lib/utils/vennData";

const CHART_VARS = ["--chart-1", "--chart-2", "--chart-3", "--chart-4", "--chart-5"];
const FALLBACK_COLORS = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed"];

/** Resolve CSS custom properties to actual color strings D3/chroma can parse. */
function resolveChartColors(): string[] {
  if (typeof document === "undefined") return FALLBACK_COLORS;
  const style = getComputedStyle(document.documentElement);
  return CHART_VARS.map((v, i) => {
    const raw = style.getPropertyValue(v).trim();
    return raw ? `hsl(${raw})` : FALLBACK_COLORS[i];
  });
}

interface SetVennProps {
  sets: VennInput[];
  height?: number;
  width?: number;
  onRegionClick?: (geneIds: string[], label: string) => void;
}

export function SetVenn({
  sets,
  height = 240,
  width = 380,
  onRegionClick,
}: SetVennProps) {
  const [colors, setColors] = useState(FALLBACK_COLORS);
  useEffect(() => {
    queueMicrotask(() => setColors(resolveChartColors()));
  }, []);

  const data = useMemo(() => logScaleVennData(computeVennData(sets)), [sets]);

  const exclusiveRegions = useMemo(
    () => (onRegionClick ? computeExclusiveRegions(sets) : null),
    [sets, onRegionClick],
  );

  const handleArcClick = useCallback(
    (event: { value: { sets: string[]; size: number }; nativeEvent: MouseEvent }) => {
      if (!onRegionClick || !exclusiveRegions) return;
      const regionKey = event.value.sets.join(",");
      const geneIds = exclusiveRegions.get(regionKey) ?? [];
      const label =
        event.value.sets.length === 1
          ? `Only ${event.value.sets[0]}`
          : event.value.sets.join(" \u2229 ");
      onRegionClick(geneIds, label);
    },
    [onRegionClick, exclusiveRegions],
  );

  return (
    <div className="flex flex-col items-center gap-1">
      <VennDiagram
        type="euler"
        height={height}
        width={width}
        data={data}
        series={
          <VennSeries
            colorScheme={colors.slice(0, sets.length)}
            arc={
              <VennArc
                strokeWidth={1.5}
                onClick={onRegionClick ? handleArcClick : undefined}
                style={{ cursor: onRegionClick ? "pointer" : "default" }}
              />
            }
          />
        }
      />
      {onRegionClick && (
        <p className="text-[10px] text-muted-foreground">
          Click a region to create a gene set
        </p>
      )}
    </div>
  );
}

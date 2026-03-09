"use client";

import { useMemo } from "react";
import { computeVennRegions } from "@/lib/utils/setOperations";

interface VennSet {
  name: string;
  geneIds: string[];
}

interface VennDiagramProps {
  setA: VennSet;
  setB: VennSet;
  onRegionClick: (geneIds: string[], label: string) => void;
}

// SVG layout: two overlapping circles
const W = 240;
const H = 140;
const R = 55;
const CX_A = W / 2 - 25;
const CX_B = W / 2 + 25;
const CY = H / 2;

export function VennDiagram({ setA, setB, onRegionClick }: VennDiagramProps) {
  const regions = useMemo(
    () => computeVennRegions(setA.geneIds, setB.geneIds),
    [setA.geneIds, setB.geneIds],
  );

  const regionStyle = "cursor-pointer transition-opacity duration-150 hover:opacity-80";

  return (
    <div className="flex flex-col items-center gap-1">
      {/* Set labels */}
      <div className="flex w-full justify-between px-4 text-[10px] font-medium text-muted-foreground">
        <span className="max-w-[45%] truncate" title={setA.name}>
          {setA.name}
        </span>
        <span className="max-w-[45%] truncate text-right" title={setB.name}>
          {setB.name}
        </span>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full max-w-[240px]"
        role="img"
        aria-label="Venn diagram"
      >
        {/* Only A region */}
        <circle
          cx={CX_A}
          cy={CY}
          r={R}
          className={regionStyle}
          fill="hsl(var(--chart-1) / 0.25)"
          stroke="hsl(var(--chart-1) / 0.6)"
          strokeWidth={1.5}
          aria-label={`Only ${setA.name}: ${regions.onlyA.length} genes`}
          role="button"
          tabIndex={0}
          onClick={() => onRegionClick(regions.onlyA, `Only ${setA.name}`)}
        />

        {/* Only B region */}
        <circle
          cx={CX_B}
          cy={CY}
          r={R}
          className={regionStyle}
          fill="hsl(var(--chart-2) / 0.25)"
          stroke="hsl(var(--chart-2) / 0.6)"
          strokeWidth={1.5}
          aria-label={`Only ${setB.name}: ${regions.onlyB.length} genes`}
          role="button"
          tabIndex={0}
          onClick={() => onRegionClick(regions.onlyB, `Only ${setB.name}`)}
        />

        {/* Intersection region (rendered on top) */}
        <ellipse
          cx={(CX_A + CX_B) / 2}
          cy={CY}
          rx={R - 25}
          ry={R - 5}
          className={regionStyle}
          fill="hsl(var(--chart-3) / 0.35)"
          stroke="hsl(var(--chart-3) / 0.6)"
          strokeWidth={1.5}
          aria-label={`Shared: ${regions.shared.length} genes`}
          role="button"
          tabIndex={0}
          onClick={() =>
            onRegionClick(regions.shared, `${setA.name} \u2229 ${setB.name}`)
          }
        />

        {/* Count labels */}
        <text
          x={CX_A - 20}
          y={CY + 4}
          textAnchor="middle"
          className="pointer-events-none fill-foreground text-sm font-semibold"
          data-testid="count-only-a"
        >
          {regions.onlyA.length}
        </text>
        <text
          x={(CX_A + CX_B) / 2}
          y={CY + 4}
          textAnchor="middle"
          className="pointer-events-none fill-foreground text-sm font-bold"
          data-testid="count-shared"
        >
          {regions.shared.length}
        </text>
        <text
          x={CX_B + 20}
          y={CY + 4}
          textAnchor="middle"
          className="pointer-events-none fill-foreground text-sm font-semibold"
          data-testid="count-only-b"
        >
          {regions.onlyB.length}
        </text>
      </svg>

      <p className="text-[10px] text-muted-foreground">
        Click a region to create a gene set
      </p>
    </div>
  );
}

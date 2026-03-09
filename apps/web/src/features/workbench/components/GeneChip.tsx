"use client";

import { useState, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { AlertCircle, Check, X } from "lucide-react";
import type { ResolvedGene } from "@pathfinder/shared";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ChipStatus = "pending" | "verified" | "invalid";

interface GeneChipProps {
  geneId: string;
  status: ChipStatus;
  resolvedGene?: ResolvedGene | null;
  onRemove: (geneId: string) => void;
}

// ---------------------------------------------------------------------------
// Hover card
// ---------------------------------------------------------------------------

function GeneHoverCard({
  gene,
  position,
}: {
  gene: ResolvedGene;
  position: { top: number; left: number };
}) {
  return createPortal(
    <div
      className="pointer-events-none fixed z-50 w-64 rounded-lg border border-border bg-popover p-3 shadow-lg animate-hover-card-in"
      style={{ top: position.top, left: position.left }}
    >
      <p className="font-mono text-xs font-semibold text-foreground">{gene.geneId}</p>
      <dl className="mt-2 space-y-1 text-[10px]">
        <div>
          <dt className="font-medium text-muted-foreground">Product</dt>
          <dd className="text-foreground">{gene.product || "\u2014"}</dd>
        </div>
        <div>
          <dt className="font-medium text-muted-foreground">Organism</dt>
          <dd className="italic text-foreground">{gene.organism}</dd>
        </div>
        {gene.geneName && (
          <div>
            <dt className="font-medium text-muted-foreground">Gene name</dt>
            <dd className="text-foreground">{gene.geneName}</dd>
          </div>
        )}
        {gene.geneType && (
          <div>
            <dt className="font-medium text-muted-foreground">Type</dt>
            <dd className="text-foreground">{gene.geneType}</dd>
          </div>
        )}
        {gene.location && (
          <div>
            <dt className="font-medium text-muted-foreground">Location</dt>
            <dd className="text-foreground">{gene.location}</dd>
          </div>
        )}
      </dl>
    </div>,
    document.body,
  );
}

// ---------------------------------------------------------------------------
// Status styling
// ---------------------------------------------------------------------------

const STATUS_CLASSES: Record<ChipStatus, string> = {
  pending: "border-border bg-muted/50 text-foreground animate-pulse-subtle",
  verified: "border-green-500/40 bg-green-500/5 text-foreground",
  invalid: "border-destructive/40 bg-destructive/5 text-destructive",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function GeneChip({ geneId, status, resolvedGene, onRemove }: GeneChipProps) {
  const [showHover, setShowHover] = useState(false);
  const [hoverPos, setHoverPos] = useState({ top: 0, left: 0 });
  const chipRef = useRef<HTMLSpanElement>(null);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = useCallback(() => {
    if (!resolvedGene) return;
    hoverTimer.current = setTimeout(() => {
      if (!chipRef.current) return;
      const rect = chipRef.current.getBoundingClientRect();
      setHoverPos({ top: rect.bottom + 4, left: rect.left });
      setShowHover(true);
    }, 200);
  }, [resolvedGene]);

  const handleMouseLeave = useCallback(() => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    setShowHover(false);
  }, []);

  return (
    <>
      <span
        ref={chipRef}
        data-gene-chip
        data-status={status}
        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-mono animate-chip-in transition-colors duration-300 ${STATUS_CLASSES[status]}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {status === "verified" && (
          <Check className="h-2.5 w-2.5 text-green-600 dark:text-green-400" />
        )}
        {status === "invalid" && <AlertCircle className="h-2.5 w-2.5" />}
        {geneId}
        <button
          type="button"
          aria-label={`Remove ${geneId}`}
          onClick={() => onRemove(geneId)}
          className="ml-0.5 rounded-full p-0.5 hover:bg-accent transition-colors duration-150"
        >
          <X className="h-2.5 w-2.5" />
        </button>
      </span>

      {showHover && resolvedGene && (
        <GeneHoverCard gene={resolvedGene} position={hoverPos} />
      )}
    </>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useWorkbenchStore } from "../store";
import type { GeneSet } from "../store";
import { deleteGeneSet } from "../api/geneSets";
import { exportAsTxt, exportAsCsv } from "../utils/export";
import { SetOperationsMenu } from "./SetOperationsMenu";
import { cn } from "@/lib/utils/cn";
import { Button } from "@/lib/components/ui/Button";
import {
  Database,
  ClipboardPaste,
  Upload,
  GitMerge,
  Bookmark,
  Plus,
  Trash2,
  GitCompare,
  Layers,
  Download,
} from "lucide-react";
import { AddGeneSetModal } from "./AddGeneSetModal";
import { CompareModal } from "./CompareModal";
import { OverlapModal } from "./OverlapModal";

// ---------------------------------------------------------------------------
// Source icon mapping
// ---------------------------------------------------------------------------

const SOURCE_ICONS: Record<GeneSet["source"], React.ElementType> = {
  strategy: Database,
  paste: ClipboardPaste,
  upload: Upload,
  derived: GitMerge,
  saved: Bookmark,
};

function SourceIcon({ source }: { source: GeneSet["source"] }) {
  const Icon = SOURCE_ICONS[source];
  return <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />;
}

// ---------------------------------------------------------------------------
// Gene set card (with selection checkbox)
// ---------------------------------------------------------------------------

interface GeneSetCardProps {
  geneSet: GeneSet;
  isActive: boolean;
  isSelected: boolean;
  onActivate: () => void;
  onToggleSelect: () => void;
}

function GeneSetCard({
  geneSet,
  isActive,
  isSelected,
  onActivate,
  onToggleSelect,
}: GeneSetCardProps) {
  return (
    <div
      className={cn(
        "group flex items-start gap-2 rounded-md border px-3 py-2 transition-colors",
        isActive ? "border-input bg-muted" : "border-transparent hover:bg-muted/50",
      )}
    >
      {/* Selection checkbox */}
      <label className="mt-0.5 flex shrink-0 items-center">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
          className="h-3.5 w-3.5 cursor-pointer rounded border-border accent-primary"
          aria-label={`Select ${geneSet.name}`}
        />
      </label>

      {/* Clickable card body */}
      <button type="button" onClick={onActivate} className="min-w-0 flex-1 text-left">
        <div className="flex items-center gap-2">
          <SourceIcon source={geneSet.source} />
          <span className="truncate text-sm font-medium text-foreground">
            {geneSet.name}
          </span>
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          <span>{geneSet.geneCount.toLocaleString()} genes</span>
          <span className="text-border">|</span>
          <span className="capitalize">{geneSet.source}</span>
        </div>
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

export function WorkbenchSidebar() {
  const geneSets = useWorkbenchStore((s) => s.geneSets);
  const activeSetId = useWorkbenchStore((s) => s.activeSetId);
  const selectedSetIds = useWorkbenchStore((s) => s.selectedSetIds);
  const setActiveSet = useWorkbenchStore((s) => s.setActiveSet);
  const toggleSetSelection = useWorkbenchStore((s) => s.toggleSetSelection);
  const removeGeneSet = useWorkbenchStore((s) => s.removeGeneSet);
  const [deleting, setDeleting] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [showOverlap, setShowOverlap] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!showExportMenu) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setShowExportMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showExportMenu]);

  const activeSet = geneSets.find((gs) => gs.id === activeSetId) ?? null;
  const selectedSets = geneSets.filter((gs) => selectedSetIds.includes(gs.id));
  const hasExactlyTwo = selectedSets.length === 2;
  const hasTwoOrMore = selectedSets.length >= 2;

  // ---- Actions ----

  const handleDelete = useCallback(async () => {
    if (!activeSet) return;
    setDeleting(true);
    try {
      await deleteGeneSet(activeSet.id);
      removeGeneSet(activeSet.id);
    } catch (err) {
      console.error("Failed to delete gene set:", err);
    } finally {
      setDeleting(false);
    }
  }, [activeSet, removeGeneSet]);

  const handleCompare = useCallback(() => {
    if (selectedSets.length !== 2) return;
    setShowCompare(true);
  }, [selectedSets]);

  const handleOverlap = useCallback(() => {
    if (selectedSets.length < 2) return;
    setShowOverlap(true);
  }, [selectedSets]);

  const handleExportTxt = useCallback(() => {
    if (!activeSet) return;
    exportAsTxt(activeSet);
    setShowExportMenu(false);
  }, [activeSet]);

  const handleExportCsv = useCallback(() => {
    if (!activeSet) return;
    exportAsCsv(activeSet);
    setShowExportMenu(false);
  }, [activeSet]);

  return (
    <aside className="flex h-full flex-col overflow-hidden">
      {/* Gene Sets section */}
      <div className="flex-1 overflow-y-auto px-3 py-4">
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Gene Sets
        </h3>

        {geneSets.length === 0 ? (
          <p className="px-1 text-xs text-muted-foreground">No gene sets loaded yet.</p>
        ) : (
          <div className="flex flex-col gap-1">
            {geneSets.map((gs) => (
              <GeneSetCard
                key={gs.id}
                geneSet={gs}
                isActive={activeSetId === gs.id}
                isSelected={selectedSetIds.includes(gs.id)}
                onActivate={() => setActiveSet(gs.id)}
                onToggleSelect={() => toggleSetSelection(gs.id)}
              />
            ))}
          </div>
        )}

        <Button
          variant="outline"
          size="sm"
          className="mt-3 w-full justify-start gap-1.5"
          onClick={() => setShowAddModal(true)}
        >
          <Plus className="h-3.5 w-3.5" />
          Add
        </Button>

        {/* Set operations — shown when exactly 2 sets are selected */}
        {hasExactlyTwo && (
          <div className="mt-3">
            <SetOperationsMenu setA={selectedSets[0]} setB={selectedSets[1]} />
          </div>
        )}
      </div>

      {/* Actions section */}
      <div className="border-t border-border px-3 py-3">
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Actions
        </h3>
        <div className="flex flex-wrap gap-1.5">
          <Button
            variant="outline"
            size="sm"
            disabled={!activeSet || deleting}
            loading={deleting}
            onClick={handleDelete}
            className="gap-1 text-xs"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </Button>

          <Button
            variant="outline"
            size="sm"
            disabled={!hasExactlyTwo}
            onClick={handleCompare}
            className="gap-1 text-xs"
          >
            <GitCompare className="h-3.5 w-3.5" />
            Compare
          </Button>

          <Button
            variant="outline"
            size="sm"
            disabled={!hasTwoOrMore}
            onClick={handleOverlap}
            className="gap-1 text-xs"
          >
            <Layers className="h-3.5 w-3.5" />
            Overlap
          </Button>

          <div ref={exportMenuRef} className="relative">
            <Button
              variant="outline"
              size="sm"
              disabled={!activeSet}
              onClick={() => setShowExportMenu((v) => !v)}
              className="gap-1 text-xs"
            >
              <Download className="h-3.5 w-3.5" />
              Export
            </Button>
            {showExportMenu && (
              <div className="absolute bottom-full left-0 mb-1 rounded-md border border-border bg-popover p-1 shadow-md z-10">
                <button
                  type="button"
                  onClick={handleExportCsv}
                  className="block w-full rounded px-3 py-1.5 text-left text-xs hover:bg-muted"
                >
                  Export as CSV
                </button>
                <button
                  type="button"
                  onClick={handleExportTxt}
                  className="block w-full rounded px-3 py-1.5 text-left text-xs hover:bg-muted"
                >
                  Export as TXT
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Saved section */}
      <div className="border-t border-border px-3 py-3">
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Saved
        </h3>
        <p className="text-xs text-muted-foreground">No saved analyses</p>
      </div>
      <AddGeneSetModal open={showAddModal} onClose={() => setShowAddModal(false)} />

      {showCompare && selectedSets.length === 2 && (
        <CompareModal
          open={showCompare}
          onClose={() => setShowCompare(false)}
          setA={selectedSets[0]}
          setB={selectedSets[1]}
        />
      )}

      {showOverlap && selectedSets.length >= 2 && (
        <OverlapModal
          open={showOverlap}
          onClose={() => setShowOverlap(false)}
          sets={selectedSets}
        />
      )}
    </aside>
  );
}

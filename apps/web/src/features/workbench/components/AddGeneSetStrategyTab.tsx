"use client";

import { useCallback, useState } from "react";
import { Database, Loader2 } from "lucide-react";
import { useSessionStore } from "@/state/useSessionStore";
import { useStrategyList } from "@/state/useStrategySelectors";
import { useWorkbenchStore } from "../store/useWorkbenchStore";
import { createGeneSetFromStrategy } from "../api/geneSets";
import { cn } from "@/lib/utils/cn";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface AddGeneSetStrategyTabProps {
  onCreated: () => void;
  onError: (message: string) => void;
}

export function AddGeneSetStrategyTab({
  onCreated,
  onError,
}: AddGeneSetStrategyTabProps) {
  const selectedSite = useSessionStore((s) => s.selectedSite);
  const addGeneSet = useWorkbenchStore((s) => s.addGeneSet);
  const { strategies } = useStrategyList();

  const [loadingStrategyId, setLoadingStrategyId] = useState<string | null>(null);

  const builtStrategies = strategies.filter((s) => s.wdkStrategyId);

  const handleImportStrategy = useCallback(
    async (strategy: (typeof strategies)[0]) => {
      if (!strategy.wdkStrategyId) return;
      setLoadingStrategyId(strategy.id);

      try {
        const geneSet = await createGeneSetFromStrategy({
          name: strategy.name || "Strategy results",
          siteId: strategy.siteId || selectedSite,
          wdkStrategyId: strategy.wdkStrategyId,
          recordType: strategy.recordType ?? undefined,
        });
        addGeneSet(geneSet);
        onCreated();
      } catch (err) {
        onError(err instanceof Error ? err.message : "Failed to import strategy.");
      } finally {
        setLoadingStrategyId(null);
      }
    },
    [selectedSite, addGeneSet, onCreated, onError],
  );

  if (builtStrategies.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-border px-4 py-8 text-center">
        <Database className="h-6 w-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">No built strategies available.</p>
        <p className="text-xs text-muted-foreground">
          Build a search strategy in Chat first, then return here to import its results.
        </p>
      </div>
    );
  }

  return (
    <div className="flex max-h-64 flex-col gap-1 overflow-y-auto">
      {builtStrategies.map((strategy) => {
        const isLoading = loadingStrategyId === strategy.id;

        return (
          <button
            key={strategy.id}
            type="button"
            onClick={() => handleImportStrategy(strategy)}
            disabled={!!loadingStrategyId}
            className={cn(
              "flex items-center gap-3 rounded-md border border-border px-3 py-2.5 text-left transition-colors",
              isLoading ? "bg-muted" : "hover:bg-muted/50 disabled:opacity-50",
            )}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
            ) : (
              <Database className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-foreground">
                {strategy.name || "Untitled strategy"}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {strategy.resultCount != null && (
                  <span>
                    {strategy.resultCount.toLocaleString()}{" "}
                    {strategy.recordType ?? "results"}
                  </span>
                )}
                {(strategy.stepCount ?? 0) > 0 && (
                  <span>
                    {strategy.stepCount} step
                    {strategy.stepCount !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

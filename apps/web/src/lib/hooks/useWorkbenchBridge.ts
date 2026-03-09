"use client";

import { useCallback } from "react";
import type { GeneSet } from "@pathfinder/shared";

/**
 * Bridge between chat events and the workbench gene-set store.
 *
 * When the backend emits a gene-set event during streaming, this hook
 * deduplicates it against existing sets and pushes it into the workbench.
 *
 * Accepts store bindings as parameters so that it lives outside any feature.
 */
export function useWorkbenchBridge(
  addGeneSet: (gs: GeneSet) => void,
  geneSets: GeneSet[],
) {
  const handleWorkbenchGeneSet = useCallback(
    (gs: {
      id: string;
      name: string;
      geneCount: number;
      source: string;
      siteId: string;
    }) => {
      if (geneSets.some((s) => s.id === gs.id)) return;
      addGeneSet({
        id: gs.id,
        name: gs.name,
        geneIds: [],
        siteId: gs.siteId,
        geneCount: gs.geneCount,
        source: gs.source as "strategy" | "paste" | "upload" | "derived" | "saved",
        createdAt: new Date().toISOString(),
      });
    },
    [addGeneSet, geneSets],
  );

  return { handleWorkbenchGeneSet };
}

import type { ChatEventContext } from "./handleChatEvent.types";
import { useWorkbenchStore } from "@/features/workbench/store";

/**
 * Handle `workbench_gene_set` events — AI created a gene set in the workbench.
 *
 * Adds the gene set to the workbench store so it appears in the sidebar
 * when the user navigates to /workbench.
 */
export function handleWorkbenchGeneSetEvent(_ctx: ChatEventContext, data: unknown) {
  const raw = data as {
    geneSet?: {
      id: string;
      name: string;
      geneCount: number;
      source: string;
      siteId: string;
    };
  };
  const gs = raw.geneSet;
  if (!gs || !gs.id) return;

  // Add to workbench store (even if not on /workbench page — Zustand is global)
  const store = useWorkbenchStore.getState();
  // Avoid duplicates
  if (store.geneSets.some((s) => s.id === gs.id)) return;

  store.addGeneSet({
    id: gs.id,
    name: gs.name,
    geneIds: [], // Gene IDs will be loaded from API when workbench mounts
    siteId: gs.siteId,
    geneCount: gs.geneCount,
    source: gs.source as "strategy" | "paste" | "upload" | "derived" | "saved",
    createdAt: new Date().toISOString(),
  });
}

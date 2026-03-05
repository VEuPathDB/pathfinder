"use client";

import { useMemo } from "react";
import { Modal } from "@/lib/components/Modal";
import type { GeneSet } from "../store";

interface OverlapModalProps {
  open: boolean;
  onClose: () => void;
  sets: GeneSet[];
}

interface PairwiseResult {
  nameA: string;
  nameB: string;
  sizeA: number;
  sizeB: number;
  shared: number;
  jaccard: number;
}

export function OverlapModal({ open, onClose, sets }: OverlapModalProps) {
  const analysis = useMemo(() => {
    // Pairwise comparisons
    const pairwise: PairwiseResult[] = [];
    for (let i = 0; i < sets.length; i++) {
      for (let j = i + 1; j < sets.length; j++) {
        const a = new Set(sets[i].geneIds);
        const b = new Set(sets[j].geneIds);
        const shared = sets[i].geneIds.filter((id) => b.has(id)).length;
        const unionSize = new Set([...sets[i].geneIds, ...sets[j].geneIds]).size;
        pairwise.push({
          nameA: sets[i].name,
          nameB: sets[j].name,
          sizeA: a.size,
          sizeB: b.size,
          shared,
          jaccard: unionSize > 0 ? shared / unionSize : 0,
        });
      }
    }

    // Universal genes (in ALL sets)
    const allSets = sets.map((s) => new Set(s.geneIds));
    const allGenes = new Set(sets.flatMap((s) => s.geneIds));
    const universal = [...allGenes].filter((g) => allSets.every((s) => s.has(g)));

    // Total unique genes
    const totalUnique = allGenes.size;

    return { pairwise, universal, totalUnique };
  }, [sets]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Gene Set Overlap"
      maxWidth="max-w-3xl"
      showCloseButton
    >
      <div className="p-5 space-y-5">
        {/* Summary */}
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-md border border-border bg-muted/50 px-3 py-2 text-center">
            <p className="text-lg font-semibold">{sets.length}</p>
            <p className="text-[11px] text-muted-foreground">Gene Sets</p>
          </div>
          <div className="rounded-md border border-border bg-muted/50 px-3 py-2 text-center">
            <p className="text-lg font-semibold">
              {analysis.totalUnique.toLocaleString()}
            </p>
            <p className="text-[11px] text-muted-foreground">Unique Genes</p>
          </div>
          <div className="rounded-md border border-border bg-muted/50 px-3 py-2 text-center">
            <p className="text-lg font-semibold">
              {analysis.universal.length.toLocaleString()}
            </p>
            <p className="text-[11px] text-muted-foreground">In All Sets</p>
          </div>
        </div>

        {/* Per-set summary */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground mb-2">Per Set</h4>
          <div className="space-y-1">
            {sets.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-md border border-border px-3 py-1.5"
              >
                <span className="text-sm font-medium truncate mr-2">{s.name}</span>
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {s.geneIds.length.toLocaleString()} genes
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Pairwise table */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground mb-2">
            Pairwise Overlap
          </h4>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                    Set A
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                    Set B
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                    Shared
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                    Jaccard
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                    Overlap %
                  </th>
                </tr>
              </thead>
              <tbody>
                {analysis.pairwise.map((p, i) => (
                  <tr key={i} className="border-b border-border last:border-0">
                    <td
                      className="px-3 py-2 font-medium truncate max-w-[120px]"
                      title={p.nameA}
                    >
                      {p.nameA}
                    </td>
                    <td
                      className="px-3 py-2 font-medium truncate max-w-[120px]"
                      title={p.nameB}
                    >
                      {p.nameB}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {p.shared.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {p.jaccard.toFixed(3)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {Math.min(p.sizeA, p.sizeB) > 0
                        ? ((p.shared / Math.min(p.sizeA, p.sizeB)) * 100).toFixed(1)
                        : "0.0"}
                      %
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Universal genes */}
        {analysis.universal.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-muted-foreground mb-2">
              Genes in All Sets ({analysis.universal.length})
            </h4>
            <div className="max-h-32 overflow-y-auto rounded-md border border-border bg-background p-2">
              <div className="flex flex-wrap gap-1">
                {analysis.universal.map((id) => (
                  <span
                    key={id}
                    className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]"
                  >
                    {id}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

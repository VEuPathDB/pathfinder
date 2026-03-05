/**
 * Gene set export utilities.
 */

import type { GeneSet } from "../store";

function downloadBlob(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function sanitizeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9_-]/g, "_");
}

/** Export gene IDs as a plain text file (one ID per line). */
export function exportAsTxt(geneSet: GeneSet) {
  const content = geneSet.geneIds.join("\n");
  downloadBlob(content, `${sanitizeFilename(geneSet.name)}_gene_ids.txt`, "text/plain");
}

/** Export gene set as CSV with metadata header. */
export function exportAsCsv(geneSet: GeneSet) {
  const rows: string[] = [];
  // Header
  rows.push("gene_id");
  // Data
  for (const id of geneSet.geneIds) {
    rows.push(id);
  }
  const content = rows.join("\n");
  downloadBlob(content, `${sanitizeFilename(geneSet.name)}_gene_ids.csv`, "text/csv");
}

/** Export multiple gene sets as a single CSV with set membership. */
export function exportMultipleAsCsv(geneSets: GeneSet[]) {
  const rows: string[] = [];
  // Header
  rows.push("gene_id,gene_set_name,source");
  // Data
  for (const gs of geneSets) {
    for (const id of gs.geneIds) {
      // Escape commas in name
      const safeName = gs.name.includes(",") ? `"${gs.name}"` : gs.name;
      rows.push(`${id},${safeName},${gs.source}`);
    }
  }
  const content = rows.join("\n");
  const filename =
    geneSets.length === 1
      ? `${sanitizeFilename(geneSets[0].name)}_gene_ids.csv`
      : `gene_sets_export.csv`;
  downloadBlob(content, filename, "text/csv");
}

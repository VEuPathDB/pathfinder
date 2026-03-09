/**
 * Zod schemas for Analysis API responses.
 *
 * All object schemas use `.passthrough()` so extra fields from the backend
 * are preserved rather than stripped.
 */
import { z } from "zod";

// ---------------------------------------------------------------------------
// Custom Enrichment
// ---------------------------------------------------------------------------

export const CustomEnrichmentResultSchema = z
  .object({
    geneSetName: z.string(),
    geneSetSize: z.number(),
    overlapCount: z.number(),
    overlapGenes: z.array(z.string()),
    backgroundSize: z.number(),
    tpCount: z.number(),
    foldEnrichment: z.number(),
    pValue: z.number(),
    oddsRatio: z.number(),
  })
  .passthrough();

/**
 * Zod schemas for Gene API responses.
 *
 * All object schemas use `.passthrough()` so extra fields from the backend
 * are preserved rather than stripped.
 */
import { z } from "zod";

// ---------------------------------------------------------------------------
// Organisms
// ---------------------------------------------------------------------------

export const OrganismListResponseSchema = z
  .object({
    organisms: z.array(z.string()),
  })
  .passthrough();

// ---------------------------------------------------------------------------
// Gene Search
// ---------------------------------------------------------------------------

export const GeneSearchResultSchema = z
  .object({
    geneId: z.string(),
    displayName: z.string(),
    organism: z.string(),
    product: z.string(),
    matchedFields: z.array(z.string()),
    geneName: z.string(),
    geneType: z.string(),
    location: z.string(),
  })
  .passthrough();

export const GeneSearchResponseSchema = z
  .object({
    results: z.array(GeneSearchResultSchema),
    totalCount: z.number(),
    suggestedOrganisms: z.array(z.string()),
  })
  .passthrough();

// ---------------------------------------------------------------------------
// Gene Resolve
// ---------------------------------------------------------------------------

export const ResolvedGeneSchema = z
  .object({
    geneId: z.string(),
    displayName: z.string(),
    organism: z.string(),
    product: z.string(),
    geneName: z.string(),
    geneType: z.string(),
    location: z.string(),
  })
  .passthrough();

export const GeneResolveResponseSchema = z
  .object({
    resolved: z.array(ResolvedGeneSchema),
    unresolved: z.array(z.string()),
  })
  .passthrough();

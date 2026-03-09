/**
 * Zod schemas for Experiment API responses.
 *
 * All object schemas use `.passthrough()` so extra fields from the backend
 * are preserved rather than stripped.
 */
import { z } from "zod";
import { DateTimeString } from "./common";

// ---------------------------------------------------------------------------
// Experiment Summary
// ---------------------------------------------------------------------------

const ExperimentStatusSchema = z.enum([
  "pending",
  "running",
  "completed",
  "error",
  "cancelled",
]);

const ExperimentModeSchema = z.enum(["single", "multi-step", "import"]);

export const ExperimentSummarySchema = z
  .object({
    id: z.string(),
    name: z.string(),
    siteId: z.string(),
    searchName: z.string(),
    recordType: z.string(),
    mode: ExperimentModeSchema.optional(),
    status: ExperimentStatusSchema,
    f1Score: z.number().nullable(),
    sensitivity: z.number().nullable(),
    specificity: z.number().nullable(),
    totalPositives: z.number(),
    totalNegatives: z.number(),
    createdAt: DateTimeString,
    batchId: z.string().nullable(),
    benchmarkId: z.string().nullable(),
    controlSetLabel: z.string().nullable(),
    isPrimaryBenchmark: z.boolean(),
  })
  .passthrough();

export const ExperimentSummaryListSchema = z.array(ExperimentSummarySchema);

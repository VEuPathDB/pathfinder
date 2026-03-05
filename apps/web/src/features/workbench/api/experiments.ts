import type { Classification, Experiment, ExperimentSummary } from "@pathfinder/shared";
import { buildUrl, requestJson } from "@/lib/api/http";

export interface RecordAttribute {
  name: string;
  displayName: string;
  help?: string | null;
  type?: string | null;
  isDisplayable?: boolean;
  isSortable?: boolean;
  isSuggested?: boolean;
}

export interface WdkRecord {
  id: { name: string; value: string }[];
  attributes: Record<string, string | null>;
  _classification?: Classification | null;
}

export interface RecordsResponse {
  records: WdkRecord[];
  meta: {
    totalCount: number;
    displayTotalCount: number;
    responseCount: number;
    pagination: { offset: number; numRecords: number };
    attributes: string[];
    tables: string[];
  };
}

export interface StrategyNode {
  stepId: number;
  primaryInput?: StrategyNode;
  secondaryInput?: StrategyNode;
}

export interface StrategyResponse {
  strategyId: number;
  name: string;
  stepTree: StrategyNode;
  steps: Record<
    string,
    {
      stepId: number;
      searchName: string;
      customName?: string;
      estimatedSize?: number;
      searchConfig?: { parameters: Record<string, string> };
    }
  >;
}

export async function listExperiments(
  siteId?: string | null,
): Promise<ExperimentSummary[]> {
  return await requestJson<ExperimentSummary[]>("/api/v1/experiments", {
    query: siteId ? { siteId } : undefined,
  });
}

export async function getExperiment(experimentId: string): Promise<Experiment> {
  return await requestJson<Experiment>(`/api/v1/experiments/${experimentId}`);
}

export async function deleteExperiment(experimentId: string): Promise<void> {
  await requestJson(`/api/v1/experiments/${experimentId}`, { method: "DELETE" });
}

export async function updateExperimentNotes(
  experimentId: string,
  notes: string,
): Promise<Experiment> {
  return await requestJson<Experiment>(`/api/v1/experiments/${experimentId}`, {
    method: "PATCH",
    body: { notes },
  });
}

export async function exportExperiment(
  experimentId: string,
  name: string,
): Promise<void> {
  const url = buildUrl(`/api/v1/experiments/${experimentId}/export`);
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) throw new Error(`Export failed: ${resp.status}`);
  const blob = await resp.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${name.replace(/\s+/g, "_").slice(0, 50)}.zip`;
  a.click();
  URL.revokeObjectURL(a.href);
}

export async function refineExperiment(
  experimentId: string,
  action: "combine" | "transform",
  config: Record<string, unknown>,
): Promise<{ success: boolean; newStepId?: number }> {
  return await requestJson(`/api/v1/experiments/${experimentId}/refine`, {
    method: "POST",
    body: { action, ...config },
  });
}

export async function reEvaluateExperiment(experimentId: string): Promise<Experiment> {
  return await requestJson<Experiment>(
    `/api/v1/experiments/${experimentId}/re-evaluate`,
    { method: "POST" },
  );
}

import { requestJsonValidated } from "./http";
import { ModelCatalogResponseSchema } from "./schemas/model";

export interface ModelCatalogResponse {
  models: import("@pathfinder/shared").ModelCatalogEntry[];
  default: string;
  defaultReasoningEffort: import("@pathfinder/shared").ReasoningEffort;
}

export async function listModels(): Promise<ModelCatalogResponse> {
  return (await requestJsonValidated(
    ModelCatalogResponseSchema,
    "/api/v1/models",
  )) as ModelCatalogResponse;
}

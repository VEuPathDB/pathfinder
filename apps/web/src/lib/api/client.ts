/**
 * Barrel re-exports for backward compatibility.
 *
 * New code should import directly from the domain module
 * (e.g. `@/lib/api/sites`, `@/lib/api/strategies`).
 */

export { APIError } from "./http";

// Sites / discovery
export {
  listSites,
  getRecordTypes,
  getSearches,
  getParamSpecs,
  validateSearchParams,
} from "./sites";

// Strategies
export {
  listStrategies,
  syncWdkStrategies,
  openStrategy,
  getStrategy,
  createStrategy,
  updateStrategy,
  deleteStrategy,
  normalizePlan,
  computeStepCounts,
} from "./strategies";

// VEuPathDB auth bridge
export {
  getVeupathdbAuthStatus,
  loginVeupathdb,
  logoutVeupathdb,
  refreshAuth,
} from "./veupathdb-auth";

// Gene search
export { searchGenes, resolveGeneIds } from "./genes";

// Models / catalog
export type { ModelCatalogResponse } from "./models";
export { listModels } from "./models";

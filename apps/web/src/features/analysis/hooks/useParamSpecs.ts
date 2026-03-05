import { useEffect, useMemo, useState } from "react";
import type { ParamSpec } from "@pathfinder/shared";
import { getParamSpecs } from "@/lib/api/sites";

export function useParamSpecs(siteId: string, recordType: string, searchName: string) {
  const [paramSpecs, setParamSpecs] = useState<ParamSpec[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!siteId || !recordType || !searchName) return;

    let active = true;

    async function load() {
      setIsLoading(true);
      try {
        const specs = await getParamSpecs(siteId, recordType, searchName);
        if (active) setParamSpecs(specs);
      } catch (err) {
        console.error("[useParamSpecs]", err);
        if (active) setParamSpecs([]);
      } finally {
        if (active) setIsLoading(false);
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [siteId, recordType, searchName]);

  const result = useMemo(() => ({ paramSpecs, isLoading }), [paramSpecs, isLoading]);

  return result;
}

"use client";

import { useEffect, useState, startTransition } from "react";
import { useDebouncedCallback } from "use-debounce";
import type { ParamSpec, Search } from "@pathfinder/shared";
import { getParamSpecs } from "@/lib/api/client";
import { normalizeRecordType } from "@/features/strategy/recordType";
import { buildContextValues } from "./stepEditorUtils";

type UseParamSpecsArgs = {
  siteId: string;
  recordType: string | null;
  searchName: string;
  selectedSearch: Search | null;
  isSearchNameAvailable: boolean;
  apiRecordTypeValue: string | null | undefined;
  resolveRecordTypeForSearch: (searchRecordType?: string | null) => string;
  contextValues?: Record<string, unknown>;
  enabled?: boolean;
};

export function useParamSpecs({
  siteId,
  recordType,
  searchName,
  selectedSearch,
  isSearchNameAvailable,
  apiRecordTypeValue,
  resolveRecordTypeForSearch,
  contextValues,
  enabled = true,
}: UseParamSpecsArgs) {
  const [paramSpecs, setParamSpecs] = useState<ParamSpec[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const debouncedFetch = useDebouncedCallback((resolvedRecordType: string) => {
    let isActive = true;
    setIsLoading(true);
    getParamSpecs(
      siteId,
      resolvedRecordType,
      searchName,
      buildContextValues(contextValues || {}),
    )
      .then((details) => {
        if (!isActive) return;
        setParamSpecs(details || []);
      })
      .catch((err) => {
        console.error("[useParamSpecs]", err);
        if (!isActive) return;
        setParamSpecs([]);
      })
      .finally(() => {
        if (!isActive) return;
        setIsLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, 250);

  useEffect(() => {
    if (!enabled) {
      startTransition(() => {
        setParamSpecs([]);
        setIsLoading(false);
      });
      return;
    }
    const preferredRecordType =
      resolveRecordTypeForSearch(selectedSearch?.recordType) ||
      apiRecordTypeValue ||
      recordType;
    if (!isSearchNameAvailable) {
      startTransition(() => {
        setParamSpecs([]);
      });
      return;
    }
    const resolvedRecordType = normalizeRecordType(preferredRecordType);
    if (!searchName || !resolvedRecordType) {
      startTransition(() => {
        setParamSpecs([]);
      });
      return;
    }
    debouncedFetch(resolvedRecordType);
  }, [
    enabled,
    siteId,
    recordType,
    searchName,
    selectedSearch,
    isSearchNameAvailable,
    apiRecordTypeValue,
    resolveRecordTypeForSearch,
    contextValues,
    debouncedFetch,
  ]);

  return { paramSpecs, isLoading };
}

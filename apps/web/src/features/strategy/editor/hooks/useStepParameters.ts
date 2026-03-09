"use client";

import { useEffect, useMemo, useState, startTransition } from "react";
import type { Search, StepKind } from "@pathfinder/shared";
import type { StepParameters } from "@/lib/strategyGraph/types";
import { usePrevious } from "@/lib/hooks/usePrevious";
import { useParamSpecs } from "@/lib/hooks/useParamSpecs";
import { extractVocabOptions, type VocabOption } from "@/lib/utils/vocab";
import { extractSpecVocabulary } from "../components/stepEditorUtils";

interface UseStepParametersArgs {
  stepId: string;
  siteId: string;
  recordType: string | null;
  kind: StepKind;
  searchName: string;
  selectedSearch: Search | null;
  isSearchNameAvailable: boolean;
  apiRecordTypeValue: string | null | undefined;
  resolveRecordTypeForSearch: (searchRecordType?: string | null) => string;
  initialParameters: StepParameters;
}

export function useStepParameters({
  stepId,
  siteId,
  recordType,
  kind,
  searchName,
  selectedSearch,
  isSearchNameAvailable,
  apiRecordTypeValue,
  resolveRecordTypeForSearch,
  initialParameters,
}: UseStepParametersArgs) {
  const [parameters, setParameters] = useState<StepParameters>(initialParameters);
  const [rawParams, setRawParams] = useState(
    JSON.stringify(initialParameters, null, 2),
  );
  const [showRaw, setShowRaw] = useState(false);

  // Dependent parameter state (currently unused placeholders).
  const dependentOptions: Record<string, VocabOption[]> = {};
  const dependentLoading: Record<string, boolean> = {};
  const dependentErrors: Record<string, string | null> = {};

  // -------------------------------------------------------------------------
  // Param specs
  // -------------------------------------------------------------------------
  const { paramSpecs, isLoading } = useParamSpecs({
    siteId,
    recordType,
    searchName,
    selectedSearch,
    isSearchNameAvailable,
    apiRecordTypeValue,
    resolveRecordTypeForSearch,
    contextValues: parameters,
    enabled: kind !== "combine",
  });

  // -------------------------------------------------------------------------
  // Reset params when spec key changes (step, record type, or search changed)
  // -------------------------------------------------------------------------
  const resolvedSpecRecordType = resolveRecordTypeForSearch(selectedSearch?.recordType);
  const specKey = `${stepId}:${resolvedSpecRecordType || ""}:${searchName || ""}`;
  const prevSpecKey = usePrevious(specKey);

  useEffect(() => {
    if (prevSpecKey === undefined) return;
    if (prevSpecKey === specKey) return;
    startTransition(() => {
      setParameters({});
      setRawParams("{}");
    });
  }, [specKey, prevSpecKey]);

  // -------------------------------------------------------------------------
  // Vocabulary options (derived from param specs)
  // -------------------------------------------------------------------------
  const vocabOptions = useMemo(() => {
    return paramSpecs.reduce<Record<string, VocabOption[]>>((acc, spec) => {
      if (!spec.name) return acc;
      const vocabulary = extractSpecVocabulary(spec);
      if (vocabulary) {
        acc[spec.name] = extractVocabOptions(vocabulary);
      }
      return acc;
    }, {});
  }, [paramSpecs]);

  return {
    parameters,
    setParameters,
    rawParams,
    setRawParams,
    showRaw,
    setShowRaw,
    paramSpecs,
    isLoading,
    vocabOptions,
    dependentOptions,
    dependentLoading,
    dependentErrors,
  };
}

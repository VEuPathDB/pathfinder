"use client";

import { useCallback, useRef, useState } from "react";
import { AlertCircle, Check, Database, FileUp, Loader2, Search } from "lucide-react";
import { Modal } from "@/lib/components/Modal";
import { Button } from "@/lib/components/ui/Button";
import { useSessionStore } from "@/state/useSessionStore";
import { useStrategyStore } from "@/state/useStrategyStore";
import {
  createGeneSet,
  createGeneSetFromStrategy,
  resolveGeneIds,
} from "../api/geneSets";
import type { ResolvedGene } from "../api/geneSets";
import { useWorkbenchStore } from "../store/useWorkbenchStore";
import { cn } from "@/lib/utils/cn";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AddGeneSetModalProps {
  open: boolean;
  onClose: () => void;
}

type Tab = "paste" | "strategy" | "upload";

const TABS: { value: Tab; label: string }[] = [
  { value: "paste", label: "Paste IDs" },
  { value: "strategy", label: "From Strategy" },
  { value: "upload", label: "Upload File" },
];

const ACCEPTED_FILE_TYPES = ".txt,.csv,.tsv";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const parseGeneIds = (text: string): string[] => {
  return text
    .split(/[\n,\t]+/)
    .map((s) => s.trim())
    .filter(Boolean);
};

const stripExtension = (filename: string): string => {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex > 0 ? filename.slice(0, dotIndex) : filename;
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function AddGeneSetModal({ open, onClose }: AddGeneSetModalProps) {
  const selectedSite = useSessionStore((s) => s.selectedSite);
  const addGeneSet = useWorkbenchStore((s) => s.addGeneSet);
  const strategies = useStrategyStore((s) => s.strategies);

  // Form state
  const [activeTab, setActiveTab] = useState<Tab>("paste");
  const [name, setName] = useState("");
  const [pasteText, setPasteText] = useState("");
  const [fileText, setFileText] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Verification state
  const [verifying, setVerifying] = useState(false);
  const [resolvedGenes, setResolvedGenes] = useState<ResolvedGene[] | null>(null);
  const [unresolvedIds, setUnresolvedIds] = useState<string[]>([]);
  const [verified, setVerified] = useState(false);

  // Strategy loading state
  const [loadingStrategyId, setLoadingStrategyId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Derived
  const rawText = activeTab === "paste" ? pasteText : fileText;
  const parsedIds = parseGeneIds(rawText);
  const detectedCount = parsedIds.length;

  const resetForm = useCallback(() => {
    setActiveTab("paste");
    setName("");
    setPasteText("");
    setFileText("");
    setFileName(null);
    setError(null);
    setIsSubmitting(false);
    setVerifying(false);
    setResolvedGenes(null);
    setUnresolvedIds([]);
    setVerified(false);
    setLoadingStrategyId(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  const handleClose = useCallback(() => {
    if (isSubmitting || loadingStrategyId) return;
    resetForm();
    onClose();
  }, [isSubmitting, loadingStrategyId, resetForm, onClose]);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      setError(null);
      setVerified(false);
      setResolvedGenes(null);
      setUnresolvedIds([]);
      const reader = new FileReader();
      reader.onload = () => {
        const text = reader.result as string;
        setFileText(text);
        setFileName(file.name);
        if (!name) {
          setName(stripExtension(file.name));
        }
      };
      reader.onerror = () => {
        setError("Failed to read file. Please try again.");
      };
      reader.readAsText(file);
    },
    [name],
  );

  // Reset verification when paste text changes
  const handlePasteChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setPasteText(e.target.value);
    setVerified(false);
    setResolvedGenes(null);
    setUnresolvedIds([]);
    setError(null);
  }, []);

  // ---- Verify gene IDs ----

  const handleVerify = useCallback(async () => {
    if (parsedIds.length === 0) return;
    setVerifying(true);
    setError(null);

    try {
      const result = await resolveGeneIds(selectedSite, parsedIds);
      setResolvedGenes(result.resolved);
      setUnresolvedIds(result.unresolved);
      setVerified(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to verify gene IDs.");
    } finally {
      setVerifying(false);
    }
  }, [parsedIds, selectedSite]);

  // ---- Submit (paste/upload) ----

  const handleSubmit = useCallback(async () => {
    setError(null);

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Please enter a name for the gene set.");
      return;
    }

    // Use resolved IDs if verified, otherwise use parsed IDs
    const idsToSubmit =
      verified && resolvedGenes ? resolvedGenes.map((g) => g.geneId) : parsedIds;

    if (idsToSubmit.length === 0) {
      setError("No valid gene IDs to add.");
      return;
    }

    setIsSubmitting(true);
    try {
      const geneSet = await createGeneSet({
        name: trimmedName,
        source: activeTab === "upload" ? "upload" : "paste",
        geneIds: idsToSubmit,
        siteId: selectedSite,
      });
      addGeneSet(geneSet);
      resetForm();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create gene set.");
    } finally {
      setIsSubmitting(false);
    }
  }, [
    name,
    parsedIds,
    selectedSite,
    activeTab,
    verified,
    resolvedGenes,
    addGeneSet,
    resetForm,
    onClose,
  ]);

  // ---- Import from strategy ----

  const handleImportStrategy = useCallback(
    async (strategy: (typeof strategies)[0]) => {
      if (!strategy.wdkStrategyId) return;
      setLoadingStrategyId(strategy.id);
      setError(null);

      try {
        // Backend resolves root step and fetches gene IDs from wdkStrategyId
        const geneSet = await createGeneSetFromStrategy({
          name: strategy.name || "Strategy results",
          siteId: strategy.siteId || selectedSite,
          wdkStrategyId: strategy.wdkStrategyId,
          recordType: strategy.recordType ?? undefined,
        });
        addGeneSet(geneSet);
        resetForm();
        onClose();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to import strategy.");
      } finally {
        setLoadingStrategyId(null);
      }
    },
    [selectedSite, addGeneSet, resetForm, onClose],
  );

  // Filter to strategies that have been built on WDK
  const builtStrategies = strategies.filter((s) => s.wdkStrategyId);

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Add Gene Set"
      maxWidth="max-w-lg"
      showCloseButton
    >
      <div className="p-5">
        {/* ---- Header ---- */}
        <h2 className="text-base font-semibold text-foreground">Add Gene Set</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Import a list of gene IDs to analyse in the workbench.
        </p>

        {/* ---- Tab switcher ---- */}
        <div className="mt-4 flex rounded-lg bg-muted p-1">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => {
                setActiveTab(tab.value);
                setError(null);
              }}
              className={cn(
                "flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors duration-150",
                activeTab === tab.value
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ---- Tab content ---- */}
        <div className="mt-4">
          {/* ==================== PASTE TAB ==================== */}
          {(activeTab === "paste" || activeTab === "upload") && (
            <>
              {/* Name input */}
              <div>
                <label
                  htmlFor="gene-set-name"
                  className="block text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                >
                  Name
                </label>
                <input
                  id="gene-set-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. My upregulated genes"
                  disabled={isSubmitting}
                  className="mt-1.5 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                />
              </div>

              <div className="mt-4">
                {activeTab === "paste" && (
                  <div>
                    <label
                      htmlFor="gene-ids-paste"
                      className="block text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                    >
                      Gene IDs
                    </label>
                    <textarea
                      id="gene-ids-paste"
                      value={pasteText}
                      onChange={handlePasteChange}
                      placeholder="Paste gene IDs separated by newlines, commas, or tabs"
                      rows={5}
                      disabled={isSubmitting}
                      className="mt-1.5 w-full resize-none rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                    />
                  </div>
                )}

                {activeTab === "upload" && (
                  <div>
                    <label
                      htmlFor="gene-ids-upload"
                      className="block text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                    >
                      Upload File
                    </label>
                    <div className="mt-1.5">
                      <label
                        htmlFor="gene-ids-upload"
                        className={cn(
                          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed border-border px-4 py-6 transition-colors hover:border-ring hover:bg-muted/50",
                          isSubmitting && "pointer-events-none opacity-50",
                        )}
                      >
                        <FileUp className="h-6 w-6 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
                          {fileName ?? "Choose a .txt, .csv, or .tsv file"}
                        </span>
                        <input
                          ref={fileInputRef}
                          id="gene-ids-upload"
                          type="file"
                          accept={ACCEPTED_FILE_TYPES}
                          onChange={handleFileChange}
                          disabled={isSubmitting}
                          className="sr-only"
                        />
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Detection + verify row */}
              {detectedCount > 0 && (
                <div className="mt-3 flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    {detectedCount} gene{detectedCount !== 1 ? "s" : ""} detected
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleVerify}
                    loading={verifying}
                    disabled={verifying || isSubmitting}
                    className="gap-1 text-xs"
                  >
                    <Search className="h-3 w-3" />
                    Verify IDs
                  </Button>
                </div>
              )}

              {/* Verification results */}
              {verified && resolvedGenes !== null && (
                <div className="mt-3 rounded-md border border-border bg-muted/30 p-3">
                  <div className="flex items-center gap-4 text-xs">
                    {resolvedGenes.length > 0 && (
                      <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                        <Check className="h-3 w-3" />
                        {resolvedGenes.length} valid
                      </span>
                    )}
                    {unresolvedIds.length > 0 && (
                      <span className="flex items-center gap-1 text-destructive">
                        <AlertCircle className="h-3 w-3" />
                        {unresolvedIds.length} not found
                      </span>
                    )}
                  </div>

                  {/* Resolved gene details (compact) */}
                  {resolvedGenes.length > 0 && (
                    <div className="mt-2 max-h-32 overflow-y-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-left text-muted-foreground">
                            <th className="pb-1 pr-2 font-medium">ID</th>
                            <th className="pb-1 pr-2 font-medium">Product</th>
                            <th className="pb-1 font-medium">Organism</th>
                          </tr>
                        </thead>
                        <tbody>
                          {resolvedGenes.slice(0, 20).map((g) => (
                            <tr key={g.geneId} className="text-foreground">
                              <td className="py-0.5 pr-2 font-mono">{g.geneId}</td>
                              <td className="truncate py-0.5 pr-2 max-w-[150px]">
                                {g.product || "—"}
                              </td>
                              <td className="truncate py-0.5 italic max-w-[120px]">
                                {g.organism || "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {resolvedGenes.length > 20 && (
                        <p className="mt-1 text-muted-foreground">
                          … and {resolvedGenes.length - 20} more
                        </p>
                      )}
                    </div>
                  )}

                  {/* Unresolved IDs */}
                  {unresolvedIds.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-medium text-destructive">Not found:</p>
                      <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                        {unresolvedIds.slice(0, 10).join(", ")}
                        {unresolvedIds.length > 10 &&
                          ` … +${unresolvedIds.length - 10} more`}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* ==================== STRATEGY TAB ==================== */}
          {activeTab === "strategy" && (
            <div>
              {builtStrategies.length === 0 ? (
                <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-border px-4 py-8 text-center">
                  <Database className="h-6 w-6 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    No built strategies available.
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Build a search strategy in Chat first, then return here to import
                    its results.
                  </p>
                </div>
              ) : (
                <div className="flex max-h-64 flex-col gap-1 overflow-y-auto">
                  {builtStrategies.map((strategy) => {
                    const isLoading = loadingStrategyId === strategy.id;

                    return (
                      <button
                        key={strategy.id}
                        type="button"
                        onClick={() => handleImportStrategy(strategy)}
                        disabled={!!loadingStrategyId}
                        className={cn(
                          "flex items-center gap-3 rounded-md border border-border px-3 py-2.5 text-left transition-colors",
                          isLoading
                            ? "bg-muted"
                            : "hover:bg-muted/50 disabled:opacity-50",
                        )}
                      >
                        {isLoading ? (
                          <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
                        ) : (
                          <Database className="h-4 w-4 shrink-0 text-muted-foreground" />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-medium text-foreground">
                            {strategy.name || "Untitled strategy"}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            {strategy.resultCount != null && (
                              <span>
                                {strategy.resultCount.toLocaleString()}{" "}
                                {strategy.recordType ?? "results"}
                              </span>
                            )}
                            {(strategy.stepCount ?? 0) > 0 && (
                              <span>
                                {strategy.stepCount} step
                                {strategy.stepCount !== 1 ? "s" : ""}
                              </span>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ---- Error ---- */}
        {error && (
          <p className="mt-3 text-xs text-destructive" role="alert">
            {error}
          </p>
        )}

        {/* ---- Actions (paste/upload only) ---- */}
        {activeTab !== "strategy" && (
          <div className="mt-5 flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleSubmit}
              loading={isSubmitting}
              disabled={detectedCount === 0}
            >
              {verified && resolvedGenes
                ? `Add ${resolvedGenes.length} Gene${resolvedGenes.length !== 1 ? "s" : ""}`
                : "Add Gene Set"}
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}

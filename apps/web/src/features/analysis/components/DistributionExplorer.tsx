import { useState, useEffect, useCallback } from "react";
import { BarChart3, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { Modal } from "@/lib/components/Modal";
import type { RecordAttribute, WdkRecord } from "@/features/workbench/api";
import {
  getAttributes,
  getDistribution,
  getRecords,
  type EntityRef,
} from "@/features/analysis/api/stepResults";

interface DistributionExplorerProps {
  entityRef: EntityRef;
}

interface DistributionEntry {
  value: string;
  count: number;
}

interface ColumnHistogramBin {
  value: number;
  binStart: string;
  binEnd: string;
  binLabel: string;
}

function parseDistribution(raw: Record<string, unknown>): DistributionEntry[] {
  if (Array.isArray(raw.histogram)) {
    return (raw.histogram as ColumnHistogramBin[])
      .filter((bin) => bin.value > 0)
      .map((bin) => ({
        value: bin.binLabel || bin.binStart || "",
        count: bin.value,
      }))
      .sort((a, b) => b.count - a.count);
  }

  const histogram = (raw.distribution ?? raw) as Record<string, unknown>;
  return Object.entries(histogram)
    .filter(([key]) => key !== "total" && key !== "attributeName")
    .map(([value, count]) => ({ value, count: Number(count) || 0 }))
    .sort((a, b) => b.count - a.count);
}

// ---- Attribute filtering ----
// WDK gene records have 100+ attributes. Most are visualization URLs, genome
// browser links, graph images, or internal fields. We use VEuPathDB's own
// naming conventions to identify non-distributable columns.

/** Exact attribute names to exclude. */
const BLOCKED_NAMES = new Set([
  "primary_key",
  "project",
  "dataset_id",
  "start_min_text",
  "end_max_text",
  "gff_seqid",
  "gff_fstart",
  "gff_fend",
]);

/** Substrings anywhere in the name that indicate non-distributable columns. */
const BLOCKED_SUBSTRINGS = [
  "url",
  "jbrowse",
  "gbrowse",
  "pbrowse",
  "browse",
  "apollo",
  "gtracks",
  "overview",
  "highlight",
  "context_start",
  "context_end",
  "zoom_context",
  "_rsrc_",
  "expr_graph",
  "pct_graph",
];

/** Prefixes that indicate internal or non-distributable columns. */
const BLOCKED_PREFIXES = ["wdk_", "j_", "lc_", "link"];

/** Suffixes that indicate non-distributable columns. */
const BLOCKED_SUFFIXES = [
  "link",
  "_graph",
  "_img",
  "_filename",
  "_help",
  "_warn",
  "_warning",
  "_prefix",
  "_partial",
];

/** Pattern for RNA-seq sample columns (pan_NNNN). */
const SAMPLE_COLUMN_RE = /^pan_\d+$/;

function isDistributableAttr(a: RecordAttribute): boolean {
  if (a.isDisplayable === false || a.type === "link") return false;

  const n = a.name.toLowerCase();

  if (BLOCKED_NAMES.has(n)) return false;
  if (BLOCKED_SUBSTRINGS.some((s) => n.includes(s))) return false;
  if (BLOCKED_PREFIXES.some((p) => n.startsWith(p))) return false;
  if (BLOCKED_SUFFIXES.some((s) => n.endsWith(s))) return false;
  if (SAMPLE_COLUMN_RE.test(n)) return false;

  return true;
}

// ---- Component ----

export function DistributionExplorer({ entityRef }: DistributionExplorerProps) {
  const [attributes, setAttributes] = useState<RecordAttribute[]>([]);
  const [selectedAttr, setSelectedAttr] = useState<string>("");
  const [distribution, setDistribution] = useState<DistributionEntry[]>([]);
  const [loadingAttrs, setLoadingAttrs] = useState(true);
  const [loadingDist, setLoadingDist] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalValue, setModalValue] = useState<string | null>(null);
  const [modalRecords, setModalRecords] = useState<WdkRecord[]>([]);
  const [loadingModal, setLoadingModal] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoadingAttrs(true);
    setError(null);

    getAttributes(entityRef)
      .then(({ attributes: attrs }) => {
        if (cancelled) return;
        const displayable = attrs.filter(isDistributableAttr);
        setAttributes(displayable);
        if (displayable.length > 0 && !selectedAttr) {
          setSelectedAttr(displayable[0].name);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoadingAttrs(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityRef.id, entityRef.type]);

  const fetchDistribution = useCallback(
    (attrName: string) => {
      if (!attrName) return;
      setLoadingDist(true);
      setError(null);

      getDistribution(entityRef, attrName)
        .then((raw) => {
          const entries = parseDistribution(raw);
          if (entries.length === 0) {
            setError(
              "No distribution data available for this attribute. Try a different one.",
            );
            setDistribution([]);
          } else {
            setDistribution(entries);
          }
        })
        .catch((err) => {
          const msg = err instanceof Error ? err.message : String(err);
          if (msg.includes("422") || msg.includes("404") || msg.includes("not found")) {
            setError(
              "No distribution data available for this attribute. Try a different one.",
            );
          } else {
            setError(msg);
          }
        })
        .finally(() => setLoadingDist(false));
    },
    [entityRef],
  );

  useEffect(() => {
    if (selectedAttr) fetchDistribution(selectedAttr);
  }, [selectedAttr, fetchDistribution]);

  const handleBarClick = useCallback(
    async (value: string) => {
      setModalValue(value);
      setModalRecords([]);
      setLoadingModal(true);

      try {
        // Gene-set endpoint supports server-side filtering.
        // For experiments, fetch all and filter client-side.
        if (entityRef.type === "gene-set") {
          const { records } = await getRecords(entityRef, {
            attributes: [selectedAttr, "gene_product"],
            filterAttribute: selectedAttr,
            filterValue: value,
            limit: 500,
          });
          setModalRecords(records);
        } else {
          const { meta } = await getRecords(entityRef, {
            attributes: [selectedAttr, "gene_product"],
            limit: 1,
          });
          const total = meta.totalCount || meta.displayTotalCount || 5000;

          const { records } = await getRecords(entityRef, {
            attributes: [selectedAttr, "gene_product"],
            limit: total,
          });

          const filtered = records.filter((r) => r.attributes[selectedAttr] === value);
          setModalRecords(filtered);
        }
      } catch {
        setModalRecords([]);
      } finally {
        setLoadingModal(false);
      }
    },
    [entityRef, selectedAttr],
  );

  const maxCount = Math.max(1, ...distribution.map((d) => d.count));
  const topEntries = distribution.slice(0, 20);

  if (loadingAttrs) {
    return (
      <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading attributes…
      </div>
    );
  }

  if (error && attributes.length === 0) {
    return (
      <div className="flex items-center gap-2 py-8 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        {error}
      </div>
    );
  }

  if (attributes.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No attributes with distribution data found.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-center gap-2">
        <BarChart3 className="h-4 w-4 text-muted-foreground" />
        <select
          value={selectedAttr}
          onChange={(e) => setSelectedAttr(e.target.value)}
          className="h-8 rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {attributes.map((attr) => (
            <option key={attr.name} value={attr.name}>
              {attr.displayName}
            </option>
          ))}
        </select>
        <button
          onClick={() => fetchDistribution(selectedAttr)}
          disabled={loadingDist}
          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
          title="Refresh"
        >
          {loadingDist ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs text-destructive">
          <AlertCircle className="h-3.5 w-3.5" />
          {error}
        </div>
      )}

      {loadingDist ? (
        <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading distribution…
        </div>
      ) : topEntries.length === 0 ? (
        <div className="py-6 text-center text-xs text-muted-foreground">
          No distribution data available for this attribute.
        </div>
      ) : (
        <div className="space-y-1.5">
          {topEntries.map(({ value, count }) => {
            const pct = (count / maxCount) * 100;
            return (
              <div
                key={value}
                className="group flex cursor-pointer items-center gap-3"
                onClick={() => handleBarClick(value)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleBarClick(value);
                  }
                }}
              >
                <span
                  className="w-28 shrink-0 truncate text-right text-xs text-muted-foreground"
                  title={value}
                >
                  {value || "(empty)"}
                </span>
                <div className="relative h-5 flex-1 overflow-hidden rounded bg-muted/40">
                  <div
                    className="absolute inset-y-0 left-0 rounded bg-primary/20 transition-all duration-300 group-hover:bg-primary/30"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-14 shrink-0 text-right font-mono text-xs tabular-nums text-foreground">
                  {count.toLocaleString()}
                </span>
              </div>
            );
          })}
          {distribution.length > 20 && (
            <p className="pt-1 text-right text-xs text-muted-foreground">
              Showing top 20 of {distribution.length} values
            </p>
          )}
        </div>
      )}

      <Modal
        open={modalValue !== null}
        onClose={() => setModalValue(null)}
        title={`Genes: ${selectedAttr} = ${modalValue}`}
        maxWidth="max-w-2xl"
        showCloseButton
      >
        <div className="p-4">
          <h3 className="mb-3 text-sm font-medium text-foreground">
            {attributes.find((a) => a.name === selectedAttr)?.displayName ??
              selectedAttr}{" "}
            = &ldquo;{modalValue}&rdquo;
          </h3>

          {loadingModal ? (
            <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading genes…
            </div>
          ) : modalRecords.length === 0 ? (
            <p className="py-6 text-center text-xs text-muted-foreground">
              No matching genes found.
            </p>
          ) : (
            (() => {
              const hasClassifications = modalRecords.some(
                (r) => r._classification != null,
              );
              return (
                <div className="max-h-80 overflow-auto rounded border border-border">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-muted text-left">
                      <tr>
                        <th className="px-3 py-1.5 font-medium">Gene ID</th>
                        <th className="px-3 py-1.5 font-medium">Product</th>
                        {hasClassifications && (
                          <th className="px-3 py-1.5 font-medium">Class</th>
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {modalRecords.map((rec) => {
                        const rawId =
                          rec.id.find((k) => k.name === "gene_source_id")?.value ??
                          rec.id[0]?.value ??
                          "\u2014";
                        return (
                          <tr key={rawId} className="hover:bg-muted/40">
                            <td className="px-3 py-1.5 font-mono">{rawId}</td>
                            <td
                              className="max-w-xs truncate px-3 py-1.5"
                              title={rec.attributes.gene_product ?? ""}
                            >
                              {rec.attributes.gene_product ?? "\u2014"}
                            </td>
                            {hasClassifications && (
                              <td className="px-3 py-1.5">
                                {rec._classification ?? "\u2014"}
                              </td>
                            )}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              );
            })()
          )}

          {!loadingModal && modalRecords.length > 0 && (
            <p className="mt-2 text-right text-xs text-muted-foreground">
              {modalRecords.length} gene{modalRecords.length !== 1 && "s"}
            </p>
          )}
        </div>
      </Modal>
    </div>
  );
}

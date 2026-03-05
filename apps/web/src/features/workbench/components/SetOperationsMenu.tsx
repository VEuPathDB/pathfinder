"use client";

/**
 * SetOperationsMenu — shown when exactly 2 gene sets are selected.
 *
 * Provides intersect (A n B), union (A u B), and minus (A - B) operations.
 * Calls the backend set operation endpoint, then adds the derived set to the store.
 */

import { useCallback, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/lib/components/ui/Button";
import { performSetOperation } from "../api/geneSets";
import { useWorkbenchStore } from "../store";
import type { GeneSet } from "../store";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Operation = "intersect" | "union" | "minus";

const OP_LABELS: Record<Operation, { symbol: string; label: string }> = {
  intersect: { symbol: "\u2229", label: "Intersect" },
  union: { symbol: "\u222A", label: "Union" },
  minus: { symbol: "\u2212", label: "Minus" },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SetOperationsMenuProps {
  setA: GeneSet;
  setB: GeneSet;
}

export function SetOperationsMenu({ setA, setB }: SetOperationsMenuProps) {
  const addGeneSet = useWorkbenchStore((s) => s.addGeneSet);
  const clearSelection = useWorkbenchStore((s) => s.clearSelection);
  const [loading, setLoading] = useState<Operation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleOperation = useCallback(
    async (operation: Operation) => {
      setError(null);
      setLoading(operation);
      const { symbol } = OP_LABELS[operation];
      const name = `${setA.name} ${symbol} ${setB.name}`;

      try {
        const result = await performSetOperation({
          operation,
          setAId: setA.id,
          setBId: setB.id,
          name,
        });
        addGeneSet(result);
        clearSelection();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Set operation failed.");
      } finally {
        setLoading(null);
      }
    },
    [setA, setB, addGeneSet, clearSelection],
  );

  const isDisabled = loading !== null;

  return (
    <div className="rounded-md border border-border bg-muted/50 px-3 py-2.5">
      <p className="mb-2 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">{setA.name}</span>
        {" & "}
        <span className="font-medium text-foreground">{setB.name}</span>
      </p>

      <div className="flex gap-1.5">
        {(
          Object.entries(OP_LABELS) as [Operation, (typeof OP_LABELS)[Operation]][]
        ).map(([op, { symbol, label }]) => (
          <Button
            key={op}
            variant="outline"
            size="sm"
            disabled={isDisabled}
            onClick={() => handleOperation(op)}
            className="flex-1 gap-1 text-xs"
          >
            {loading === op ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <span className="font-semibold">{symbol}</span>
            )}
            {label}
          </Button>
        ))}
      </div>

      {error && (
        <p className="mt-2 text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

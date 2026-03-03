import { useEffect, useState } from "react";
import type { ExperimentSummary } from "@pathfinder/shared";
import { useExperimentViewStore } from "../store";
import { Button } from "@/lib/components/ui/Button";
import { Input } from "@/lib/components/ui/Input";
import { Badge } from "@/lib/components/ui/Badge";
import { ScrollArea } from "@/lib/components/ui/ScrollArea";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/lib/components/ui/Tooltip";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/lib/components/ui/AlertDialog";
import { cn } from "@/lib/utils/cn";
import {
  Plus,
  Search,
  Trash2,
  FlaskConical,
  Clock,
  Copy,
  Layers,
  BarChart3,
} from "lucide-react";

function pct(v: number | null | undefined): string {
  if (v == null) return "--";
  return `${(v * 100).toFixed(1)}%`;
}

function statusVariant(status: string) {
  switch (status) {
    case "completed":
      return "success" as const;
    case "running":
      return "default" as const;
    case "error":
      return "destructive" as const;
    default:
      return "secondary" as const;
  }
}

interface ExperimentListProps {
  siteId: string;
}

export function ExperimentList({ siteId }: ExperimentListProps) {
  const {
    experiments,
    fetchExperiments,
    loadExperiment,
    deleteExperiment,
    cloneExperiment,
    setView,
  } = useExperimentViewStore();
  const [search, setSearch] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<ExperimentSummary | null>(null);

  useEffect(() => {
    fetchExperiments(siteId);
  }, [siteId, fetchExperiments]);

  const filtered = experiments.filter(
    (e) =>
      !search ||
      e.name.toLowerCase().includes(search.toLowerCase()) ||
      e.searchName.toLowerCase().includes(search.toLowerCase()),
  );

  const completedCount = experiments.filter((e) => e.status === "completed").length;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header: New Experiment + group actions in one row */}
      <div className="border-b border-border p-3">
        <div className="flex items-center gap-1.5">
          <Button className="flex-1" size="sm" onClick={() => setView("mode-select")}>
            <Plus className="h-3.5 w-3.5" />
            New Experiment
          </Button>
          {completedCount >= 2 && (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0 px-2"
                    onClick={() => setView("overlap")}
                  >
                    <Layers className="h-3.5 w-3.5" />
                    <span className="hidden lg:inline">Overlap</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Compare result overlap</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0 px-2"
                    onClick={() => setView("enrichment-compare")}
                  >
                    <BarChart3 className="h-3.5 w-3.5" />
                    <span className="hidden lg:inline">Enrichment</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Compare enrichment</TooltipContent>
              </Tooltip>
            </>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="border-b border-border px-3 py-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search experiments..."
            className="pl-8"
          />
        </div>
      </div>

      {/* Experiment list */}
      <ScrollArea className="flex-1 [&>[data-radix-scroll-area-viewport]>div]:!block">
        {filtered.length === 0 ? (
          <div className="px-4 py-8 text-center animate-fade-in">
            <FlaskConical className="mx-auto h-8 w-8 text-muted-foreground/40" />
            <p className="mt-2 text-sm text-muted-foreground">
              {experiments.length === 0
                ? "No experiments yet. Create one to get started."
                : "No experiments match your search."}
            </p>
          </div>
        ) : (
          <div className="space-y-0.5 p-1.5">
            {filtered.map((exp) => (
              <ExperimentCard
                key={exp.id}
                experiment={exp}
                onSelect={() => loadExperiment(exp.id)}
                onDelete={() => setDeleteTarget(exp)}
                onClone={() => cloneExperiment(exp.id)}
              />
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Delete confirmation dialog */}
      <AlertDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete experiment?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete{" "}
              <span className="font-medium text-foreground">{deleteTarget?.name}</span>.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (deleteTarget) {
                  deleteExperiment(deleteTarget.id);
                  setDeleteTarget(null);
                }
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function ExperimentCard({
  experiment: exp,
  onSelect,
  onDelete,
  onClone,
}: {
  experiment: ExperimentSummary;
  onSelect: () => void;
  onDelete: () => void;
  onClone: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter") onSelect();
      }}
      className="group relative flex w-full flex-col gap-1 overflow-hidden rounded-lg px-3 py-2.5 text-left transition-all duration-150 hover:bg-accent"
    >
      <div className="flex min-w-0 items-start justify-between gap-2">
        <span className="min-w-0 truncate text-sm font-medium text-foreground">
          {exp.name}
        </span>
        <div className="flex shrink-0 items-center gap-1">
          <div className="hidden gap-0.5 group-hover:flex">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onClone();
              }}
              className="rounded-md p-1 text-muted-foreground transition-colors duration-150 hover:bg-primary/10 hover:text-primary"
              title="Clone experiment"
            >
              <Copy className="h-3 w-3" />
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="rounded-md p-1 text-muted-foreground transition-colors duration-150 hover:bg-destructive/10 hover:text-destructive"
              title="Delete experiment"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
          <Badge variant={statusVariant(exp.status)} className="shrink-0 text-xs">
            {exp.status}
          </Badge>
        </div>
      </div>
      <div className="min-w-0 truncate text-xs font-mono text-muted-foreground">
        {exp.searchName}
      </div>
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        {exp.f1Score != null && (
          <span>
            F1:{" "}
            <span className="font-mono font-medium text-foreground">
              {pct(exp.f1Score)}
            </span>
          </span>
        )}
        {exp.sensitivity != null && (
          <span>
            Sens:{" "}
            <span className="font-mono font-medium text-foreground">
              {pct(exp.sensitivity)}
            </span>
          </span>
        )}
        <span className="ml-auto flex shrink-0 items-center gap-1">
          <Clock className="h-3 w-3" />
          {new Date(exp.createdAt).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
}

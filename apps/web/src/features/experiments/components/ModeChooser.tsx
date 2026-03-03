import { ArrowLeft, FlaskConical, GitBranch } from "lucide-react";
import { Button } from "@/lib/components/ui/Button";
import { useExperimentViewStore } from "../store";

const MODES = [
  {
    id: "single" as const,
    title: "Single Search",
    description:
      "Pick one search, tune its parameters, and evaluate with controls. Best for focused hypothesis testing.",
    icon: FlaskConical,
    view: "setup" as const,
  },
  {
    id: "strategy-builder" as const,
    title: "Strategy Builder",
    description:
      "Build a multi-step strategy graph from scratch or import an existing VEuPathDB strategy. Evaluate and optimize across steps.",
    icon: GitBranch,
    view: "multi-step-setup" as const,
  },
] as const;

export function ModeChooser() {
  const setView = useExperimentViewStore((s) => s.setView);

  return (
    <div className="flex h-full flex-col items-center justify-center p-8">
      <h2 className="mb-2 text-xl font-semibold text-foreground">New Experiment</h2>
      <p className="mb-8 max-w-md text-center text-sm text-muted-foreground">
        Choose how you want to set up your experiment. Each mode offers different levels
        of control over your search strategy.
      </p>

      <div className="grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-2">
        {MODES.map((mode) => (
          <button
            key={mode.id}
            data-testid={`mode-${mode.id}`}
            onClick={() => setView(mode.view)}
            className="group flex flex-col items-start gap-3 rounded-xl border border-border bg-card p-6 text-left transition-all hover:border-primary/40 hover:shadow-md"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary/20">
              <mode.icon className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">{mode.title}</h3>
            <p className="text-xs leading-relaxed text-muted-foreground">
              {mode.description}
            </p>
          </button>
        ))}
      </div>

      <Button
        variant="ghost"
        size="sm"
        className="mt-8"
        onClick={() => setView("list")}
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to list
      </Button>
    </div>
  );
}

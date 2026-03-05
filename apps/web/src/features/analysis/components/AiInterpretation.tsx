import { useState, useRef, useCallback } from "react";
import type { Experiment } from "@pathfinder/shared";
import { streamAiAssist } from "@/features/workbench/api";
import { ChatMarkdown } from "@/features/chat/components/message/ChatMarkdown";
import { Sparkles, Loader2 } from "lucide-react";
import { Section } from "./Section";
import { flattenPlanStepNode } from "@/features/analysis/utils/multiStepUtils";

interface AiInterpretationProps {
  experiment: Experiment;
  siteId: string;
}

export function AiInterpretation({ experiment, siteId }: AiInterpretationProps) {
  const [response, setResponse] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const interpret = useCallback(() => {
    if (streaming) return;

    abortRef.current?.abort();
    setStreaming(true);
    setResponse("");
    setHasRun(true);

    const m = experiment.metrics;
    const cm = m?.confusionMatrix;
    const enrichSummary = (experiment.enrichmentResults ?? [])
      .map((er) => {
        const top = er.terms
          .filter((t) => t.pValue < 0.05)
          .slice(0, 5)
          .map(
            (t) =>
              `${t.termName} (p=${t.pValue.toExponential(2)}, fold=${t.foldEnrichment.toFixed(1)})`,
          )
          .join("; ");
        return `${er.analysisType}: ${top || "no significant terms"}`;
      })
      .join("\n");

    const config = experiment.config;
    const stepTree = config.stepTree;
    const strategySummary =
      stepTree && config.recordType
        ? flattenPlanStepNode(stepTree, config.recordType)
            .map((s) => s.searchName)
            .join(" \u2192 ")
        : `Single search: ${config.searchName}`;

    const sampleGenes = (ids: string[], names: (string | null | undefined)[]) =>
      ids
        .slice(0, 10)
        .map((id, i) => `${id}${names[i] ? ` (${names[i]})` : ""}`)
        .join(", ");

    const geneListsParts: string[] = [];
    if (experiment.truePositiveGenes?.length) {
      geneListsParts.push(
        `True positives (${experiment.truePositiveGenes.length}): ${sampleGenes(
          experiment.truePositiveGenes.map((g) => g.id),
          experiment.truePositiveGenes.map((g) => g.name),
        )}`,
      );
    }
    if (experiment.falsePositiveGenes?.length) {
      geneListsParts.push(
        `False positives (${experiment.falsePositiveGenes.length}): ${sampleGenes(
          experiment.falsePositiveGenes.map((g) => g.id),
          experiment.falsePositiveGenes.map((g) => g.name),
        )}`,
      );
    }
    if (experiment.falseNegativeGenes?.length) {
      geneListsParts.push(
        `False negatives (${experiment.falseNegativeGenes.length}): ${sampleGenes(
          experiment.falseNegativeGenes.map((g) => g.id),
          experiment.falseNegativeGenes.map((g) => g.name),
        )}`,
      );
    }
    const geneListsSummary = geneListsParts.length > 0 ? geneListsParts.join("\n") : "";

    const context: Record<string, unknown> = {
      experimentId: experiment.id,
      searchName: config.searchName,
      recordType: config.recordType,
      mode: config.mode ?? "single",
      strategySummary,
      parameters: config.parameterDisplayValues ?? config.parameters,
      positiveControls: config.positiveControls.slice(0, 20),
      negativeControls: config.negativeControls.slice(0, 20),
    };

    if (geneListsSummary) {
      context.geneListsSummary = geneListsSummary;
    }

    if (m) {
      context.metrics = {
        sensitivity: m.sensitivity,
        specificity: m.specificity,
        precision: m.precision,
        f1Score: m.f1Score,
        mcc: m.mcc,
        balancedAccuracy: m.balancedAccuracy,
        totalResults: m.totalResults,
      };
    }
    if (cm) {
      context.confusionMatrix = {
        TP: cm.truePositives,
        FP: cm.falsePositives,
        FN: cm.falseNegatives,
        TN: cm.trueNegatives,
      };
    }
    if (enrichSummary) {
      context.enrichmentSummary = enrichSummary;
    }
    if (experiment.crossValidation) {
      context.crossValidation = {
        overfittingLevel: experiment.crossValidation.overfittingLevel,
        overfittingScore: experiment.crossValidation.overfittingScore,
        meanF1: experiment.crossValidation.meanMetrics.f1Score,
      };
    }

    abortRef.current = streamAiAssist(
      {
        siteId,
        step: "results",
        message:
          "Please interpret these experiment results. Provide a clear scientific assessment, " +
          "explain what the metrics mean for this specific search, highlight key enrichment findings, " +
          "and suggest concrete next steps.",
        context,
        history: [],
      },
      {
        onDelta: (delta) => setResponse((prev) => prev + delta),
        onComplete: () => setStreaming(false),
        onError: () => setStreaming(false),
      },
    );
  }, [experiment, siteId, streaming]);

  return (
    <Section title="AI Interpretation">
      <div className="rounded-lg border border-border bg-card">
        {!hasRun ? (
          <div className="flex items-center justify-between px-5 py-4">
            <div>
              <p className="text-sm text-muted-foreground">
                Get an AI-generated analysis of your results with actionable next steps.
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                The AI will interpret metrics, enrichment findings, and suggest
                improvements.
              </p>
            </div>
            <button
              type="button"
              onClick={interpret}
              className="flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-xs font-medium text-primary-foreground transition hover:bg-primary/90"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Interpret Results
            </button>
          </div>
        ) : (
          <div className="px-5 py-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                <span className="text-xs font-semibold text-foreground">
                  AI Analysis
                </span>
              </div>
              {!streaming && (
                <button
                  type="button"
                  onClick={interpret}
                  className="text-xs text-muted-foreground transition hover:text-foreground"
                >
                  Re-analyze
                </button>
              )}
            </div>
            {response ? (
              <ChatMarkdown
                content={response}
                className="text-sm leading-relaxed text-foreground [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_p]:break-words [&_h1]:text-sm [&_h2]:text-sm [&_h3]:text-sm"
              />
            ) : (
              <div className="flex items-center gap-1.5 py-4 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Analyzing experiment results...
              </div>
            )}
          </div>
        )}
      </div>
    </Section>
  );
}

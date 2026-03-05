"use client";

import { Sparkles } from "lucide-react";
import { AiInterpretation } from "@/features/analysis";
import { AnalysisPanelContainer } from "../AnalysisPanelContainer";
import { useWorkbenchStore } from "../../store";
import { useSessionStore } from "@/state/useSessionStore";

export function AiInterpretationPanel() {
  const activeSetId = useWorkbenchStore((s) => s.activeSetId);
  const lastExperiment = useWorkbenchStore((s) => s.lastExperiment);
  const lastExperimentSetId = useWorkbenchStore((s) => s.lastExperimentSetId);
  const selectedSite = useSessionStore((s) => s.selectedSite);

  const experiment = lastExperimentSetId === activeSetId ? lastExperiment : null;
  const isDisabled = !experiment;

  return (
    <AnalysisPanelContainer
      panelId="ai-interpretation"
      title="AI Interpretation"
      subtitle="Get AI-powered analysis and interpretation of your results"
      icon={<Sparkles className="h-4 w-4" />}
      disabled={isDisabled}
      disabledReason="Requires a completed evaluation first"
    >
      {experiment && <AiInterpretation experiment={experiment} siteId={selectedSite} />}
    </AnalysisPanelContainer>
  );
}

import type { EnrichmentAnalysisType } from "@pathfinder/shared";
import { ENRICHMENT_ANALYSIS_LABELS } from "@/features/experiments/constants";
import { Checkbox } from "@/lib/components/ui/Checkbox";
import { Label } from "@/lib/components/ui/Label";

const ENRICHMENT_OPTIONS = (
  Object.entries(ENRICHMENT_ANALYSIS_LABELS) as [EnrichmentAnalysisType, string][]
).map(([type, label]) => ({ type, label }));

export interface EnrichmentConfigSectionProps {
  enrichments: Set<EnrichmentAnalysisType>;
  onToggleEnrichment: (type: EnrichmentAnalysisType) => void;
}

export function EnrichmentConfigSection({
  enrichments,
  onToggleEnrichment,
}: EnrichmentConfigSectionProps) {
  return (
    <div className="space-y-2">
      {ENRICHMENT_OPTIONS.map((opt) => (
        <Label
          key={opt.type}
          className="flex items-center gap-2 text-xs font-normal text-foreground"
        >
          <Checkbox
            checked={enrichments.has(opt.type)}
            onCheckedChange={() => onToggleEnrichment(opt.type)}
            className="h-3.5 w-3.5"
          />
          {opt.label}
        </Label>
      ))}
    </div>
  );
}

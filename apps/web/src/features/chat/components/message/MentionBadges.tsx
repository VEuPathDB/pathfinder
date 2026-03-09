import { FileText, FlaskConical, X } from "lucide-react";
import type { ChatMention } from "@pathfinder/shared";

interface MentionBadgesProps {
  mentions: ChatMention[];
  onRemove: (idx: number) => void;
}

export function MentionBadges({ mentions, onRemove }: MentionBadgesProps) {
  if (mentions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 border-b border-border px-2.5 py-1.5">
      {mentions.map((m, i) => {
        const MIcon = m.type === "strategy" ? FileText : FlaskConical;
        return (
          <span
            key={`${m.type}-${m.id}`}
            className="inline-flex items-center gap-1 rounded-md bg-primary/5 px-2 py-0.5 text-xs font-medium text-primary ring-1 ring-inset ring-primary/20"
          >
            <MIcon className="h-3 w-3 shrink-0" />
            {m.displayName}
            <button
              type="button"
              onClick={() => onRemove(i)}
              aria-label={`Remove mention: ${m.displayName}`}
              className="ml-0.5 rounded p-0.5 text-primary/50 transition-colors duration-150 hover:bg-primary/10 hover:text-primary"
            >
              <X className="h-2.5 w-2.5" aria-hidden />
            </button>
          </span>
        );
      })}
    </div>
  );
}

import { useEffect } from "react";
import type { NodeSelection } from "@/lib/types/nodeSelection";

export function useConsumePendingAskNode(args: {
  enabled: boolean;
  pendingAskNode: NodeSelection | null;
  setDraftSelection: (value: NodeSelection | null) => void;
  onConsumeAskNode?: () => void;
}) {
  const { enabled, pendingAskNode, setDraftSelection, onConsumeAskNode } = args;

  useEffect(() => {
    if (!enabled) return;
    if (!pendingAskNode) return;
    setDraftSelection(pendingAskNode);
    onConsumeAskNode?.();
  }, [enabled, pendingAskNode, setDraftSelection, onConsumeAskNode]);
}

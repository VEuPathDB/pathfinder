"use client";

/**
 * Orchestrator hook for UnifiedChatPanel.
 *
 * Composes all sub-hooks (stores, streaming, recovery, feature hooks)
 * and returns only the values/callbacks the JSX layer needs.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { Message, Strategy, StrategyPlan } from "@pathfinder/shared";
import type { NodeSelection } from "@/lib/types/nodeSelection";
import { usePrevious } from "@/lib/hooks/usePrevious";
import { getStrategy, updateStrategy as updateStrategyApi } from "@/lib/api/strategies";
import { useSessionStore } from "@/state/useSessionStore";
import { useStrategyStore } from "@/state/useStrategyStore";
import { useThinkingState } from "@/features/chat/hooks/useThinkingState";
import { useChatStreaming } from "@/features/chat/hooks/useChatStreaming";
import { useUnifiedChatModels } from "@/features/chat/hooks/useUnifiedChatModels";
import { StreamingSession } from "@/features/chat/streaming/StreamingSession";
import { useChatPreviewUpdate } from "@/features/chat/hooks/useChatPreviewUpdate";
import { useChatAutoScroll } from "@/features/chat/hooks/useChatAutoScroll";
import { useConsumePendingAskNode } from "@/features/chat/hooks/useConsumePendingAskNode";
import { useResetOnStrategyChange } from "@/features/chat/hooks/useResetOnStrategyChange";
import { parseToolArguments } from "@/features/chat/utils/parseToolArguments";
import { parseToolResult } from "@/features/chat/utils/parseToolResult";
import { useGraphSnapshot } from "@/features/chat/hooks/useGraphSnapshot";
import { useUnifiedChatDataLoading } from "@/features/chat/hooks/useUnifiedChatDataLoading";
import { useUnifiedChatStreamingArgs } from "@/features/chat/components/unifiedChatStreamingArgs";
import { useOperationRecovery } from "@/features/chat/hooks/useOperationRecovery";
import { useWorkbenchBridge } from "@/lib/hooks/useWorkbenchBridge";
import { useChatErrorHandling } from "@/features/chat/hooks/useChatErrorHandling";
import { useChatStrategyActions } from "@/features/chat/hooks/useChatStrategyActions";

interface UseChatPanelStateArgs {
  siteId: string;
  pendingAskNode?: NodeSelection | null;
  onConsumeAskNode?: () => void;
  /** Workbench store bindings — injected from page to avoid cross-feature import. */
  addGeneSet: (gs: import("@pathfinder/shared").GeneSet) => void;
  geneSets: import("@pathfinder/shared").GeneSet[];
}

export function useChatPanelState({
  siteId,
  pendingAskNode = null,
  onConsumeAskNode,
  addGeneSet,
  geneSets,
}: UseChatPanelStateArgs) {
  // --- Global state ---
  const strategyId = useSessionStore((s) => s.strategyId);
  const setStrategyIdGlobal = useSessionStore((s) => s.setStrategyId);
  const setChatIsStreaming = useSessionStore((s) => s.setChatIsStreaming);
  const selectedSiteDisplayName = useSessionStore((s) => s.selectedSiteDisplayName);
  const veupathdbName = useSessionStore((s) => s.veupathdbName);

  const firstName = veupathdbName?.split(" ")[0];
  const displayName = selectedSiteDisplayName || siteId;

  // --- Model management ---
  const models = useUnifiedChatModels();

  // --- Local state ---
  const [messages, setMessages] = useState<Message[]>([]);
  const [draftSelection, setDraftSelection] = useState<NodeSelection | null>(null);
  const [undoSnapshots, setUndoSnapshots] = useState<Record<number, Strategy>>({});

  const thinking = useThinkingState();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const previousStrategyId = usePrevious(strategyId);

  // --- Session ref ---
  const currentStrategy = useStrategyStore((s) => s.strategy);
  const sessionRef = useRef<StreamingSession | null>(null);

  useEffect(() => {
    if (sessionRef.current) sessionRef.current.latestStrategy = currentStrategy;
  }, [currentStrategy]);

  const createSession = useCallback(
    () => new StreamingSession(currentStrategy),
    [currentStrategy],
  );

  // --- Workbench bridge ---
  const { handleWorkbenchGeneSet } = useWorkbenchBridge(addGeneSet, geneSets);

  const clearMessages = useCallback(() => setMessages([]), []);
  const { handleError, apiError, setApiError } = useChatErrorHandling(
    setStrategyIdGlobal,
    clearMessages,
    setChatIsStreaming,
  );

  const {
    addStep,
    setStrategy,
    setWdkInfo,
    setStrategyMeta,
    clearStrategy,
    stepsById,
    addStrategy,
    addExecutedStrategy,
    loadGraph,
    handleAttachThinking,
  } = useChatStrategyActions(sessionRef, setMessages);

  const { applyGraphSnapshot } = useGraphSnapshot({
    siteId,
    strategyId,
    stepsById,
    sessionRef,
    setStrategy,
    setStrategyMeta,
  });

  // --- Streaming ---
  const streamingArgs = useUnifiedChatStreamingArgs({
    siteId,
    strategyId,
    draftSelection,
    setDraftSelection,
    thinking,
    setMessages,
    setUndoSnapshots,
    sessionRef,
    createSession,
    loadGraph,
    addStrategy,
    addExecutedStrategy,
    setStrategyIdGlobal,
    setWdkInfo,
    setStrategy,
    setStrategyMeta,
    clearStrategy,
    addStep,
    parseToolArguments,
    parseToolResult,
    applyGraphSnapshot,
    getStrategy,
    currentStrategy,
    attachThinkingToLastAssistant: handleAttachThinking,
    currentModelSelection: models.currentModelSelection,
    setSelectedModelId: models.setSelectedModelId,
    setChatIsStreaming,
    handleError,
    onWorkbenchGeneSet: handleWorkbenchGeneSet,
  });

  const {
    handleSendMessage: handleSendRaw,
    stopStreaming,
    isStreaming,
    setIsStreaming,
    optimizationProgress,
    setOptimizationProgress,
  } = useChatStreaming(streamingArgs);

  // Sync streaming state globally
  useEffect(() => {
    setChatIsStreaming(isStreaming);
  }, [isStreaming, setChatIsStreaming]);

  const onSend = useCallback(
    async (content: string, mentions?: import("@pathfinder/shared").ChatMention[]) => {
      setChatIsStreaming(true);
      setApiError(null);
      await handleSendRaw(content, mentions);
    },
    [handleSendRaw, setChatIsStreaming, setApiError],
  );

  // --- Data loading ---
  const handleStrategyNotFound = useCallback(() => {
    setStrategyIdGlobal(null);
  }, [setStrategyIdGlobal]);

  const { isLoading: isLoadingChat } = useUnifiedChatDataLoading({
    strategyId,
    sessionRef,
    setMessages,
    setApiError,
    setSelectedModelId: models.setSelectedModelId,
    thinking,
    setStrategy,
    setStrategyMeta,
    onStrategyNotFound: handleStrategyNotFound,
  });

  // --- Operation recovery (reconnect to in-flight ops on refresh) ---
  useOperationRecovery({
    strategyId,
    siteId,
    isStreaming,
    setIsStreaming,
    setMessages,
    setUndoSnapshots,
    thinking,
    currentStrategy,
    setStrategyId: setStrategyIdGlobal,
    addStrategy,
    addExecutedStrategy,
    setWdkInfo,
    setStrategy,
    setStrategyMeta,
    clearStrategy,
    addStep,
    loadGraph,
    parseToolArguments,
    parseToolResult,
    applyGraphSnapshot,
    getStrategy,
    attachThinkingToLastAssistant: handleAttachThinking,
    setSelectedModelId: models.setSelectedModelId,
    onApiError: handleError
      ? (msg: string) => handleError(new Error(msg), msg)
      : undefined,
    setOptimizationProgress,
    onWorkbenchGeneSet: handleWorkbenchGeneSet,
  });

  // --- Feature hooks ---
  useChatPreviewUpdate(strategyId, `${messages.length}`);

  useResetOnStrategyChange({
    strategyId,
    previousStrategyId,
    resetThinking: thinking.reset,
    setIsStreaming,
    setMessages,
    setUndoSnapshots,
    sessionRef,
    stopStreaming,
  });

  useChatAutoScroll(messagesEndRef, `${messages.length}:${isStreaming ? "s" : "i"}`);

  useConsumePendingAskNode({
    enabled: true,
    pendingAskNode,
    setDraftSelection,
    onConsumeAskNode,
  });

  // --- Undo snapshot handler ---
  const handleUndoSnapshot = useCallback(
    (snapshot: Strategy) => {
      setStrategy(snapshot);
      setStrategyMeta({
        name: snapshot.name,
        description: snapshot.description ?? undefined,
        recordType: snapshot.recordType ?? undefined,
      });
    },
    [setStrategy, setStrategyMeta],
  );

  // --- Apply planning artifact handler ---
  const handleApplyPlanningArtifact = useCallback(
    async (artifact: { proposedStrategyPlan?: unknown }) => {
      if (!strategyId) return;
      const proposed = artifact.proposedStrategyPlan;
      if (!proposed || typeof proposed !== "object" || Array.isArray(proposed)) return;
      try {
        await updateStrategyApi(strategyId, {
          plan: proposed as StrategyPlan,
        });
        const full = await getStrategy(strategyId);
        setStrategy(full);
        setStrategyMeta({
          name: full.name,
          description: full.description ?? undefined,
          recordType: full.recordType ?? undefined,
          siteId: full.siteId,
        });
      } catch (err) {
        console.warn("[UnifiedChat] Failed to apply planning artifact:", err);
      }
    },
    [strategyId, setStrategy, setStrategyMeta],
  );

  return {
    displayName,
    firstName,
    messages,
    undoSnapshots,
    isStreaming,
    isLoadingChat,
    onSend,
    stopStreaming,
    optimizationProgress,
    thinking,
    apiError,
    setApiError,
    draftSelection,
    setDraftSelection,
    models,
    messagesEndRef,
    handleUndoSnapshot,
    handleApplyPlanningArtifact,
  };
}

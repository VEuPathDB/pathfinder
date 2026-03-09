"use client";

/**
 * ConversationSidebar — sidebar listing strategy conversations
 * in chronologically sorted order.
 *
 * Composed from:
 * - `useConversationSidebarData` — data fetching, filtering
 * - `useConversationSidebarActions` — selection, rename, delete, duplicate
 * - `ConversationList` — list rendering
 */

import { useCallback } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { useSessionStore } from "@/state/useSessionStore";
import { useConversationSidebarData } from "@/features/sidebar/hooks/useConversationSidebarData";
import { useConversationSidebarActions } from "@/features/sidebar/hooks/useConversationSidebarActions";
import { ConversationList } from "@/features/sidebar/components/ConversationList";
import { DeleteConversationModal } from "@/features/sidebar/components/DeleteConversationModal";
import { DuplicateStrategyModal } from "@/features/sidebar/components/DuplicateStrategyModal";

interface ConversationSidebarProps {
  siteId: string;
  onToast?: (toast: {
    type: "success" | "error" | "warning" | "info";
    message: string;
  }) => void;
}

export function ConversationSidebar({ siteId, onToast }: ConversationSidebarProps) {
  const chatIsStreaming = useSessionStore((s) => s.chatIsStreaming);

  const reportError = useCallback(
    (message: string) => onToast?.({ type: "error", message }),
    [onToast],
  );

  const data = useConversationSidebarData({ siteId, reportError });
  const actions = useConversationSidebarActions({
    siteId,
    reportError,
    refreshStrategies: data.refreshStrategies,
    setStrategyItems: data.setStrategyItems,
  });

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 px-3 py-4">
      {/* Header: title + action buttons */}
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Conversations
        </div>
        <div className="flex items-center gap-1">
          <button
            data-testid="conversations-refresh-button"
            type="button"
            disabled={chatIsStreaming || data.isSyncing}
            onClick={() => void data.handleManualRefresh()}
            className="rounded-md p-1 text-muted-foreground transition-colors duration-150 hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
            title="Refresh conversations & strategies"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${data.isSyncing ? "animate-spin" : ""}`}
            />
          </button>
          <button
            data-testid="conversations-new-button"
            type="button"
            disabled={chatIsStreaming}
            onClick={() => void actions.handleNewConversation()}
            aria-label="New chat"
            className="rounded-md border border-input bg-background px-2.5 py-1 text-xs font-medium text-foreground transition-colors duration-150 hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            New Chat
          </button>
        </div>
      </div>

      {/* Search */}
      <input
        data-testid="conversations-search-input"
        value={data.query}
        onChange={(e) => data.setQuery(e.target.value)}
        placeholder="Search conversations..."
        aria-label="Search conversations"
        className="w-full rounded-md border border-border bg-card px-2.5 py-1.5 text-sm text-foreground placeholder:text-muted-foreground transition-colors duration-150 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
      />

      {/* Loading indicator — shown until the first fetch completes */}
      {(!data.hasInitiallyLoaded || data.isSyncing) && data.filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-2 py-10 text-muted-foreground animate-fade-in">
          <Loader2 className="h-5 w-5 animate-spin" />
          <p className="text-xs">Loading conversations…</p>
        </div>
      )}

      {/* Conversation list */}
      <ConversationList
        items={data.filtered}
        query={data.query}
        hasInitiallyLoaded={data.hasInitiallyLoaded}
        activeId={actions.activeId}
        renamingId={actions.renamingId}
        renameValue={actions.renameValue}
        onRenameValueChange={actions.setRenameValue}
        onCommitRename={(target) => void actions.commitRename(target)}
        onCancelRename={actions.cancelRename}
        onSelect={actions.handleSelect}
        onStartRename={actions.startRename}
        onStartDelete={actions.setDeleteTarget}
        onStartDuplicate={actions.startDuplicate}
        onToggleSaved={(si) => void actions.handleToggleSaved(si)}
      />

      {/* Modals */}
      <DeleteConversationModal
        target={actions.deleteTarget}
        isDeleting={actions.isDeleting}
        onClose={() => actions.setDeleteTarget(null)}
        onConfirmDelete={() => void actions.confirmDelete()}
      />

      <DuplicateStrategyModal
        duplicateModal={actions.duplicateModal}
        setDuplicateModal={actions.setDuplicateModal}
        onDuplicate={actions.handleDuplicate}
      />
    </div>
  );
}

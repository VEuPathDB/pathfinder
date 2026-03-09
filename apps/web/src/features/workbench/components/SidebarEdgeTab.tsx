"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

interface SidebarEdgeTabProps {
  /** Which edge this tab sits on. */
  side: "left" | "right";
  /** Label shown vertically on the tab. */
  label: string;
  /** Icon rendered above the label. */
  icon: React.ReactNode;
  onClick: () => void;
}

/**
 * Thin vertical tab pinned to a screen edge. Clicking it opens the
 * collapsed sidebar. Shows an icon, a rotated label, and a chevron.
 */
export function SidebarEdgeTab({ side, label, icon, onClick }: SidebarEdgeTabProps) {
  const Chevron = side === "left" ? ChevronRight : ChevronLeft;

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Open ${label}`}
      className={`group flex h-full w-9 shrink-0 flex-col items-center gap-2 border-border bg-sidebar py-3 text-muted-foreground transition-colors duration-150 hover:bg-accent hover:text-foreground ${
        side === "left" ? "border-r" : "border-l"
      }`}
    >
      <Chevron className="h-4 w-4 opacity-60 group-hover:opacity-100" />
      <span className="flex h-4 w-4 items-center justify-center">{icon}</span>
      <span
        className="text-[10px] font-medium uppercase tracking-widest"
        style={{ writingMode: "vertical-lr" }}
      >
        {label}
      </span>
    </button>
  );
}

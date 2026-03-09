"use client";

import { Database } from "lucide-react";

export function BlockingOverlay() {
  return (
    <div data-blocking-overlay className="flex h-full items-center justify-center">
      <div className="text-center animate-fade-in">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted/50">
          <Database className="h-8 w-8 text-muted-foreground" />
        </div>
        <h2 className="text-base font-semibold text-foreground">
          Select a gene set to begin
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Pick a gene set from the sidebar to unlock analysis panels.
        </p>
      </div>
    </div>
  );
}

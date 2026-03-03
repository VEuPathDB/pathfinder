// @vitest-environment jsdom
import React from "react";
import { afterEach, describe, it, expect, vi } from "vitest";
import { cleanup, render, fireEvent } from "@testing-library/react";
import type { ExperimentSummary } from "@pathfinder/shared";

/* ------------------------------------------------------------------ */
/*  Mocks                                                              */
/* ------------------------------------------------------------------ */

const STORE_STATE = {
  experiments: [] as ExperimentSummary[],
  fetchExperiments: vi.fn(),
  loadExperiment: vi.fn(),
  deleteExperiment: vi.fn(),
  cloneExperiment: vi.fn(),
  setView: vi.fn(),
};

vi.mock("../store", () => ({
  useExperimentViewStore: () => STORE_STATE,
}));

vi.mock("@/lib/components/ui/Button", () => ({
  Button: ({ children, ...props }: React.ComponentProps<"button">) => (
    <button {...props}>{children}</button>
  ),
}));
vi.mock("@/lib/components/ui/Input", () => ({
  Input: (props: React.ComponentProps<"input">) => <input {...props} />,
}));
vi.mock("@/lib/components/ui/Badge", () => ({
  Badge: ({ children, ...props }: React.ComponentProps<"span">) => (
    <span data-testid="badge" {...props}>
      {children}
    </span>
  ),
}));
vi.mock("@/lib/components/ui/ScrollArea", () => ({
  ScrollArea: ({ children, ...props }: React.ComponentProps<"div">) => (
    <div data-testid="scroll-area" {...props}>
      {children}
    </div>
  ),
}));
vi.mock("@/lib/components/ui/Tooltip", () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <span>{children}</span>
  ),
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock("@/lib/components/ui/AlertDialog", () => ({
  AlertDialog: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  AlertDialogAction: (props: React.ComponentProps<"button">) => <button {...props} />,
  AlertDialogCancel: (props: React.ComponentProps<"button">) => <button {...props} />,
  AlertDialogContent: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  AlertDialogDescription: ({ children }: { children: React.ReactNode }) => (
    <p>{children}</p>
  ),
  AlertDialogFooter: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  AlertDialogHeader: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  AlertDialogTitle: ({ children }: { children: React.ReactNode }) => (
    <h2>{children}</h2>
  ),
}));
vi.mock("@/lib/utils/cn", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

import { ExperimentList } from "./ExperimentList";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function makeExp(overrides: Partial<ExperimentSummary> = {}): ExperimentSummary {
  return {
    id: "exp-1",
    name: "Test Experiment",
    searchName: "GenesByTaxon",
    status: "completed",
    createdAt: "2026-03-01T00:00:00Z",
    f1Score: null,
    sensitivity: null,
    specificity: null,
    precision: null,
    mcc: null,
    siteId: "PlasmoDB",
    recordType: "transcript",
    stepCount: 1,
    resultCount: 100,
    ...overrides,
  } as ExperimentSummary;
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  STORE_STATE.experiments = [];
});

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe("ExperimentCard layout", () => {
  it("card container has overflow-hidden to prevent name overflow", () => {
    STORE_STATE.experiments = [makeExp({ name: "A".repeat(200) })];
    const { container } = render(<ExperimentList siteId="PlasmoDB" />);

    const card = container.querySelector("[role='button']");
    expect(card).toBeTruthy();
    expect(card!.className).toContain("overflow-hidden");
  });

  it("action buttons are inside the flex flow, not absolute-positioned", () => {
    STORE_STATE.experiments = [makeExp()];
    const { container } = render(<ExperimentList siteId="PlasmoDB" />);

    const cloneBtn = container.querySelector("button[title='Clone experiment']");
    const deleteBtn = container.querySelector("button[title='Delete experiment']");
    expect(cloneBtn).toBeTruthy();
    expect(deleteBtn).toBeTruthy();

    // Walk up from clone button — no ancestor within the card should be absolute
    const actionWrapper = cloneBtn!.parentElement!;
    expect(actionWrapper.className).not.toContain("absolute");
  });

  it("name row has min-w-0 to enable truncation within flex layout", () => {
    STORE_STATE.experiments = [makeExp({ name: "A".repeat(200) })];
    const { container } = render(<ExperimentList siteId="PlasmoDB" />);

    const card = container.querySelector("[role='button']");
    // The first child div is the name row (flex row with name + buttons)
    const nameRow = card!.querySelector(".justify-between");
    expect(nameRow).toBeTruthy();
    expect(nameRow!.className).toContain("min-w-0");
  });

  it("name text has truncate class for ellipsis", () => {
    const longName = "A very long experiment name that should be truncated";
    STORE_STATE.experiments = [makeExp({ name: longName })];
    const { container } = render(<ExperimentList siteId="PlasmoDB" />);

    const card = container.querySelector("[role='button']");
    const nameSpan = card!.querySelector(".truncate");
    expect(nameSpan).toBeTruthy();
    expect(nameSpan!.textContent).toContain(longName);
  });

  it("clone button click does not trigger card selection", () => {
    STORE_STATE.experiments = [makeExp()];
    const { container } = render(<ExperimentList siteId="PlasmoDB" />);

    const cloneBtn = container.querySelector(
      "button[title='Clone experiment']",
    ) as HTMLElement;
    fireEvent.click(cloneBtn);

    expect(STORE_STATE.cloneExperiment).toHaveBeenCalledWith("exp-1");
    expect(STORE_STATE.loadExperiment).not.toHaveBeenCalled();
  });

  it("delete button click does not trigger card selection", () => {
    STORE_STATE.experiments = [makeExp()];
    const { container } = render(<ExperimentList siteId="PlasmoDB" />);

    const deleteBtn = container.querySelector(
      "button[title='Delete experiment']",
    ) as HTMLElement;
    fireEvent.click(deleteBtn);

    // Delete sets deleteTarget, not directly calling deleteExperiment — but
    // the key assertion is that card selection (loadExperiment) was NOT called.
    expect(STORE_STATE.loadExperiment).not.toHaveBeenCalled();
  });

  it("ScrollArea forces block display on Radix viewport wrapper to prevent horizontal expansion", () => {
    STORE_STATE.experiments = [makeExp({ name: "A".repeat(300) })];
    const { container } = render(<ExperimentList siteId="PlasmoDB" />);

    const scrollArea = container.querySelector("[data-testid='scroll-area']");
    expect(scrollArea).toBeTruthy();
    // The ScrollArea must include the Tailwind class that overrides Radix's
    // internal `display: table` wrapper, preventing content from expanding
    // beyond the sidebar width and breaking truncation.
    expect(scrollArea!.className).toMatch(/\[&>?\[data-radix/);
  });

  it("sidebar container has overflow-hidden to clip horizontal content", () => {
    STORE_STATE.experiments = [makeExp({ name: "B".repeat(300) })];
    const { container } = render(<ExperimentList siteId="PlasmoDB" />);

    // The outermost div of ExperimentList should have overflow-hidden
    const root = container.firstElementChild;
    expect(root).toBeTruthy();
    expect(root!.className).toContain("overflow-hidden");
  });
});

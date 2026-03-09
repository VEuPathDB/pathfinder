import { describe, expect, it, vi, afterEach } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

function makeLocalStorage(initial: Record<string, string> = {}) {
  const store = new Map<string, string>(Object.entries(initial));
  return {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
    raw: store,
  };
}

const STORAGE_KEY = "pathfinder-settings";

// ---------------------------------------------------------------------------
// Default initial state
// ---------------------------------------------------------------------------

describe("state/useSettingsStore - defaults", () => {
  it("initializes with default values when no localStorage", async () => {
    const mod = await import("./useSettingsStore");
    const state = mod.useSettingsStore.getState();

    expect(state.defaultModelId).toBeNull();
    expect(state.defaultReasoningEffort).toBe("medium");
    expect(state.advancedReasoningBudgets).toEqual({});
    expect(state.showRawToolCalls).toBe(false);
    expect(state.modelCatalog).toEqual([]);
    expect(state.catalogDefault).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// setDefaultModelId
// ---------------------------------------------------------------------------

describe("setDefaultModelId", () => {
  it("updates defaultModelId in state", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    store.getState().setDefaultModelId("openai/gpt-5");
    expect(store.getState().defaultModelId).toBe("openai/gpt-5");
  });

  it("sets defaultModelId to null", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    store.getState().setDefaultModelId("some-model");
    store.getState().setDefaultModelId(null);
    expect(store.getState().defaultModelId).toBeNull();
  });

  it("persists to localStorage", async () => {
    const localStorage = makeLocalStorage();
    vi.stubGlobal("window", { localStorage });

    const mod = await import("./useSettingsStore");
    mod.useSettingsStore.getState().setDefaultModelId("anthropic/claude-4");

    const persisted = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(persisted.defaultModelId).toBe("anthropic/claude-4");
  });
});

// ---------------------------------------------------------------------------
// setDefaultReasoningEffort
// ---------------------------------------------------------------------------

describe("setDefaultReasoningEffort", () => {
  it("updates reasoning effort", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    store.getState().setDefaultReasoningEffort("high");
    expect(store.getState().defaultReasoningEffort).toBe("high");
  });

  it("supports all reasoning effort levels", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    for (const effort of ["none", "low", "medium", "high"] as const) {
      store.getState().setDefaultReasoningEffort(effort);
      expect(store.getState().defaultReasoningEffort).toBe(effort);
    }
  });

  it("persists to localStorage", async () => {
    const localStorage = makeLocalStorage();
    vi.stubGlobal("window", { localStorage });

    const mod = await import("./useSettingsStore");
    mod.useSettingsStore.getState().setDefaultReasoningEffort("low");

    const persisted = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(persisted.defaultReasoningEffort).toBe("low");
  });
});

// ---------------------------------------------------------------------------
// setAdvancedReasoningBudget
// ---------------------------------------------------------------------------

describe("setAdvancedReasoningBudget", () => {
  it("adds a budget for a new provider", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    store.getState().setAdvancedReasoningBudget("openai", 2048);
    expect(store.getState().advancedReasoningBudgets).toEqual({ openai: 2048 });
  });

  it("updates an existing provider budget", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    store.getState().setAdvancedReasoningBudget("openai", 1024);
    store.getState().setAdvancedReasoningBudget("openai", 4096);
    expect(store.getState().advancedReasoningBudgets.openai).toBe(4096);
  });

  it("supports multiple providers simultaneously", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    store.getState().setAdvancedReasoningBudget("openai", 1024);
    store.getState().setAdvancedReasoningBudget("anthropic", 2048);
    store.getState().setAdvancedReasoningBudget("google", 512);

    const budgets = store.getState().advancedReasoningBudgets;
    expect(budgets).toEqual({ openai: 1024, anthropic: 2048, google: 512 });
  });

  it("persists to localStorage", async () => {
    const localStorage = makeLocalStorage();
    vi.stubGlobal("window", { localStorage });

    const mod = await import("./useSettingsStore");
    mod.useSettingsStore.getState().setAdvancedReasoningBudget("openai", 2048);

    const persisted = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(persisted.advancedReasoningBudgets).toEqual({ openai: 2048 });
  });
});

// ---------------------------------------------------------------------------
// setShowRawToolCalls
// ---------------------------------------------------------------------------

describe("setShowRawToolCalls", () => {
  it("toggles show raw tool calls on", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    store.getState().setShowRawToolCalls(true);
    expect(store.getState().showRawToolCalls).toBe(true);
  });

  it("toggles show raw tool calls off", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    store.getState().setShowRawToolCalls(true);
    store.getState().setShowRawToolCalls(false);
    expect(store.getState().showRawToolCalls).toBe(false);
  });

  it("persists to localStorage", async () => {
    const localStorage = makeLocalStorage();
    vi.stubGlobal("window", { localStorage });

    const mod = await import("./useSettingsStore");
    mod.useSettingsStore.getState().setShowRawToolCalls(true);

    const persisted = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(persisted.showRawToolCalls).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// setModelCatalog
// ---------------------------------------------------------------------------

describe("setModelCatalog", () => {
  it("sets model catalog and catalog default", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    const models = [
      {
        id: "openai/gpt-5",
        name: "GPT-5",
        provider: "openai" as const,
        model: "gpt-5",
        supportsReasoning: true,
        enabled: true,
      },
      {
        id: "anthropic/claude-4",
        name: "Claude 4",
        provider: "anthropic" as const,
        model: "claude-4",
        supportsReasoning: true,
        enabled: true,
      },
    ];

    store.getState().setModelCatalog(models, "openai/gpt-5");

    expect(store.getState().modelCatalog).toEqual(models);
    expect(store.getState().catalogDefault).toBe("openai/gpt-5");
  });

  it("does not persist catalog to localStorage", async () => {
    const localStorage = makeLocalStorage();
    vi.stubGlobal("window", { localStorage });

    const mod = await import("./useSettingsStore");
    mod.useSettingsStore.getState().setModelCatalog(
      [
        {
          id: "openai/gpt-5",
          name: "GPT-5",
          provider: "openai" as const,
          model: "gpt-5",
          supportsReasoning: true,
          enabled: true,
        },
      ],
      "openai/gpt-5",
    );

    // The catalog should NOT appear in persisted data - only user-editable fields
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const persisted = JSON.parse(raw);
      expect(persisted.modelCatalog).toBeUndefined();
      expect(persisted.catalogDefault).toBeUndefined();
    }
  });
});

// ---------------------------------------------------------------------------
// resetToDefaults
// ---------------------------------------------------------------------------

describe("resetToDefaults", () => {
  it("resets all user-editable state to defaults", async () => {
    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    // Set everything to non-default values
    store.getState().setDefaultModelId("anthropic/claude-4");
    store.getState().setDefaultReasoningEffort("high");
    store.getState().setAdvancedReasoningBudget("openai", 4096);
    store.getState().setShowRawToolCalls(true);

    // Reset
    store.getState().resetToDefaults();

    const state = store.getState();
    expect(state.defaultModelId).toBeNull();
    expect(state.defaultReasoningEffort).toBe("medium");
    expect(state.advancedReasoningBudgets).toEqual({});
    expect(state.showRawToolCalls).toBe(false);
  });

  it("persists reset state to localStorage", async () => {
    const localStorage = makeLocalStorage();
    vi.stubGlobal("window", { localStorage });

    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    store.getState().setDefaultModelId("some-model");
    store.getState().resetToDefaults();

    const persisted = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(persisted.defaultModelId).toBeNull();
    expect(persisted.defaultReasoningEffort).toBe("medium");
    expect(persisted.advancedReasoningBudgets).toEqual({});
    expect(persisted.showRawToolCalls).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Persistence — restoring from localStorage
// ---------------------------------------------------------------------------

describe("persistence", () => {
  it("restores settings from localStorage on init", async () => {
    const stored = {
      defaultModelId: "anthropic/claude-4",
      defaultReasoningEffort: "high",
      advancedReasoningBudgets: { openai: 2048 },
      showRawToolCalls: true,
    };
    vi.stubGlobal("window", {
      localStorage: makeLocalStorage({
        [STORAGE_KEY]: JSON.stringify(stored),
      }),
    });

    const mod = await import("./useSettingsStore");
    const state = mod.useSettingsStore.getState();

    expect(state.defaultModelId).toBe("anthropic/claude-4");
    expect(state.defaultReasoningEffort).toBe("high");
    expect(state.advancedReasoningBudgets).toEqual({ openai: 2048 });
    expect(state.showRawToolCalls).toBe(true);
  });

  it("handles corrupted localStorage gracefully", async () => {
    vi.stubGlobal("window", {
      localStorage: makeLocalStorage({
        [STORAGE_KEY]: "not valid json!!!",
      }),
    });

    const mod = await import("./useSettingsStore");
    const state = mod.useSettingsStore.getState();

    // Should fall back to defaults
    expect(state.defaultModelId).toBeNull();
    expect(state.defaultReasoningEffort).toBe("medium");
  });

  it("handles missing localStorage key gracefully", async () => {
    vi.stubGlobal("window", {
      localStorage: makeLocalStorage({}),
    });

    const mod = await import("./useSettingsStore");
    const state = mod.useSettingsStore.getState();

    expect(state.defaultModelId).toBeNull();
    expect(state.defaultReasoningEffort).toBe("medium");
  });

  it("merges persisted state with existing values on subsequent calls", async () => {
    const localStorage = makeLocalStorage({
      [STORAGE_KEY]: JSON.stringify({ defaultModelId: "model-1" }),
    });
    vi.stubGlobal("window", { localStorage });

    const mod = await import("./useSettingsStore");
    const store = mod.useSettingsStore;

    // Changing reasoning effort should merge with existing persisted defaultModelId
    store.getState().setDefaultReasoningEffort("high");

    const persisted = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(persisted.defaultModelId).toBe("model-1");
    expect(persisted.defaultReasoningEffort).toBe("high");
  });
});

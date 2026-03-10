import { test, expect } from "../fixtures/test";

test.describe("AI Workbench Integration", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ chatPage }) => {
    await chatPage.goto();
    await chatPage.newChat();
  });

  test("delegation creates strategy with steps visible in graph and stored in DB", async ({
    chatPage,
    graphPage,
    apiClient,
  }) => {
    await chatPage.send("delegation");
    await chatPage.expectAssistantMessage(/\[mock\].*delegation/i);

    // UI: Compact view with step pills
    await graphPage.expectCompactView();
    const pillCount = await graphPage.stepPills.count();
    expect(pillCount).toBeGreaterThan(0);

    // API: Strategy persisted — use captured ID for isolation
    const strategyId = chatPage.lastStrategyId;
    expect(strategyId).toBeTruthy();
    const fullResp = await apiClient.get(`/api/v1/strategies/${strategyId}`);
    expect(fullResp.ok()).toBeTruthy();
    const full = await fullResp.json();
    expect(full.messages).toBeDefined();
    expect(full.messages.length).toBeGreaterThan(0);
  });

  test("artifact graph creates exportable strategy persisted in DB", async ({
    chatPage,
    graphPage,
    page,
    apiClient,
  }) => {
    await chatPage.send("artifact graph");
    await chatPage.expectPlanningArtifact();

    // UI: Click apply to create strategy
    await page.getByRole("button", { name: /apply to strategy/i }).click();
    await graphPage.expectCompactView();

    // UI: Edit button visible
    await expect(page.getByRole("button", { name: /edit/i })).toBeVisible();

    // UI: Step pills show content
    const pillCount = await graphPage.stepPills.count();
    expect(pillCount).toBeGreaterThan(0);

    // API: Strategy with steps persisted — use captured ID for isolation
    const strategyId = chatPage.lastStrategyId;
    expect(strategyId).toBeTruthy();
    const fullResp = await apiClient.get(`/api/v1/strategies/${strategyId}`);
    expect(fullResp.ok()).toBeTruthy();
    const full = await fullResp.json();
    expect(full.steps.length).toBeGreaterThan(0);
  });
});

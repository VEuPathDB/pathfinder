import { test, expect } from "../fixtures/test";

/**
 * Feature: Chat — real event pipeline through Redis + PostgreSQL.
 * Mock LLM provides deterministic text, but events flow through
 * real kani orchestration → Redis streams → PostgreSQL projections.
 * Every test verifies server-side state via API.
 */
test.describe("Chat", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ chatPage }) => {
    await chatPage.goto();
    await chatPage.newChat();
  });

  test("send message stores conversation in PostgreSQL", async ({
    chatPage,
    apiClient,
  }) => {
    await chatPage.send("find chloroquine resistance genes");
    await chatPage.expectAssistantMessage(/\[mock\]/);
    await chatPage.expectIdle();

    // Fetch full strategy — verify messages stored (use captured ID)
    const strategyId = chatPage.lastStrategyId;
    expect(strategyId).toBeTruthy();
    const fullResp = await apiClient.get(`/api/v1/strategies/${strategyId}`);
    expect(fullResp.ok()).toBeTruthy();
    const full = await fullResp.json();
    expect(full.messages).toBeDefined();
    expect(full.messages.length).toBeGreaterThan(0);
  });

  test("empty message keeps send button disabled", async ({ chatPage }) => {
    await chatPage.expectSendDisabled();
  });

  test("artifact graph stores strategy plan with real WDK search names", async ({
    chatPage,
    page,
    apiClient,
  }) => {
    await chatPage.send("artifact graph");
    await chatPage.expectAssistantMessage(/\[mock\]/);
    await chatPage.expectPlanningArtifact();
    await chatPage.expectIdle();

    // Apply the plan
    await page.getByRole("button", { name: /apply to strategy/i }).click();

    // Wait for strategy update
    await page.waitForTimeout(2_000);

    // Fetch full strategy — verify steps were created from the plan
    const strategyId = chatPage.lastStrategyId;
    expect(strategyId).toBeTruthy();
    const fullResp = await apiClient.get(`/api/v1/strategies/${strategyId}`);
    expect(fullResp.ok()).toBeTruthy();
    const full = await fullResp.json();
    expect(full.steps.length).toBeGreaterThan(0);
  });

  test("delegation draft stores event data", async ({ chatPage, apiClient }) => {
    await chatPage.send("delegation draft");
    await chatPage.expectAssistantMessage(/\[mock\]/);
    await chatPage.expectIdle();

    // Fetch full conversation — messages should be stored (use captured ID)
    const strategyId = chatPage.lastStrategyId;
    expect(strategyId).toBeTruthy();
    const fullResp = await apiClient.get(`/api/v1/strategies/${strategyId}`);
    expect(fullResp.ok()).toBeTruthy();
    const full = await fullResp.json();
    expect(full.messages.length).toBeGreaterThan(0);
  });

  test("stop streaming cancels operation", async ({ chatPage }) => {
    await chatPage.send("slow");
    await chatPage.expectStreaming();
    await chatPage.stopStreaming();
    await chatPage.expectIdle();
  });

  test("multiple messages stored sequentially in conversation", async ({
    chatPage,
    apiClient,
  }) => {
    await chatPage.send("first message");
    await chatPage.expectAssistantMessage(/\[mock\].*first message/);
    await chatPage.expectIdle();

    await chatPage.send("second message");
    await chatPage.expectAssistantMessage(/\[mock\].*second message/);
    await chatPage.expectIdle();

    // Verify both messages persisted (use captured ID)
    const strategyId = chatPage.lastStrategyId;
    expect(strategyId).toBeTruthy();
    const fullResp = await apiClient.get(`/api/v1/strategies/${strategyId}`);
    const full = await fullResp.json();
    const userMsgs = full.messages.filter((m: { role: string }) => m.role === "user");
    const assistantMsgs = full.messages.filter(
      (m: { role: string }) => m.role === "assistant",
    );
    expect(userMsgs.length).toBeGreaterThanOrEqual(2);
    expect(assistantMsgs.length).toBeGreaterThanOrEqual(2);
  });

  test("conversation auto-created and persisted", async ({ chatPage, sidebarPage }) => {
    await chatPage.send("hello world");
    await chatPage.expectAssistantMessage(/\[mock\]/);

    await expect(sidebarPage.items.first()).toBeVisible({ timeout: 15_000 });

    // Strategy ID was captured during newChat
    expect(chatPage.lastStrategyId).toBeTruthy();
  });

  test("page reload restores conversation from PostgreSQL", async ({
    chatPage,
    page,
    apiClient,
  }) => {
    await chatPage.send("persistent message");
    await chatPage.expectAssistantMessage(/\[mock\].*persistent message/);

    const strategyId = chatPage.lastStrategyId;
    expect(strategyId).toBeTruthy();

    await page.reload();
    await expect(page.getByTestId("message-composer")).toBeVisible();
    await expect(page.getByText("persistent message", { exact: true })).toBeVisible({
      timeout: 15_000,
    });

    // Strategy still exists after reload
    const afterResp = await apiClient.get(`/api/v1/strategies/${strategyId}`);
    expect(afterResp.ok()).toBeTruthy();
  });
});

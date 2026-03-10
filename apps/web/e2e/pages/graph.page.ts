import { type Locator, type Page, expect } from "@playwright/test";

export class GraphPage {
  constructor(private page: Page) {}

  /** The compact strategy strip at the bottom of the chat page. */
  get compactView(): Locator {
    // CompactStrategyView: <div class="border-t border-border bg-muted">
    return this.page.locator(".border-t.border-border.bg-muted").filter({
      has: this.page.locator(".overflow-x-auto"),
    });
  }

  /** Step pills in the compact strategy view. */
  get stepPills(): Locator {
    return this.compactView.locator(".rounded.border.bg-card");
  }

  /** Open the graph editor modal from the compact view "Edit" button. */
  async open() {
    await this.page.getByRole("button", { name: /edit/i }).click();
  }

  async close() {
    // The graph editor modal can be closed via the modal close button.
    await this.page.getByRole("dialog").getByRole("button", { name: /close/i }).click();
  }

  /** All strategy graph nodes in the ReactFlow editor modal. */
  get nodes(): Locator {
    return this.page.locator("[data-testid^='rf-node-']");
  }

  node(stepId: string): Locator {
    return this.page.getByTestId(`rf-node-${stepId}`);
  }

  async clickNode(stepId: string) {
    await this.node(stepId).click();
  }

  async askAboutNode(stepId: string) {
    await this.page.getByTestId(`rf-add-to-chat-${stepId}`).click();
  }

  /** Click the "Workbench" export button in the compact view. */
  async exportAsGeneSet() {
    await this.page.getByRole("button", { name: /workbench/i }).click();
  }

  async expectCompactView() {
    await expect(this.compactView).toBeVisible({ timeout: 30_000 });
  }

  async expectStepPillCount(count: number) {
    await expect(this.stepPills).toHaveCount(count);
  }

  async expectNodeCount(count: number) {
    await expect(this.nodes).toHaveCount(count);
  }

  async expectNodeVisible(stepId: string) {
    await expect(this.node(stepId)).toBeVisible();
  }
}

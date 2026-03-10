import { type Locator, type Page, expect } from "@playwright/test";

export class GeneSearchSidebar {
  readonly searchInput: Locator;

  constructor(private page: Page) {
    this.searchInput = page.getByPlaceholder(/search genes/i);
  }

  async search(query: string) {
    await this.searchInput.fill(query);
    // Wait for results to load
    await this.page.waitForTimeout(500);
  }

  async expectResultsVisible() {
    await expect(this.page.getByText(/\d+ results?/i)).toBeVisible({ timeout: 15_000 });
  }

  async expectResultCount(count: number) {
    await expect(this.page.getByText(new RegExp(`${count} results?`))).toBeVisible();
  }
}

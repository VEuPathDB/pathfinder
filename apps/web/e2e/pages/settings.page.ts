import { type Page, expect } from "@playwright/test";

export class SettingsPage {
  constructor(private page: Page) {}

  /** Open settings via the top bar settings button. */
  async open() {
    await this.page.getByRole("button", { name: /settings/i }).click();
    await expect(
      this.page.getByRole("dialog").filter({ hasText: /settings/i }),
    ).toBeVisible();
  }

  async close() {
    // Settings modal has no close button — dismiss with Escape key.
    await this.page.keyboard.press("Escape");
    await expect(this.page.getByRole("dialog")).not.toBeVisible({ timeout: 5_000 });
  }

  async openTab(tabName: "General" | "Data" | "Advanced") {
    await this.page.getByRole("dialog").getByRole("button", { name: tabName }).click();
  }

  async expectTabVisible(tabName: "General" | "Data" | "Advanced") {
    await expect(
      this.page.getByRole("dialog").getByRole("button", { name: tabName }),
    ).toBeVisible();
  }

  async expectThreeTabsVisible() {
    for (const tab of ["General", "Data", "Advanced"] as const) {
      await this.expectTabVisible(tab);
    }
  }
}

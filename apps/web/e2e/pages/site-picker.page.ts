import { type Locator, type Page, expect } from "@playwright/test";

export class SitePickerComponent {
  readonly select: Locator;

  constructor(private page: Page) {
    // The site-select testid only appears on the SitePicker with showSelect=true.
    this.select = page.getByTestId("site-select");
  }

  async selectSite(siteId: string) {
    // Native <select> element — use selectOption with the value attribute.
    await this.select.selectOption(siteId);
  }

  async confirmSwitch() {
    await this.page.getByRole("button", { name: /switch site/i }).click();
  }

  async cancelSwitch() {
    await this.page.getByRole("button", { name: /cancel/i }).click();
  }

  async expectCurrentSite(siteId: string) {
    await expect(this.select).toHaveValue(siteId);
  }
}

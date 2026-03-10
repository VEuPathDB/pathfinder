import { type Locator, type Page, expect } from "@playwright/test";

export class SidebarPage {
  readonly refreshButton: Locator;
  readonly newButton: Locator;
  readonly searchInput: Locator;

  constructor(private page: Page) {
    this.refreshButton = page.getByTestId("conversations-refresh-button");
    this.newButton = page.getByTestId("conversations-new-button");
    this.searchInput = page.getByTestId("conversations-search-input");
  }

  /** All conversation items in the sidebar. */
  get items(): Locator {
    return this.page.getByTestId("conversation-item");
  }

  /** A specific conversation by its data-conversation-id attribute. */
  item(conversationId: string): Locator {
    return this.page.locator(
      `[data-testid="conversation-item"][data-conversation-id="${conversationId}"]`,
    );
  }

  async createNew() {
    await this.newButton.click();
  }

  async search(query: string) {
    await this.searchInput.fill(query);
  }

  async clearSearch() {
    await this.searchInput.clear();
  }

  async selectConversation(conversationId: string) {
    await this.item(conversationId).click();
  }

  /** Open the dropdown menu on a conversation item via the "..." button. */
  private async openMenu(conversationId: string) {
    // Hover to reveal the overflow menu button, then click it
    await this.item(conversationId).hover();
    await this.item(conversationId)
      .getByRole("button", { name: /conversation actions/i })
      .click();
  }

  async rename(conversationId: string, newName: string) {
    await this.openMenu(conversationId);
    await this.page.getByRole("menuitem", { name: /rename/i }).click();
    const renameInput = this.page.getByTestId("conversation-rename-input");
    await renameInput.clear();
    await renameInput.fill(newName);
    await renameInput.press("Enter");
  }

  async delete(conversationId: string) {
    await this.openMenu(conversationId);
    await this.page.getByRole("menuitem", { name: /delete/i }).click();
    // Confirm in the delete modal
    await this.page
      .getByRole("dialog")
      .getByRole("button", { name: /delete/i })
      .click();
  }

  async duplicate(conversationId: string) {
    await this.openMenu(conversationId);
    await this.page.getByRole("menuitem", { name: /duplicate/i }).click();
  }

  async refresh() {
    await this.refreshButton.click();
  }

  async expectConversationCount(count: number) {
    await expect(this.items).toHaveCount(count);
  }

  async expectConversationVisible(conversationId: string) {
    await expect(this.item(conversationId)).toBeVisible();
  }

  async expectConversationName(conversationId: string, name: string | RegExp) {
    const pattern = typeof name === "string" ? new RegExp(name) : name;
    await expect(this.item(conversationId)).toContainText(pattern);
  }

  /** Get the first conversation item's data-conversation-id. */
  async firstConversationId(): Promise<string> {
    const first = this.items.first();
    await expect(first).toBeVisible({ timeout: 15_000 });
    return (await first.getAttribute("data-conversation-id")) ?? "";
  }
}

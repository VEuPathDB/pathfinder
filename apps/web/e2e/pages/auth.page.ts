import { type Locator, type Page, expect } from "@playwright/test";

export class AuthPage {
  readonly loginModal: Locator;
  readonly signInButton: Locator;

  constructor(private page: Page) {
    // LoginModal uses a Modal with title "Sign in to VEuPathDB"
    this.loginModal = page.getByRole("dialog").filter({ hasText: /sign in/i });
    this.signInButton = page.getByRole("button", { name: /sign in/i });
  }

  async expectLoginModal() {
    await expect(this.loginModal).toBeVisible();
  }

  async expectNoLoginModal() {
    await expect(this.loginModal).not.toBeVisible();
  }

  async expectSignedIn() {
    await expect(this.loginModal).not.toBeVisible();
    await expect(this.page.getByTestId("message-composer")).toBeVisible();
  }
}

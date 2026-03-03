import { test, expect } from "@playwright/test";
import { gotoHome, sendMessage } from "./helpers";

test("chat: send message from fresh home and see response", async ({ page }) => {
  await gotoHome(page);

  await sendMessage(page, "please help me plan a strategy");

  // The unified agent auto-creates a strategy-backed conversation.
  // The mock provider responds with a [mock] prefix.
  await expect(page.getByText("[mock]").first()).toBeVisible({
    timeout: 20_000,
  });

  // Verify our user message is visible in the transcript.
  await expect(
    page.getByText("please help me plan a strategy", { exact: true }).first(),
  ).toBeVisible();
});

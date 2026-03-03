import { test, expect } from "@playwright/test";
import {
  gotoHomeWithStrategy,
  sendMessage,
  expectStreaming,
  expectIdleComposer,
} from "./helpers";

test("chat: send message and see streamed response", async ({ page }) => {
  await gotoHomeWithStrategy(page);

  await sendMessage(page, "hello from e2e");

  await expect(page.getByText(/\[mock\]/).first()).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText("hello from e2e", { exact: true }).first()).toBeVisible();
});

test("chat: stop streaming returns to idle composer", async ({ page }) => {
  await gotoHomeWithStrategy(page);

  await sendMessage(page, "slow please");
  await expectStreaming(page);
  await page.getByTestId("stop-button").click();

  await expectIdleComposer(page);
});

test("chat: shows error for failed POST and recovers", async ({ page }) => {
  // Fail only the first chat request (the POST that starts the operation).
  await page.route(
    "**/api/v1/chat",
    async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "text/plain",
        body: "boom",
      });
    },
    { times: 1 },
  );

  await gotoHomeWithStrategy(page);

  await sendMessage(page, "please fail once");
  // The error message comes from requestJson; match broadly for HTTP error text.
  await expect(page.getByText(/HTTP 500|error|failed/i).first()).toBeVisible();
  await expectIdleComposer(page);

  // Next request should succeed.
  await sendMessage(page, "hello after failure");
  await expect(page.getByText(/\[mock\]/).first()).toBeVisible({
    timeout: 20_000,
  });
});

import { test } from "../fixtures/test";

test.describe("Settings", () => {
  test.beforeEach(async ({ chatPage }) => {
    await chatPage.goto();
  });

  test("open settings shows three tabs", async ({ settingsPage }) => {
    await settingsPage.open();
    await settingsPage.expectThreeTabsVisible();
  });

  test("switch between settings tabs", async ({ settingsPage }) => {
    await settingsPage.open();

    await settingsPage.openTab("Data");
    await settingsPage.openTab("Advanced");
    await settingsPage.openTab("General");
  });

  test("close settings modal", async ({ settingsPage }) => {
    await settingsPage.open();
    await settingsPage.close();
  });
});

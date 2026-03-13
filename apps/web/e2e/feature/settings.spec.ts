import { test } from "../fixtures/test";

test.describe("Settings", () => {
  test.beforeEach(async ({ chatPage }) => {
    await chatPage.goto();
  });

  test("open settings shows all tabs", async ({ settingsPage }) => {
    await settingsPage.open();
    await settingsPage.expectAllTabsVisible();
  });

  test("switch between settings tabs", async ({ settingsPage }) => {
    await settingsPage.open();

    await settingsPage.openTab("Data");
    await settingsPage.openTab("Advanced");
    await settingsPage.openTab("Seeding");
    await settingsPage.openTab("Model");
  });

  test("close settings modal", async ({ settingsPage }) => {
    await settingsPage.open();
    await settingsPage.close();
  });
});

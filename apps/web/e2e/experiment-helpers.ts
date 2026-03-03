import { type Page } from "@playwright/test";
import { setupAuth } from "./helpers";

/**
 * Navigate to the experiments tab with authentication.
 */
export async function gotoExperiments(page: Page): Promise<void> {
  await setupAuth(page);
  await page.goto("/experiments");
}

/**
 * Start a new experiment by clicking the "New Experiment" button
 * and selecting the specified mode.
 */
export async function startNewExperiment(
  page: Page,
  mode: "single" | "multistep" | "import" = "multistep",
): Promise<void> {
  // Click the new experiment button (use .first() as both the empty state and
  // the header may render a "New Experiment" button simultaneously).
  await page
    .getByRole("button", { name: /new experiment/i })
    .first()
    .click();
  // Select mode - look for mode-specific button or option
  if (mode === "single") {
    await page.getByTestId("mode-single").click();
  } else if (mode === "multistep") {
    await page.getByTestId("mode-multistep").click();
  } else {
    await page.getByTestId("mode-import").click();
  }
}

/**
 * Mock the experiment list API endpoint.
 */
export async function mockExperimentList(
  page: Page,
  experiments: object[],
): Promise<void> {
  await page.route("**/api/v1/experiments", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(experiments),
      });
    } else {
      await route.continue();
    }
  });
}

/**
 * Mock the experiment creation endpoint.
 *
 * The real endpoint returns 202 JSON `{operationId}` (fire-and-forget),
 * then the client subscribes to GET /operations/{id}/subscribe for SSE.
 * This helper intercepts both the POST (returns a mock operationId) and
 * the subscribe GET (returns SSE events).
 */
export async function mockExperimentSSE(
  page: Page,
  events: Array<{ type: string; data: object }>,
): Promise<void> {
  const mockOperationId = `mock_op_${Date.now()}`;

  // Intercept the POST to return a 202 with operationId.
  await page.route("**/api/v1/experiments", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({ operationId: mockOperationId }),
      });
    } else {
      await route.continue();
    }
  });

  // Intercept the subscribe SSE endpoint to return mock events.
  await page.route(
    `**/api/v1/operations/${mockOperationId}/subscribe`,
    async (route) => {
      const sseBody = events
        .map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e.data)}\n\n`)
        .join("");
      const endFrame = `event: experiment_end\ndata: {}\n\n`;

      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: {
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
        body: sseBody + endFrame,
      });
    },
  );
}

// Re-export types for convenience
export type MockExperiment = {
  id: string;
  status: string;
  name: string;
  config: {
    siteId: string;
    recordType: string;
    searchName: string;
    mode: string;
  };
};

/**
 * Create a minimal mock experiment object for use with mockExperimentList.
 */
export function createMockExperiment(
  overrides: Partial<MockExperiment> = {},
): MockExperiment {
  return {
    id: `exp_${Date.now()}`,
    status: "completed",
    name: "Test Experiment",
    config: {
      siteId: "PlasmoDB",
      recordType: "gene",
      searchName: "GenesByTaxon",
      mode: "multi-step",
    },
    ...overrides,
  };
}

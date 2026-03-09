// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { BlockingOverlay } from "./BlockingOverlay";

describe("BlockingOverlay", () => {
  it("renders message to select a gene set", () => {
    render(<BlockingOverlay />);
    expect(screen.getByText("Select a gene set to begin")).toBeTruthy();
  });

  it("has data attribute for testing", () => {
    const { container } = render(<BlockingOverlay />);
    const overlay = container.querySelector("[data-blocking-overlay]");
    expect(overlay).toBeTruthy();
  });
});

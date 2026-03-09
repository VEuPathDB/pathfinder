// @vitest-environment jsdom
import { afterEach, describe, it, expect, vi } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { VennDiagram } from "./VennDiagram";

afterEach(cleanup);

describe("VennDiagram", () => {
  const setA = { name: "Set A", geneIds: ["g1", "g2", "g3"] };
  const setB = { name: "Set B", geneIds: ["g2", "g3", "g4", "g5"] };

  it("renders region counts", () => {
    render(<VennDiagram setA={setA} setB={setB} onRegionClick={vi.fn()} />);
    // Only A: g1 (1), Shared: g2,g3 (2), Only B: g4,g5 (2)
    expect(screen.getByTestId("count-only-a").textContent).toBe("1");
    expect(screen.getByTestId("count-shared").textContent).toBe("2");
    expect(screen.getByTestId("count-only-b").textContent).toBe("2");
  });

  it("renders set name labels above the diagram", () => {
    render(<VennDiagram setA={setA} setB={setB} onRegionClick={vi.fn()} />);
    // Labels are in <span> elements with title attributes
    const spans = screen.getAllByTitle("Set A");
    expect(spans.length).toBeGreaterThan(0);
    expect(spans[0].textContent).toBe("Set A");

    const spansB = screen.getAllByTitle("Set B");
    expect(spansB.length).toBeGreaterThan(0);
    expect(spansB[0].textContent).toBe("Set B");
  });

  it("calls onRegionClick with only-A gene IDs when that region is clicked", () => {
    const handler = vi.fn();
    render(<VennDiagram setA={setA} setB={setB} onRegionClick={handler} />);
    const onlyARegion = screen.getByRole("button", {
      name: /Only Set A: 1 genes/,
    });
    fireEvent.click(onlyARegion);
    expect(handler).toHaveBeenCalledWith(["g1"], expect.stringContaining("Set A"));
  });

  it("calls onRegionClick with only-B gene IDs when that region is clicked", () => {
    const handler = vi.fn();
    render(<VennDiagram setA={setA} setB={setB} onRegionClick={handler} />);
    const onlyBRegion = screen.getByRole("button", {
      name: /Only Set B: 2 genes/,
    });
    fireEvent.click(onlyBRegion);
    expect(handler).toHaveBeenCalledWith(
      ["g4", "g5"],
      expect.stringContaining("Set B"),
    );
  });

  it("calls onRegionClick with shared gene IDs when the intersection is clicked", () => {
    const handler = vi.fn();
    render(<VennDiagram setA={setA} setB={setB} onRegionClick={handler} />);
    const sharedRegion = screen.getByRole("button", {
      name: /Shared: 2 genes/,
    });
    fireEvent.click(sharedRegion);
    expect(handler).toHaveBeenCalledWith(
      ["g2", "g3"],
      expect.stringContaining("\u2229"),
    );
  });

  it("renders the instructional text", () => {
    render(<VennDiagram setA={setA} setB={setB} onRegionClick={vi.fn()} />);
    expect(screen.getByText("Click a region to create a gene set")).toBeTruthy();
  });

  it("handles empty sets gracefully", () => {
    const emptyA = { name: "Empty", geneIds: [] as string[] };
    render(<VennDiagram setA={emptyA} setB={setB} onRegionClick={vi.fn()} />);
    expect(screen.getByTestId("count-only-a").textContent).toBe("0");
    expect(screen.getByTestId("count-shared").textContent).toBe("0");
    expect(screen.getByTestId("count-only-b").textContent).toBe("4");
  });

  it("handles fully overlapping sets", () => {
    const same = { name: "Same", geneIds: ["g1", "g2"] };
    render(<VennDiagram setA={same} setB={same} onRegionClick={vi.fn()} />);
    expect(screen.getByTestId("count-only-a").textContent).toBe("0");
    expect(screen.getByTestId("count-shared").textContent).toBe("2");
    expect(screen.getByTestId("count-only-b").textContent).toBe("0");
  });
});

/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, it, expect } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ExpandedRowDetail } from "./ExpandedRowDetail";
import type { RecordDetail } from "@/lib/types/wdk";

describe("ExpandedRowDetail", () => {
  afterEach(cleanup);

  const baseProps = {
    pk: "PF3D7_0102600",
    error: null,
    loading: false,
    onClose: () => {},
  };

  it("renders attribute values using display names from attributeNames", () => {
    const detail: RecordDetail = {
      attributes: {
        gene_product: "serine/threonine protein kinase",
        organism: "Plasmodium falciparum 3D7",
      },
      attributeNames: {
        gene_product: "Product Description",
        organism: "Organism",
      },
    };

    render(<ExpandedRowDetail {...baseProps} detail={detail} />);

    // Should use display name, not raw field name
    expect(screen.getByText("Product Description")).toBeTruthy();
    expect(screen.getByText("Organism")).toBeTruthy();
    // Should render values
    expect(screen.getByText("serine/threonine protein kinase")).toBeTruthy();
    expect(screen.getByText("Plasmodium falciparum 3D7")).toBeTruthy();
  });

  it("falls back to raw field name when attributeNames is missing", () => {
    const detail: RecordDetail = {
      attributes: {
        gene_product: "kinase",
      },
    };

    render(<ExpandedRowDetail {...baseProps} detail={detail} />);

    expect(screen.getByText("gene_product")).toBeTruthy();
    expect(screen.getByText("kinase")).toBeTruthy();
  });

  it("shows loading state", () => {
    render(<ExpandedRowDetail {...baseProps} detail={null} loading />);

    expect(screen.getByText("Loading details…")).toBeTruthy();
  });

  it("shows error state", () => {
    render(<ExpandedRowDetail {...baseProps} detail={null} error="Request failed" />);

    expect(screen.getByText("Request failed")).toBeTruthy();
  });

  it("shows fallback when detail has no attributes", () => {
    const detail: RecordDetail = {
      attributes: {},
    };

    render(<ExpandedRowDetail {...baseProps} detail={detail} />);

    expect(screen.getByText("Unable to load details.")).toBeTruthy();
  });
});

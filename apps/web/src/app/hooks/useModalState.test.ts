/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useModalState } from "./useModalState";

describe("useModalState", () => {
  // ---------------------------------------------------------------------------
  // Initial state
  // ---------------------------------------------------------------------------

  it("starts with all modals closed and no pending site change", () => {
    const { result } = renderHook(() => useModalState());

    expect(result.current.showSettings).toBe(false);
    expect(result.current.graphEditing).toBe(false);
    expect(result.current.pendingSiteChange).toBeNull();
  });

  // ---------------------------------------------------------------------------
  // Settings modal
  // ---------------------------------------------------------------------------

  describe("settings modal", () => {
    it("opens the settings modal", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.openSettings());

      expect(result.current.showSettings).toBe(true);
    });

    it("closes the settings modal", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.openSettings());
      act(() => result.current.closeSettings());

      expect(result.current.showSettings).toBe(false);
    });

    it("closing an already-closed settings modal is a no-op", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.closeSettings());

      expect(result.current.showSettings).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // Graph editor modal
  // ---------------------------------------------------------------------------

  describe("graph editor modal", () => {
    it("opens the graph editor", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.openGraphEditor());

      expect(result.current.graphEditing).toBe(true);
    });

    it("closes the graph editor", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.openGraphEditor());
      act(() => result.current.closeGraphEditor());

      expect(result.current.graphEditing).toBe(false);
    });

    it("closing an already-closed graph editor is a no-op", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.closeGraphEditor());

      expect(result.current.graphEditing).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // Pending site change
  // ---------------------------------------------------------------------------

  describe("pending site change", () => {
    it("sets a pending site change", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.setPendingSiteChange("toxodb"));

      expect(result.current.pendingSiteChange).toBe("toxodb");
    });

    it("updates the pending site change to a different site", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.setPendingSiteChange("toxodb"));
      act(() => result.current.setPendingSiteChange("cryptodb"));

      expect(result.current.pendingSiteChange).toBe("cryptodb");
    });

    it("clears the pending site change", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.setPendingSiteChange("toxodb"));
      act(() => result.current.clearPendingSiteChange());

      expect(result.current.pendingSiteChange).toBeNull();
    });

    it("clearing when already null is a no-op", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.clearPendingSiteChange());

      expect(result.current.pendingSiteChange).toBeNull();
    });

    it("can set pending site change to null directly via setPendingSiteChange", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.setPendingSiteChange("toxodb"));
      act(() => result.current.setPendingSiteChange(null));

      expect(result.current.pendingSiteChange).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Independence
  // ---------------------------------------------------------------------------

  describe("modal independence", () => {
    it("opening settings does not affect graph editor or pending site change", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.openSettings());

      expect(result.current.showSettings).toBe(true);
      expect(result.current.graphEditing).toBe(false);
      expect(result.current.pendingSiteChange).toBeNull();
    });

    it("opening graph editor does not affect settings or pending site change", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.openGraphEditor());

      expect(result.current.showSettings).toBe(false);
      expect(result.current.graphEditing).toBe(true);
      expect(result.current.pendingSiteChange).toBeNull();
    });

    it("setting pending site change does not affect settings or graph editor", () => {
      const { result } = renderHook(() => useModalState());

      act(() => result.current.setPendingSiteChange("plasmodb"));

      expect(result.current.showSettings).toBe(false);
      expect(result.current.graphEditing).toBe(false);
      expect(result.current.pendingSiteChange).toBe("plasmodb");
    });

    it("all three states can be active simultaneously", () => {
      const { result } = renderHook(() => useModalState());

      act(() => {
        result.current.openSettings();
        result.current.openGraphEditor();
        result.current.setPendingSiteChange("fungidb");
      });

      expect(result.current.showSettings).toBe(true);
      expect(result.current.graphEditing).toBe(true);
      expect(result.current.pendingSiteChange).toBe("fungidb");
    });
  });

  // ---------------------------------------------------------------------------
  // Callback identity stability
  // ---------------------------------------------------------------------------

  describe("callback stability", () => {
    it("returns stable callback references across renders", () => {
      const { result, rerender } = renderHook(() => useModalState());

      const firstRender = {
        openSettings: result.current.openSettings,
        closeSettings: result.current.closeSettings,
        openGraphEditor: result.current.openGraphEditor,
        closeGraphEditor: result.current.closeGraphEditor,
        clearPendingSiteChange: result.current.clearPendingSiteChange,
      };

      rerender();

      expect(result.current.openSettings).toBe(firstRender.openSettings);
      expect(result.current.closeSettings).toBe(firstRender.closeSettings);
      expect(result.current.openGraphEditor).toBe(firstRender.openGraphEditor);
      expect(result.current.closeGraphEditor).toBe(firstRender.closeGraphEditor);
      expect(result.current.clearPendingSiteChange).toBe(
        firstRender.clearPendingSiteChange,
      );
    });
  });
});

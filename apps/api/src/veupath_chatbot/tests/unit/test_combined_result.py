"""Tests for the shared combined_result utility."""

from veupath_chatbot.ai.tools.combined_result import combined_result


class TestCombinedResult:
    def test_basic_structure(self) -> None:
        result = combined_result(rag="rag_data", wdk="wdk_data")
        assert result == {
            "rag": {"data": "rag_data", "note": ""},
            "wdk": {"data": "wdk_data", "note": ""},
        }

    def test_with_notes(self) -> None:
        result = combined_result(
            rag=[1, 2],
            wdk={"key": "val"},
            rag_note="RAG note",
            wdk_note="WDK note",
        )
        assert result == {
            "rag": {"data": [1, 2], "note": "RAG note"},
            "wdk": {"data": {"key": "val"}, "note": "WDK note"},
        }

    def test_none_data(self) -> None:
        result = combined_result(rag=None, wdk=None)
        assert result["rag"]["data"] is None
        assert result["wdk"]["data"] is None
        assert result["rag"]["note"] == ""
        assert result["wdk"]["note"] == ""

    def test_none_notes_become_empty_string(self) -> None:
        result = combined_result(rag="x", wdk="y", rag_note=None, wdk_note=None)
        assert result["rag"]["note"] == ""
        assert result["wdk"]["note"] == ""

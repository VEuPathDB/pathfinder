"""Tests for vectorstore ingest utility functions."""

from veupath_chatbot.integrations.vectorstore.ingest.utils import (
    extract_search_name,
    parse_sites,
)


class TestExtractSearchName:
    def test_prefers_url_segment(self) -> None:
        obj = {"urlSegment": "transcript", "name": "TranscriptRecordClasses"}
        assert extract_search_name(obj) == "transcript"

    def test_falls_back_to_name(self) -> None:
        obj = {"name": "GenesByText"}
        assert extract_search_name(obj) == "GenesByText"

    def test_strips_whitespace(self) -> None:
        obj = {"urlSegment": "  transcript  "}
        assert extract_search_name(obj) == "transcript"

    def test_empty_url_segment_falls_to_name(self) -> None:
        obj = {"urlSegment": "", "name": "fallback"}
        assert extract_search_name(obj) == "fallback"

    def test_both_missing_returns_empty(self) -> None:
        assert extract_search_name({}) == ""

    def test_none_values_return_empty(self) -> None:
        obj = {"urlSegment": None, "name": None}
        assert extract_search_name(obj) == ""


class TestParseSites:
    def test_all_returns_none(self) -> None:
        assert parse_sites("all") is None

    def test_empty_returns_none(self) -> None:
        assert parse_sites("") is None

    def test_whitespace_returns_none(self) -> None:
        assert parse_sites("   ") is None

    def test_single_site(self) -> None:
        assert parse_sites("plasmodb") == ["plasmodb"]

    def test_multiple_sites(self) -> None:
        result = parse_sites("plasmodb,toxodb,cryptodb")
        assert result == ["plasmodb", "toxodb", "cryptodb"]

    def test_strips_whitespace(self) -> None:
        result = parse_sites("  plasmodb , toxodb  ")
        assert result == ["plasmodb", "toxodb"]

    def test_ignores_empty_segments(self) -> None:
        result = parse_sites("plasmodb,,toxodb,")
        assert result == ["plasmodb", "toxodb"]

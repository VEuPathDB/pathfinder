"""Tests for vectorstore ingest utility functions."""

from veupath_chatbot.integrations.vectorstore.ingest.utils import parse_sites


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

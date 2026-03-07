"""Unit tests for services.strategies.engine.id_mapping.IdMappingMixin."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veupath_chatbot.domain.strategy.ast import PlanStepNode
from veupath_chatbot.domain.strategy.session import StrategySession
from veupath_chatbot.services.strategies.engine.helpers import StrategyToolsHelpers


def _make_session(site_id: str = "plasmodb") -> StrategySession:
    session = StrategySession(site_id)
    session.create_graph("Test", graph_id="g1")
    return session


def _make_mixin(session: StrategySession | None = None) -> StrategyToolsHelpers:
    if session is None:
        session = _make_session()
    return StrategyToolsHelpers(session)


# -- _infer_record_type ---------------------------------------------------


class TestInferRecordType:
    def test_returns_graph_record_type(self) -> None:
        session = _make_session()
        graph = session.get_graph("g1")
        assert graph is not None
        graph.record_type = "gene"
        mixin = _make_mixin(session)
        step = PlanStepNode(search_name="S1", parameters={}, id="s1")
        assert mixin._infer_record_type(step) == "gene"

    def test_returns_none_when_no_graph(self) -> None:
        session = StrategySession("plasmodb")
        mixin = StrategyToolsHelpers(session)
        step = PlanStepNode(search_name="S1", parameters={}, id="s1")
        assert mixin._infer_record_type(step) is None

    def test_returns_none_when_graph_has_no_record_type(self) -> None:
        session = _make_session()
        graph = session.get_graph("g1")
        assert graph is not None
        graph.record_type = None
        mixin = _make_mixin(session)
        step = PlanStepNode(search_name="S1", parameters={}, id="s1")
        assert mixin._infer_record_type(step) is None


# -- _resolve_record_type -------------------------------------------------


class TestResolveRecordType:
    @pytest.mark.asyncio
    async def test_returns_none_for_none_input(self) -> None:
        mixin = _make_mixin()
        assert await mixin._resolve_record_type(None) is None

    @pytest.mark.asyncio
    async def test_returns_empty_string_for_empty_input(self) -> None:
        """Empty string is falsy, so _resolve_record_type returns it unchanged."""
        mixin = _make_mixin()
        result = await mixin._resolve_record_type("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_exact_match_string_record_type(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene", "transcript"])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type("gene")
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene", "transcript"])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type("GENE")
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_match_by_url_segment_in_dict(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(
            return_value=[
                {"urlSegment": "gene", "name": "Gene", "displayName": "Genes"},
            ]
        )
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type("gene")
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_match_by_name_in_dict(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(
            return_value=[
                {"urlSegment": "gene", "name": "Gene", "displayName": "Genes"},
            ]
        )
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            # Matching by the "name" field when urlSegment doesn't match
            result = await mixin._resolve_record_type("Gene")
            assert result == "gene"  # Should return urlSegment

    @pytest.mark.asyncio
    async def test_match_by_display_name_single(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(
            return_value=[
                {"urlSegment": "gene", "name": "Gene", "displayName": "Genes"},
                {
                    "urlSegment": "transcript",
                    "name": "Transcript",
                    "displayName": "EST",
                },
            ]
        )
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type("Genes")
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_no_match_returns_original(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene", "transcript"])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type("nonexistent")
            assert result == "nonexistent"

    @pytest.mark.asyncio
    async def test_whitespace_trimmed(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene"])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type("  gene  ")
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_dict_without_url_segment_falls_back_to_name(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=[{"name": "Gene"}])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type("Gene")
            assert result == "Gene"

    @pytest.mark.asyncio
    async def test_non_string_non_dict_entries_skipped(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(
            return_value=[42, None, True, "gene"]
        )
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type("gene")
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_ambiguous_display_name_returns_original(self) -> None:
        """When multiple record types share the same displayName, return the input."""
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(
            return_value=[
                {"urlSegment": "gene", "name": "Gene", "displayName": "Records"},
                {
                    "urlSegment": "transcript",
                    "name": "Transcript",
                    "displayName": "Records",
                },
            ]
        )
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type("Records")
            # Multiple display matches -> fallback to original input
            assert result == "Records"


# -- _resolve_record_type_for_search ---------------------------------------


class TestResolveRecordTypeForSearch:
    @pytest.mark.asyncio
    async def test_no_search_name_returns_resolved_record_type(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene"])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type_for_search("gene", None)
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_search_found_in_resolved_record_type(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene"])
        mock_discovery.get_searches = AsyncMock(
            return_value=[
                {"urlSegment": "GenesByTextSearch", "name": "GenesByTextSearch"}
            ]
        )
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type_for_search(
                "gene", "GenesByTextSearch"
            )
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_search_not_found_falls_back_to_other_record_types(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene", "transcript"])

        async def mock_get_searches(site_id: str, record_type: str):
            if record_type == "gene":
                return []
            if record_type == "transcript":
                return [{"urlSegment": "TranscriptSearch", "name": "TranscriptSearch"}]
            return []

        mock_discovery.get_searches = AsyncMock(side_effect=mock_get_searches)
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type_for_search(
                "gene", "TranscriptSearch"
            )
            assert result == "transcript"

    @pytest.mark.asyncio
    async def test_require_match_returns_none_when_not_found(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene"])
        mock_discovery.get_searches = AsyncMock(return_value=[])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type_for_search(
                "gene", "NonexistentSearch", require_match=True
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_no_fallback_returns_resolved(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene"])
        mock_discovery.get_searches = AsyncMock(return_value=[])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type_for_search(
                "gene", "NonexistentSearch", allow_fallback=False
            )
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_no_fallback_require_match_returns_none(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene"])
        mock_discovery.get_searches = AsyncMock(return_value=[])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type_for_search(
                "gene", "X", require_match=True, allow_fallback=False
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_search_exception_skipped_gracefully(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene"])
        mock_discovery.get_searches = AsyncMock(side_effect=RuntimeError("network"))
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type_for_search(
                "gene", "GenesByTextSearch"
            )
            # When initial search fails and fallback loops also fail,
            # returns resolved (no require_match)
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_none_record_type_with_search_name(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene"])
        mock_discovery.get_searches = AsyncMock(
            return_value=[
                {"urlSegment": "GenesByTextSearch", "name": "GenesByTextSearch"}
            ]
        )
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._resolve_record_type_for_search(
                None, "GenesByTextSearch"
            )
            # Falls back to searching all record types
            assert result == "gene"


# -- _find_record_type_hint ------------------------------------------------


class TestFindRecordTypeHint:
    @pytest.mark.asyncio
    async def test_finds_record_type_for_search(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene", "transcript"])

        async def mock_get_searches(site_id: str, record_type: str):
            if record_type == "gene":
                return [
                    {"urlSegment": "GenesByTextSearch", "name": "GenesByTextSearch"}
                ]
            return []

        mock_discovery.get_searches = AsyncMock(side_effect=mock_get_searches)
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._find_record_type_hint("GenesByTextSearch")
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene"])
        mock_discovery.get_searches = AsyncMock(return_value=[])
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._find_record_type_hint("NonexistentSearch")
            assert result is None

    @pytest.mark.asyncio
    async def test_excludes_specified_record_type(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene", "transcript"])

        async def mock_get_searches(site_id: str, record_type: str):
            return [{"urlSegment": "SharedSearch", "name": "SharedSearch"}]

        mock_discovery.get_searches = AsyncMock(side_effect=mock_get_searches)
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._find_record_type_hint("SharedSearch", exclude="gene")
            assert result == "transcript"

    @pytest.mark.asyncio
    async def test_handles_discovery_exception(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(side_effect=RuntimeError("fail"))
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._find_record_type_hint("AnySearch")
            assert result is None

    @pytest.mark.asyncio
    async def test_skips_empty_record_type_names(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(
            return_value=[
                {"urlSegment": "", "name": ""},
                "gene",
            ]
        )
        mock_discovery.get_searches = AsyncMock(
            return_value=[
                {"urlSegment": "GenesByTextSearch", "name": "GenesByTextSearch"}
            ]
        )
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._find_record_type_hint("GenesByTextSearch")
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_handles_dict_record_type_entries(self) -> None:
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(
            return_value=[
                {"urlSegment": "gene", "name": "Gene"},
            ]
        )
        mock_discovery.get_searches = AsyncMock(
            return_value=[
                {"urlSegment": "GenesByTextSearch", "name": "GenesByTextSearch"}
            ]
        )
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._find_record_type_hint("GenesByTextSearch")
            assert result == "gene"

    @pytest.mark.asyncio
    async def test_search_exception_continues_to_next(self) -> None:
        """When get_searches raises for one record type, continues to others."""
        mock_discovery = MagicMock()
        mock_discovery.get_record_types = AsyncMock(return_value=["gene", "transcript"])
        call_count = 0

        async def mock_get_searches(site_id: str, record_type: str):
            nonlocal call_count
            call_count += 1
            if record_type == "gene":
                raise RuntimeError("network error")
            return [{"urlSegment": "TranscriptSearch", "name": "TranscriptSearch"}]

        mock_discovery.get_searches = AsyncMock(side_effect=mock_get_searches)
        with patch(
            "veupath_chatbot.services.strategies.engine.id_mapping.get_discovery_service",
            return_value=mock_discovery,
        ):
            mixin = _make_mixin()
            result = await mixin._find_record_type_hint("TranscriptSearch")
            assert result == "transcript"
            assert call_count == 2

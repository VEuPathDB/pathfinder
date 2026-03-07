"""Unit tests for services.strategies.engine.validation.ValidationMixin."""

from veupath_chatbot.domain.strategy.session import StrategySession
from veupath_chatbot.platform.errors import ErrorCode, ValidationError
from veupath_chatbot.platform.tool_errors import tool_error
from veupath_chatbot.services.strategies.engine.validation import ValidationMixin


def _make_session(graph_id: str = "g1", graph_name: str = "Test") -> StrategySession:
    session = StrategySession("plasmodb")
    session.create_graph(graph_name, graph_id=graph_id)
    return session


def _make_mixin(session: StrategySession | None = None) -> ValidationMixin:
    if session is None:
        session = _make_session()
    return ValidationMixin(session)


# ── _get_graph ────────────────────────────────────────────────────────


class TestGetGraph:
    def test_returns_graph_for_matching_id(self) -> None:
        mixin = _make_mixin()
        graph = mixin._get_graph("g1")
        assert graph is not None
        assert graph.id == "g1"

    def test_returns_active_graph_for_none(self) -> None:
        mixin = _make_mixin()
        graph = mixin._get_graph(None)
        assert graph is not None
        assert graph.id == "g1"

    def test_returns_active_graph_for_invalid_id(self) -> None:
        """Falls back to active graph when ID doesn't match."""
        mixin = _make_mixin()
        graph = mixin._get_graph("nonexistent")
        assert graph is not None
        assert graph.id == "g1"

    def test_returns_none_when_no_graph(self) -> None:
        session = StrategySession("plasmodb")
        mixin = ValidationMixin(session)
        graph = mixin._get_graph(None)
        assert graph is None


# ── _graph_not_found ──────────────────────────────────────────────────


class TestGraphNotFound:
    def test_with_graph_id(self) -> None:
        mixin = _make_mixin()
        result = mixin._graph_not_found("g99")
        assert result["ok"] is False
        assert result["code"] == ErrorCode.NOT_FOUND
        assert "graphId" in (result.get("details") or result)

    def test_without_graph_id(self) -> None:
        mixin = _make_mixin()
        result = mixin._graph_not_found(None)
        assert result["ok"] is False
        assert "Provide a graphId" in result["message"]


# ── _validation_error_payload ─────────────────────────────────────────


class TestValidationErrorPayload:
    def test_basic_validation_error(self) -> None:
        mixin = _make_mixin()
        exc = ValidationError(title="Bad input", detail="Missing field X")
        result = mixin._validation_error_payload(exc)
        assert result["ok"] is False
        assert result["code"] == ErrorCode.VALIDATION_ERROR
        assert result["message"] == "Bad input"

    def test_with_errors_list(self) -> None:
        mixin = _make_mixin()
        exc = ValidationError(
            title="Invalid",
            errors=[{"path": "root.searchName", "message": "Missing", "code": "REQ"}],
        )
        result = mixin._validation_error_payload(exc)
        details = result.get("details", {})
        assert "errors" in details

    def test_with_extra_context(self) -> None:
        mixin = _make_mixin()
        exc = ValidationError(title="Fail")
        result = mixin._validation_error_payload(exc, graphId="g1", stepId="s1")
        # Context should be present
        details = result.get("details", {})
        assert details.get("graphId") == "g1" or result.get("graphId") == "g1"

    def test_errors_with_nested_context(self) -> None:
        mixin = _make_mixin()
        exc = ValidationError(
            title="Fail",
            errors=[
                {
                    "path": "root",
                    "message": "Bad",
                    "code": "ERR",
                    "context": {"searchName": "S1"},
                }
            ],
        )
        result = mixin._validation_error_payload(exc)
        # The nested context should be extracted
        assert result.get("searchName") == "S1" or (
            result.get("details", {}).get("searchName") == "S1"
        )


# ── tool_error ────────────────────────────────────────────────────────


class TestToolError:
    def test_produces_standard_payload(self) -> None:
        result = tool_error(ErrorCode.NOT_FOUND, "Step not found", stepId="s1")
        assert result["ok"] is False
        assert result["code"] == "NOT_FOUND"
        assert result["message"] == "Step not found"

    def test_with_string_code(self) -> None:
        result = tool_error("CUSTOM_CODE", "Custom error")
        assert result["code"] == "CUSTOM_CODE"


# ── _is_placeholder_name ─────────────────────────────────────────────


class TestIsPlaceholderName:
    def test_none_is_placeholder(self) -> None:
        mixin = _make_mixin()
        assert mixin._is_placeholder_name(None) is True

    def test_empty_string_is_placeholder(self) -> None:
        mixin = _make_mixin()
        assert mixin._is_placeholder_name("") is True

    def test_draft_graph_is_placeholder(self) -> None:
        mixin = _make_mixin()
        assert mixin._is_placeholder_name("Draft Graph") is True
        assert mixin._is_placeholder_name("draft graph") is True
        assert mixin._is_placeholder_name("  Draft Graph  ") is True

    def test_draft_strategy_is_placeholder(self) -> None:
        mixin = _make_mixin()
        assert mixin._is_placeholder_name("Draft Strategy") is True
        assert mixin._is_placeholder_name("DRAFT STRATEGY") is True

    def test_draft_is_placeholder(self) -> None:
        mixin = _make_mixin()
        assert mixin._is_placeholder_name("Draft") is True
        assert mixin._is_placeholder_name("draft") is True

    def test_real_name_is_not_placeholder(self) -> None:
        mixin = _make_mixin()
        assert mixin._is_placeholder_name("Gene Search for kinase") is False

    def test_partial_match_is_not_placeholder(self) -> None:
        mixin = _make_mixin()
        assert mixin._is_placeholder_name("Draft of kinase search") is False

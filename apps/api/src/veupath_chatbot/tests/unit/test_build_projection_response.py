"""Tests for build_projection_response message validation resilience."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from veupath_chatbot.transport.http.routers.strategies._shared import (
    build_projection_response,
)


def _make_projection(**overrides):
    """Create a minimal mock StreamProjection."""
    stream = MagicMock()
    stream.created_at = datetime.now(UTC)
    stream.site_id = overrides.get("site_id", "plasmodb")

    proj = MagicMock()
    proj.stream_id = overrides.get("stream_id", uuid4())
    proj.name = overrides.get("name", "Test Strategy")
    proj.record_type = overrides.get("record_type")
    proj.wdk_strategy_id = overrides.get("wdk_strategy_id")
    proj.is_saved = overrides.get("is_saved", False)
    proj.model_id = overrides.get("model_id")
    proj.message_count = overrides.get("message_count", 0)
    proj.step_count = overrides.get("step_count", 0)
    proj.plan = overrides.get("plan", {})
    proj.steps = overrides.get("steps", [])
    proj.root_step_id = overrides.get("root_step_id")
    proj.result_count = overrides.get("result_count")
    proj.updated_at = overrides.get("updated_at", datetime.now(UTC))
    proj.stream = stream
    proj.site_id = stream.site_id
    return proj


def _make_msg(role: str, content: str, **extra) -> dict:
    return {
        "role": role,
        "content": content,
        "timestamp": datetime.now(UTC).isoformat(),
        **extra,
    }


class TestBuildProjectionResponseMessages:
    def test_returns_messages_when_all_valid(self):
        proj = _make_projection()
        messages = [
            _make_msg("user", "hello"),
            _make_msg("assistant", "hi there"),
        ]
        resp = build_projection_response(proj, messages=messages)
        assert resp.messages is not None
        assert len(resp.messages) == 2
        assert resp.messages[0].role == "user"
        assert resp.messages[1].role == "assistant"

    def test_returns_none_when_no_messages(self):
        proj = _make_projection()
        resp = build_projection_response(proj)
        assert resp.messages is None

    def test_returns_none_when_messages_is_empty_list(self):
        proj = _make_projection()
        resp = build_projection_response(proj, messages=[])
        assert resp.messages is None

    def test_skips_malformed_message_keeps_valid_ones(self):
        """A single bad message should NOT drop all other valid messages."""
        proj = _make_projection()
        messages = [
            _make_msg("user", "hello"),
            {"role": "assistant"},  # missing required 'content' and 'timestamp'
            _make_msg("assistant", "I'm still here"),
        ]
        resp = build_projection_response(proj, messages=messages)
        assert resp.messages is not None
        assert len(resp.messages) == 2
        assert resp.messages[0].content == "hello"
        assert resp.messages[1].content == "I'm still here"

    def test_skips_non_dict_entries(self):
        proj = _make_projection()
        messages = [
            _make_msg("user", "hello"),
            "not a dict",  # type: ignore[list-item]
            42,  # type: ignore[list-item]
            _make_msg("assistant", "response"),
        ]
        resp = build_projection_response(proj, messages=messages)
        assert resp.messages is not None
        assert len(resp.messages) == 2

    def test_preserves_tool_calls(self):
        proj = _make_projection()
        messages = [
            _make_msg(
                "assistant",
                "Let me search for that",
                toolCalls=[{"id": "t1", "name": "search", "arguments": {"q": "gene"}}],
            ),
        ]
        resp = build_projection_response(proj, messages=messages)
        assert resp.messages is not None
        assert len(resp.messages) == 1
        assert resp.messages[0].tool_calls is not None
        assert resp.messages[0].tool_calls[0].name == "search"

    def test_all_messages_malformed_returns_none(self):
        proj = _make_projection()
        messages = [
            {"role": "user"},  # missing content and timestamp
            {"content": "no role"},  # missing role and timestamp
        ]
        resp = build_projection_response(proj, messages=messages)
        # All messages failed validation → msg_responses is empty → None
        assert resp.messages is None

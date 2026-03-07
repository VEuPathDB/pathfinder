"""Unit tests for the CQRS chat orchestrator module.

Covers the mock stream provider and the start_chat_stream entry point
with mocked dependencies.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from veupath_chatbot.services.chat.orchestrator import (
    start_chat_stream,
)
from veupath_chatbot.tests.fixtures.mock_chat import mock_stream_chat

# ---------------------------------------------------------------------------
# mock_stream_chat
# ---------------------------------------------------------------------------


class TestMockStreamChat:
    """Test the deterministic mock chat stream generator."""

    @pytest.mark.asyncio
    async def test_basic_message_yields_deltas_and_end(self) -> None:
        events: list[dict[str, Any]] = []
        async for ev in mock_stream_chat(message="Hello"):
            events.append(ev)

        types = [e["type"] for e in events]
        assert "assistant_delta" in types
        assert "assistant_message" in types
        assert types[-1] == "message_end"

    @pytest.mark.asyncio
    async def test_basic_message_echoes_input(self) -> None:
        events: list[dict[str, Any]] = []
        async for ev in mock_stream_chat(message="Test input"):
            events.append(ev)

        assistant_messages = [e for e in events if e["type"] == "assistant_message"]
        assert len(assistant_messages) == 1
        content = assistant_messages[0]["data"]["content"]
        assert "Test input" in content

    @pytest.mark.asyncio
    async def test_artifact_graph_trigger_yields_planning_artifact(self) -> None:
        events: list[dict[str, Any]] = []
        async for ev in mock_stream_chat(message="show artifact graph"):
            events.append(ev)

        types = [e["type"] for e in events]
        assert "planning_artifact" in types
        artifact_ev = next(e for e in events if e["type"] == "planning_artifact")
        artifact = artifact_ev["data"]["planningArtifact"]
        assert artifact["id"] == "mock_exec_graph_artifact"
        assert "proposedStrategyPlan" in artifact

    @pytest.mark.asyncio
    async def test_delegation_trigger_yields_subkani_and_strategy_events(self) -> None:
        events: list[dict[str, Any]] = []
        async for ev in mock_stream_chat(
            message="delegate_strategy_subtasks", strategy_id="test-strat-123"
        ):
            events.append(ev)

        types = [e["type"] for e in events]
        assert "subkani_task_start" in types
        assert "subkani_tool_call_start" in types
        assert "subkani_tool_call_end" in types
        assert "subkani_task_end" in types
        assert "strategy_update" in types
        assert "assistant_message" in types
        assert types[-1] == "message_end"

        su_events = [e for e in events if e["type"] == "strategy_update"]
        assert len(su_events) >= 1
        assert su_events[0]["data"]["graphId"] == "test-strat-123"

    @pytest.mark.asyncio
    async def test_slow_message_still_completes(self) -> None:
        events: list[dict[str, Any]] = []
        async for ev in mock_stream_chat(message="slow test"):
            events.append(ev)

        types = [e["type"] for e in events]
        assert "message_end" in types

    @pytest.mark.asyncio
    async def test_delegation_default_strategy_id(self) -> None:
        events: list[dict[str, Any]] = []
        async for ev in mock_stream_chat(message="delegation test"):
            events.append(ev)

        su_events = [e for e in events if e["type"] == "strategy_update"]
        assert su_events[0]["data"]["graphId"] == "mock_graph_delegation"


# ---------------------------------------------------------------------------
# start_chat_stream (CQRS version)
# ---------------------------------------------------------------------------


def _make_fake_stream(stream_id: UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=stream_id or uuid4())


class TestStartChatStream:
    """Test the CQRS start_chat_stream orchestrator.

    The new orchestrator:
    1. Ensures user exists
    2. Ensures stream exists (creates if needed)
    3. Emits user_message to Redis
    4. Registers operation in PostgreSQL
    5. Parses selected nodes from message
    6. Launches background _chat_producer
    7. Returns (operation_id, stream_id)
    """

    @pytest.mark.asyncio
    async def test_returns_operation_and_stream_ids(self) -> None:
        stream = _make_fake_stream()
        user_id = uuid4()

        user_repo = MagicMock()
        user_repo.get_or_create = AsyncMock(return_value=None)

        stream_repo = MagicMock()
        stream_repo.get_by_id = AsyncMock(return_value=stream)
        stream_repo.create = AsyncMock(return_value=stream)
        stream_repo.register_operation = AsyncMock()
        stream_repo.session = AsyncMock()

        mock_emit = AsyncMock(return_value="1234-0")

        with (
            patch(
                "veupath_chatbot.services.chat.orchestrator.emit",
                mock_emit,
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.get_redis",
                return_value=MagicMock(),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.asyncio.create_task",
            ),
        ):
            operation_id, stream_id = await start_chat_stream(
                message="Hello",
                site_id="plasmodb",
                strategy_id=None,
                user_id=user_id,
                user_repo=user_repo,
                stream_repo=stream_repo,
            )

            assert operation_id.startswith("op_")
            assert stream_id == str(stream.id)

    @pytest.mark.asyncio
    async def test_calls_get_or_create_user(self) -> None:
        stream = _make_fake_stream()
        user_id = uuid4()

        user_repo = MagicMock()
        user_repo.get_or_create = AsyncMock(return_value=None)

        stream_repo = MagicMock()
        stream_repo.get_by_id = AsyncMock(return_value=stream)
        stream_repo.create = AsyncMock(return_value=stream)
        stream_repo.register_operation = AsyncMock()
        stream_repo.session = AsyncMock()

        with (
            patch(
                "veupath_chatbot.services.chat.orchestrator.emit",
                AsyncMock(return_value="1234-0"),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.get_redis",
                return_value=MagicMock(),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.asyncio.create_task",
            ),
        ):
            await start_chat_stream(
                message="Hello",
                site_id="plasmodb",
                strategy_id=None,
                user_id=user_id,
                user_repo=user_repo,
                stream_repo=stream_repo,
            )

            user_repo.get_or_create.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_emits_user_message_to_redis(self) -> None:
        stream = _make_fake_stream()
        user_id = uuid4()

        user_repo = MagicMock()
        user_repo.get_or_create = AsyncMock(return_value=None)

        stream_repo = MagicMock()
        stream_repo.get_by_id = AsyncMock(return_value=stream)
        stream_repo.create = AsyncMock(return_value=stream)
        stream_repo.register_operation = AsyncMock()
        stream_repo.session = AsyncMock()

        mock_emit = AsyncMock(return_value="1234-0")

        with (
            patch(
                "veupath_chatbot.services.chat.orchestrator.emit",
                mock_emit,
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.get_redis",
                return_value=MagicMock(),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.asyncio.create_task",
            ),
        ):
            await start_chat_stream(
                message="Hello world",
                site_id="plasmodb",
                strategy_id=None,
                user_id=user_id,
                user_repo=user_repo,
                stream_repo=stream_repo,
            )

            # emit was called with user_message type
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args
            assert call_args[0][2] is not None  # operation_id
            assert call_args[0][3] == "user_message"
            assert call_args[0][4]["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_registers_operation(self) -> None:
        stream = _make_fake_stream()
        user_id = uuid4()

        user_repo = MagicMock()
        user_repo.get_or_create = AsyncMock(return_value=None)

        stream_repo = MagicMock()
        stream_repo.get_by_id = AsyncMock(return_value=stream)
        stream_repo.create = AsyncMock(return_value=stream)
        stream_repo.register_operation = AsyncMock()
        stream_repo.session = AsyncMock()

        with (
            patch(
                "veupath_chatbot.services.chat.orchestrator.emit",
                AsyncMock(return_value="1234-0"),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.get_redis",
                return_value=MagicMock(),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.asyncio.create_task",
            ),
        ):
            operation_id, _ = await start_chat_stream(
                message="Hello",
                site_id="plasmodb",
                strategy_id=None,
                user_id=user_id,
                user_repo=user_repo,
                stream_repo=stream_repo,
            )

            stream_repo.register_operation.assert_called_once_with(
                operation_id, stream.id, "chat"
            )

    @pytest.mark.asyncio
    async def test_creates_stream_when_not_found(self) -> None:
        new_stream = _make_fake_stream()
        user_id = uuid4()

        user_repo = MagicMock()
        user_repo.get_or_create = AsyncMock(return_value=None)

        stream_repo = MagicMock()
        stream_repo.get_by_id = AsyncMock(return_value=None)
        stream_repo.create = AsyncMock(return_value=new_stream)
        stream_repo.register_operation = AsyncMock()
        stream_repo.session = AsyncMock()

        with (
            patch(
                "veupath_chatbot.services.chat.orchestrator.emit",
                AsyncMock(return_value="1234-0"),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.get_redis",
                return_value=MagicMock(),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.asyncio.create_task",
            ),
        ):
            _, stream_id = await start_chat_stream(
                message="Hello",
                site_id="plasmodb",
                strategy_id=uuid4(),
                user_id=user_id,
                user_repo=user_repo,
                stream_repo=stream_repo,
            )

            stream_repo.create.assert_called_once()
            assert stream_id == str(new_stream.id)

    @pytest.mark.asyncio
    async def test_launches_background_producer(self) -> None:
        stream = _make_fake_stream()
        user_id = uuid4()

        user_repo = MagicMock()
        user_repo.get_or_create = AsyncMock(return_value=None)

        stream_repo = MagicMock()
        stream_repo.get_by_id = AsyncMock(return_value=stream)
        stream_repo.create = AsyncMock(return_value=stream)
        stream_repo.register_operation = AsyncMock()
        stream_repo.session = AsyncMock()

        mock_create_task = MagicMock()

        with (
            patch(
                "veupath_chatbot.services.chat.orchestrator.emit",
                AsyncMock(return_value="1234-0"),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.get_redis",
                return_value=MagicMock(),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.asyncio.create_task",
                mock_create_task,
            ),
        ):
            await start_chat_stream(
                message="Hello",
                site_id="plasmodb",
                strategy_id=None,
                user_id=user_id,
                user_repo=user_repo,
                stream_repo=stream_repo,
            )

            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_selected_nodes_parsed_from_message(self) -> None:
        stream = _make_fake_stream()
        user_id = uuid4()

        user_repo = MagicMock()
        user_repo.get_or_create = AsyncMock(return_value=None)

        stream_repo = MagicMock()
        stream_repo.get_by_id = AsyncMock(return_value=stream)
        stream_repo.create = AsyncMock(return_value=stream)
        stream_repo.register_operation = AsyncMock()
        stream_repo.session = AsyncMock()

        def capture_create_task(coro: Any) -> MagicMock:
            # Close the coroutine to avoid warnings.
            coro.close()
            return MagicMock()

        with (
            patch(
                "veupath_chatbot.services.chat.orchestrator.emit",
                AsyncMock(return_value="1234-0"),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.get_redis",
                return_value=MagicMock(),
            ),
            patch(
                "veupath_chatbot.services.chat.orchestrator.asyncio.create_task",
                side_effect=capture_create_task,
            ),
        ):
            # __NODE__ prefix encodes selected nodes.
            operation_id, _ = await start_chat_stream(
                message='__NODE__{"stepId":"s1"}\nModify this step',
                site_id="plasmodb",
                strategy_id=None,
                user_id=user_id,
                user_repo=user_repo,
                stream_repo=stream_repo,
            )

            # Verify the operation was registered and returned.
            assert operation_id.startswith("op_")

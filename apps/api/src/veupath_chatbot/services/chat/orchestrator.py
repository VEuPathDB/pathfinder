"""Chat orchestration entrypoint (service layer) — CQRS version.

Every event is persisted to Redis the moment it's emitted. The PostgreSQL
projection is updated inline. No accumulation, no finalization step.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

from kani import ChatMessage, ChatRole

from veupath_chatbot.ai.agents.factory import create_agent, resolve_effective_model_id
from veupath_chatbot.ai.models.catalog import ModelProvider, ReasoningEffort
from veupath_chatbot.persistence.models import Stream
from veupath_chatbot.persistence.repositories import StreamRepository, UserRepository
from veupath_chatbot.persistence.session import async_session_factory
from veupath_chatbot.platform.events import emit, read_stream_messages
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.redis import get_redis
from veupath_chatbot.platform.types import JSONObject
from veupath_chatbot.services.chat.streaming import stream_chat
from veupath_chatbot.services.chat.utils import parse_selected_nodes

logger = get_logger(__name__)

# Registry of running chat tasks keyed by operation_id.
# Used to cancel operations from the HTTP layer.
_active_tasks: dict[str, asyncio.Task[None]] = {}


def _use_mock_chat_provider() -> bool:
    from veupath_chatbot.platform.config import get_settings

    return get_settings().chat_provider.strip().lower() == "mock"


async def _mock_stream_chat(
    *, message: str, strategy_id: str | None = None
) -> AsyncIterator[JSONObject]:
    """Deterministic, offline-friendly stream for tests/E2E runs.

    Matches the semantic event contract produced by `stream_chat()`.
    """
    deltas = [
        "[mock] ",
        "I received your message: ",
        message,
    ]
    message_id = str(uuid4())
    for d in deltas:
        if "slow" in message.lower():
            await asyncio.sleep(0.2)
        yield {"type": "assistant_delta", "data": {"messageId": message_id, "delta": d}}

    msg_lower = message.lower()
    if "artifact graph" in msg_lower:
        now = datetime.now(UTC).isoformat()
        yield {
            "type": "planning_artifact",
            "data": {
                "planningArtifact": {
                    "id": "mock_exec_graph_artifact",
                    "title": "Mock graph artifact",
                    "summaryMarkdown": "A deterministic multi-step artifact for E2E graph interaction tests.",
                    "assumptions": [],
                    "parameters": {},
                    "proposedStrategyPlan": {
                        "recordType": "gene",
                        "root": {
                            "id": "mock_transform_1",
                            "searchName": "mock_transform",
                            "displayName": "Mock transform step",
                            "parameters": {},
                            "primaryInput": {
                                "id": "mock_search_1",
                                "searchName": "mock_search",
                                "displayName": "Mock search step",
                                "parameters": {},
                            },
                        },
                        "metadata": {"name": "Mock graph plan"},
                    },
                    "createdAt": now,
                }
            },
        }
    elif "delegation draft" in msg_lower:
        now = datetime.now(UTC).isoformat()
        yield {
            "type": "planning_artifact",
            "data": {
                "planningArtifact": {
                    "id": "delegation_draft",
                    "title": "Delegation draft",
                    "summaryMarkdown": "Build a gene strategy using an ortholog transform and a combine.",
                    "assumptions": [],
                    "parameters": {
                        "delegationGoal": "Build a gene strategy using an ortholog transform and a combine.",
                        "delegationPlan": {
                            "tasks": [
                                {
                                    "id": "task_search",
                                    "type": "search",
                                    "searchName": "GenesByTaxon",
                                    "context": "Find genes in P. falciparum",
                                },
                                {
                                    "id": "task_transform",
                                    "type": "transform",
                                    "searchName": "GenesByOrthologPattern",
                                    "context": "Ortholog transform",
                                    "dependsOn": ["task_search"],
                                },
                                {
                                    "id": "task_combine",
                                    "type": "combine",
                                    "operator": "UNION",
                                    "context": "Combine search and transform",
                                    "dependsOn": ["task_search", "task_transform"],
                                },
                            ]
                        },
                    },
                    "createdAt": now,
                }
            },
        }
    elif "delegate_strategy_subtasks" in msg_lower or "delegation" in msg_lower:
        yield {
            "type": "subkani_task_start",
            "data": {"task": "delegate:build-strategy"},
        }
        yield {
            "type": "subkani_tool_call_start",
            "data": {
                "task": "delegate:build-strategy",
                "id": "tc_delegate_1",
                "name": "search_for_searches",
                "arguments": '{"query":"ortholog transform","record_type":"gene","limit":3}',
            },
        }
        yield {
            "type": "subkani_tool_call_end",
            "data": {
                "task": "delegate:build-strategy",
                "id": "tc_delegate_1",
                "result": '{"rag":{"data":[],"note":""},"wdk":{"data":[],"note":"mock"}}',
            },
        }
        yield {
            "type": "subkani_task_end",
            "data": {"task": "delegate:build-strategy", "status": "done"},
        }

        gid = strategy_id or "mock_graph_delegation"
        yield {
            "type": "strategy_update",
            "data": {
                "graphId": gid,
                "step": {
                    "graphId": gid,
                    "stepId": "mock_search_1",
                    "kind": "search",
                    "displayName": "Delegated search step",
                    "searchName": "mock_search",
                    "parameters": {"q": "gametocyte", "min": 10},
                    "recordType": "gene",
                    "graphName": "Delegation-built strategy",
                    "description": "A deterministic delegated strategy for E2E.",
                },
            },
        }
        yield {
            "type": "strategy_update",
            "data": {
                "graphId": gid,
                "step": {
                    "graphId": gid,
                    "stepId": "mock_transform_1",
                    "kind": "transform",
                    "displayName": "Delegated transform step",
                    "searchName": "mock_transform",
                    "primaryInputStepId": "mock_search_1",
                    "parameters": {"insertBetween": True, "species": "P. falciparum"},
                    "recordType": "gene",
                },
            },
        }
        yield {
            "type": "strategy_update",
            "data": {
                "graphId": gid,
                "step": {
                    "graphId": gid,
                    "stepId": "mock_combine_1",
                    "kind": "combine",
                    "displayName": "Delegated combine step",
                    "operator": "UNION",
                    "primaryInputStepId": "mock_transform_1",
                    "secondaryInputStepId": "mock_search_1",
                    "parameters": {},
                    "recordType": "gene",
                },
            },
        }

        yield {
            "type": "assistant_message",
            "data": {
                "messageId": message_id,
                "content": "[mock] Delegation complete. Built a multi-step strategy and emitted sub-kani activity.",
            },
        }
        yield {"type": "message_end", "data": {}}
        return

    yield {
        "type": "assistant_message",
        "data": {"messageId": message_id, "content": "".join(deltas)},
    }

    yield {"type": "message_end", "data": {}}


async def _ensure_stream(
    stream_repo: StreamRepository,
    *,
    user_id: UUID,
    site_id: str,
    stream_id: UUID | None,
) -> Stream:
    """Ensure a stream exists, creating one if needed."""
    if stream_id:
        stream = await stream_repo.get_by_id(stream_id)
        if stream:
            return stream
        logger.warning("Stream not found; creating new", stream_id=stream_id)
        return await stream_repo.create(
            user_id=user_id, site_id=site_id, stream_id=stream_id
        )
    return await stream_repo.create(user_id=user_id, site_id=site_id)


async def _build_chat_history_from_redis(stream_id: str) -> list[ChatMessage]:
    """Build kani-compatible chat history from Redis stream events."""
    redis = get_redis()
    messages = await read_stream_messages(redis, stream_id)
    history: list[ChatMessage] = []
    for msg in messages:
        role = msg.get("role")
        content = str(msg.get("content", ""))
        if not content:
            continue
        if role == "user":
            _, cleaned = parse_selected_nodes(content)
            history.append(ChatMessage(role=ChatRole.USER, content=cleaned))
        elif role == "assistant":
            history.append(ChatMessage(role=ChatRole.ASSISTANT, content=content))
    return history


async def start_chat_stream(
    *,
    message: str,
    site_id: str,
    strategy_id: UUID | None,
    user_id: UUID,
    user_repo: UserRepository,
    stream_repo: StreamRepository,
    # Per-request model overrides
    provider_override: ModelProvider | None = None,
    model_override: str | None = None,
    reasoning_effort: ReasoningEffort | None = None,
    mentions: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    """Start a background chat operation and return its identifiers.

    Returns ``(operation_id, stream_id)`` so the caller can hand them
    to the client. The client subscribes to
    ``GET /operations/{operation_id}/subscribe`` for SSE events.

    Only fast, essential work runs synchronously (user lookup, stream
    resolution, operation registration, user_message emission).
    All heavy lifting is deferred into the background producer.
    """
    await user_repo.get_or_create(user_id)

    stream = await _ensure_stream(
        stream_repo,
        user_id=user_id,
        site_id=site_id,
        stream_id=strategy_id,
    )

    stream_id_str = str(stream.id)
    operation_id = f"op_{uuid4().hex[:12]}"

    # Persist user message to Redis NOW (survives even if producer errors).
    redis = get_redis()
    await emit(
        redis,
        stream_id_str,
        operation_id,
        "user_message",
        {"content": message, "messageId": str(uuid4())},
        session=stream_repo.session,
    )

    # Register the operation in PostgreSQL for client discovery.
    await stream_repo.register_operation(operation_id, stream.id, "chat")

    # Commit before launching the background producer — it creates its own
    # session and must be able to read the Stream/StreamProjection/Operation.
    await stream_repo.session.commit()

    selected_nodes, model_message = parse_selected_nodes(message)

    # Launch the background producer as an asyncio task.
    task = asyncio.create_task(
        _chat_producer(
            stream_id_str=stream_id_str,
            operation_id=operation_id,
            site_id=site_id,
            user_id=user_id,
            model_message=model_message,
            selected_nodes=selected_nodes,
            provider_override=provider_override,
            model_override=model_override,
            reasoning_effort=reasoning_effort,
            mentions=mentions,
        )
    )
    _active_tasks[operation_id] = task
    task.add_done_callback(lambda _: _active_tasks.pop(operation_id, None))

    return operation_id, stream_id_str


async def _chat_producer(
    *,
    stream_id_str: str,
    operation_id: str,
    site_id: str,
    user_id: UUID,
    model_message: str,
    selected_nodes: JSONObject | None,
    provider_override: ModelProvider | None,
    model_override: str | None,
    reasoning_effort: ReasoningEffort | None,
    mentions: list[dict[str, str]] | None,
) -> None:
    """Background task: run the LLM agent and emit every event to Redis."""
    redis = get_redis()

    async with async_session_factory() as session:
        bg_stream_repo = StreamRepository(session)
        projection = await bg_stream_repo.get_projection(UUID(stream_id_str))

        if not projection:
            await emit(
                redis,
                stream_id_str,
                operation_id,
                "error",
                {"error": "Stream not found"},
            )
            await bg_stream_repo.fail_operation(operation_id)
            await session.commit()
            return

        # Build rich context from @-mentions.
        mentioned_context: str | None = None
        if mentions:
            from veupath_chatbot.services.chat.mention_context import (
                build_mention_context,
            )

            mentioned_context = (
                await build_mention_context(mentions, bg_stream_repo) or None
            )

        # Build chat history from Redis (not from DB).
        history = await _build_chat_history_from_redis(stream_id_str)

        # Build strategy graph payload from projection.
        strategy_graph_payload: JSONObject = {
            "id": stream_id_str,
            "name": projection.name,
            "plan": projection.plan,
            "steps": projection.steps,
            "rootStepId": projection.root_step_id,
            "recordType": projection.record_type,
        }

        # Resolve the effective model.
        effective_model = resolve_effective_model_id(
            model_override=model_override,
            persisted_model_id=projection.model_id,
        )

        agent = create_agent(
            site_id=site_id,
            user_id=user_id,
            chat_history=history,
            strategy_graph=strategy_graph_payload,
            selected_nodes=selected_nodes,
            provider_override=provider_override,
            model_override=effective_model,
            reasoning_effort=reasoning_effort,
            mentioned_context=mentioned_context,
        )

        # Persist model selection if changed.
        if effective_model != projection.model_id:
            await emit(
                redis,
                stream_id_str,
                operation_id,
                "model_selected",
                {"modelId": effective_model},
                session=session,
            )

        try:
            # Emit message_start with strategy context for the frontend.
            strategy_payload: JSONObject = {
                "id": stream_id_str,
                "name": projection.name,
                "siteId": site_id,
                "recordType": projection.record_type,
                "wdkStrategyId": projection.wdk_strategy_id,
            }
            await emit(
                redis,
                stream_id_str,
                operation_id,
                "message_start",
                {"strategyId": stream_id_str, "strategy": strategy_payload},
                session=session,
            )

            stream_iter = (
                _mock_stream_chat(
                    message=model_message,
                    strategy_id=stream_id_str,
                )
                if _use_mock_chat_provider()
                else stream_chat(agent, model_message)
            )
            async for event_value in stream_iter:
                if not isinstance(event_value, dict):
                    continue
                event_type_raw = event_value.get("type", "")
                event_type = event_type_raw if isinstance(event_type_raw, str) else ""
                event_data_raw = event_value.get("data")
                event_data = event_data_raw if isinstance(event_data_raw, dict) else {}

                # Every event is persisted to Redis + projected to PostgreSQL.
                await emit(
                    redis,
                    stream_id_str,
                    operation_id,
                    event_type,
                    event_data,
                    session=session,
                )

            # Mark operation complete.
            await bg_stream_repo.complete_operation(operation_id)

        except asyncio.CancelledError:
            logger.info("Chat producer cancelled", operation_id=operation_id)
            await emit(
                redis,
                stream_id_str,
                operation_id,
                "message_end",
                {},
                session=session,
            )
            await bg_stream_repo.cancel_operation(operation_id)
            await session.commit()
            return

        except Exception as e:
            logger.error("Chat producer error", error=str(e), exc_info=True)
            await emit(
                redis,
                stream_id_str,
                operation_id,
                "error",
                {"error": str(e)},
                session=session,
            )
            await emit(
                redis,
                stream_id_str,
                operation_id,
                "message_end",
                {},
                session=session,
            )
            await bg_stream_repo.fail_operation(operation_id)

        await session.commit()


async def cancel_chat_operation(operation_id: str) -> bool:
    """Cancel a running chat operation.

    Returns True if the operation was found and cancelled, False otherwise.
    """
    task = _active_tasks.get(operation_id)
    if task is None:
        return False
    task.cancel()
    return True

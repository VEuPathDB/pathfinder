"""Unit tests for platform.context — request-scoped context variables.

Focuses on:
- Default values for context variables
- Setting and retrieving context vars
- Context variable isolation across async tasks
"""

import asyncio
from uuid import uuid4

from veupath_chatbot.platform.context import (
    request_id_ctx,
    site_id_ctx,
    user_id_ctx,
    veupathdb_auth_token_ctx,
)


class TestContextVarDefaults:
    def test_request_id_defaults_to_none(self):
        # In a fresh context, should be None
        token = request_id_ctx.set(None)
        try:
            assert request_id_ctx.get() is None
        finally:
            request_id_ctx.reset(token)

    def test_user_id_defaults_to_none(self):
        token = user_id_ctx.set(None)
        try:
            assert user_id_ctx.get() is None
        finally:
            user_id_ctx.reset(token)

    def test_site_id_defaults_to_none(self):
        token = site_id_ctx.set(None)
        try:
            assert site_id_ctx.get() is None
        finally:
            site_id_ctx.reset(token)

    def test_veupathdb_auth_token_defaults_to_none(self):
        token = veupathdb_auth_token_ctx.set(None)
        try:
            assert veupathdb_auth_token_ctx.get() is None
        finally:
            veupathdb_auth_token_ctx.reset(token)


class TestContextVarSetGet:
    def test_set_and_get_request_id(self):
        token = request_id_ctx.set("req-123")
        try:
            assert request_id_ctx.get() == "req-123"
        finally:
            request_id_ctx.reset(token)

    def test_set_and_get_user_id(self):
        uid = uuid4()
        token = user_id_ctx.set(uid)
        try:
            assert user_id_ctx.get() == uid
        finally:
            user_id_ctx.reset(token)

    def test_set_and_get_site_id(self):
        token = site_id_ctx.set("plasmodb")
        try:
            assert site_id_ctx.get() == "plasmodb"
        finally:
            site_id_ctx.reset(token)

    def test_set_and_get_auth_token(self):
        token = veupathdb_auth_token_ctx.set("secret-token")
        try:
            assert veupathdb_auth_token_ctx.get() == "secret-token"
        finally:
            veupathdb_auth_token_ctx.reset(token)


class TestContextVarIsolation:
    async def test_context_vars_isolated_between_tasks(self):
        """Context vars set in one task should not leak to another."""
        results: dict[str, str | None] = {}

        async def task_a() -> None:
            request_id_ctx.set("task-a")
            await asyncio.sleep(0.01)
            results["a"] = request_id_ctx.get()

        async def task_b() -> None:
            # task_b does NOT set request_id_ctx
            await asyncio.sleep(0.01)
            results["b"] = request_id_ctx.get()

        # Run tasks concurrently — task_b should not see task_a's value
        # because asyncio.create_task copies the context
        await asyncio.gather(
            asyncio.create_task(task_a()),
            asyncio.create_task(task_b()),
        )

        assert results["a"] == "task-a"
        # task_b should have its own copy of the context (default or parent value)
        # It should NOT see "task-a"
        assert results["b"] != "task-a"

    async def test_reset_restores_previous_value(self):
        """Resetting a context var should restore its previous value."""
        original_token = request_id_ctx.set("original")
        try:
            inner_token = request_id_ctx.set("overridden")
            assert request_id_ctx.get() == "overridden"
            request_id_ctx.reset(inner_token)
            assert request_id_ctx.get() == "original"
        finally:
            request_id_ctx.reset(original_token)

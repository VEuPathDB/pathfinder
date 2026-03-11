"""Integration tests for workbench chat endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_workbench_chat_returns_202_with_operation_id(
    authed_client: httpx.AsyncClient,
) -> None:
    resp = await authed_client.post(
        "/api/v1/experiments/test-exp/chat",
        json={"message": "Interpret these results", "siteId": "plasmodb"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "operationId" in data
    assert "streamId" in data


@pytest.mark.asyncio
async def test_workbench_chat_messages_returns_empty_for_new(
    authed_client: httpx.AsyncClient,
) -> None:
    resp = await authed_client.get("/api/v1/experiments/nonexistent/chat/messages")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_workbench_chat_requires_message(
    authed_client: httpx.AsyncClient,
) -> None:
    resp = await authed_client.post(
        "/api/v1/experiments/test-exp/chat",
        json={"siteId": "plasmodb"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_workbench_chat_requires_site_id(
    authed_client: httpx.AsyncClient,
) -> None:
    resp = await authed_client.post(
        "/api/v1/experiments/test-exp/chat",
        json={"message": "Hello"},
    )
    assert resp.status_code == 422

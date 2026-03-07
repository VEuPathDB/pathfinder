"""Integration tests for step CRUD, analyses, and reports endpoints."""

from uuid import uuid4

import httpx
import pytest

from veupath_chatbot.platform.types import JSONObject

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_plan() -> JSONObject:
    return {
        "recordType": "gene",
        "root": {
            "searchName": "GenesByTextSearch",
            "parameters": {"text": "kinase"},
        },
        "metadata": {"name": "Step Test Strategy"},
    }


async def _create_strategy(
    authed_client: httpx.AsyncClient,
) -> tuple[str, str]:
    """Create a strategy and return (strategy_id, root_step_id)."""
    resp = await authed_client.post(
        "/api/v1/strategies",
        json={
            "name": "Step Test Strategy",
            "siteId": "plasmodb",
            "plan": _minimal_plan(),
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    strategy_id = body["id"]
    root_step_id = body["rootStepId"]
    assert root_step_id is not None
    return strategy_id, root_step_id


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_step_requires_auth(client: httpx.AsyncClient) -> None:
    """Unauthenticated step access returns 401."""
    fake_id = str(uuid4())
    resp = await client.get(f"/api/v1/strategies/{fake_id}/steps/step-1")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_step(authed_client: httpx.AsyncClient) -> None:
    """Getting a step from a strategy returns step data."""
    strategy_id, root_step_id = await _create_strategy(authed_client)

    resp = await authed_client.get(
        f"/api/v1/strategies/{strategy_id}/steps/{root_step_id}"
    )
    assert resp.status_code == 200
    step = resp.json()
    assert step["id"] == root_step_id
    assert step["searchName"] == "GenesByTextSearch"
    assert "parameters" in step


@pytest.mark.asyncio
async def test_get_step_not_found(authed_client: httpx.AsyncClient) -> None:
    """Non-existent step returns 404."""
    strategy_id, _ = await _create_strategy(authed_client)

    resp = await authed_client.get(
        f"/api/v1/strategies/{strategy_id}/steps/nonexistent-step"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_step_wrong_strategy(authed_client: httpx.AsyncClient) -> None:
    """Step from wrong strategy returns 404."""
    _strategy_id, root_step_id = await _create_strategy(authed_client)
    fake_strategy_id = str(uuid4())

    resp = await authed_client.get(
        f"/api/v1/strategies/{fake_strategy_id}/steps/{root_step_id}"
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_step_filters_empty(authed_client: httpx.AsyncClient) -> None:
    """New step has no filters."""
    strategy_id, root_step_id = await _create_strategy(authed_client)

    resp = await authed_client.get(
        f"/api/v1/strategies/{strategy_id}/steps/{root_step_id}/filters"
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_set_and_list_step_filter(authed_client: httpx.AsyncClient) -> None:
    """Setting a filter on a step persists it."""
    strategy_id, root_step_id = await _create_strategy(authed_client)

    # Set a filter
    resp = await authed_client.put(
        f"/api/v1/strategies/{strategy_id}/steps/{root_step_id}/filters/organism",
        json={"value": "Plasmodium falciparum 3D7", "disabled": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "filters" in body
    assert len(body["filters"]) == 1
    assert body["filters"][0]["name"] == "organism"

    # List filters
    resp = await authed_client.get(
        f"/api/v1/strategies/{strategy_id}/steps/{root_step_id}/filters"
    )
    assert resp.status_code == 200
    filters = resp.json()
    assert len(filters) == 1
    assert filters[0]["name"] == "organism"


@pytest.mark.asyncio
async def test_delete_step_filter(authed_client: httpx.AsyncClient) -> None:
    """Deleting a filter removes it."""
    strategy_id, root_step_id = await _create_strategy(authed_client)

    # Set then delete a filter
    await authed_client.put(
        f"/api/v1/strategies/{strategy_id}/steps/{root_step_id}/filters/organism",
        json={"value": "Plasmodium falciparum 3D7", "disabled": False},
    )
    resp = await authed_client.delete(
        f"/api/v1/strategies/{strategy_id}/steps/{root_step_id}/filters/organism"
    )
    assert resp.status_code == 200
    assert resp.json()["filters"] == []


# ---------------------------------------------------------------------------
# Analyses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_step_analysis(authed_client: httpx.AsyncClient) -> None:
    """Running an analysis attaches it to the step."""
    strategy_id, root_step_id = await _create_strategy(authed_client)

    resp = await authed_client.post(
        f"/api/v1/strategies/{strategy_id}/steps/{root_step_id}/analyses",
        json={
            "analysisType": "word-enrichment",
            "parameters": {"threshold": "0.05"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "analysis" in body
    assert body["analysis"]["analysisType"] == "word-enrichment"


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_step_report(authed_client: httpx.AsyncClient) -> None:
    """Running a report attaches it to the step."""
    strategy_id, root_step_id = await _create_strategy(authed_client)

    resp = await authed_client.post(
        f"/api/v1/strategies/{strategy_id}/steps/{root_step_id}/reports",
        json={
            "reportName": "tabular",
            "config": {"attributes": ["primary_key"]},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "report" in body
    assert body["report"]["reportName"] == "tabular"

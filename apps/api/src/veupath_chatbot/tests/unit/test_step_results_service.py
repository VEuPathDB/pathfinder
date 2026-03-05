"""Tests for StepResultsService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from veupath_chatbot.services.wdk.step_results import StepResultsService


@pytest.fixture
def mock_api() -> MagicMock:
    api = MagicMock()
    api.get_record_type_info = AsyncMock(
        return_value={
            "attributes": {
                "gene_name": {
                    "displayName": "Gene Name",
                    "type": "string",
                    "isDisplayable": True,
                },
                "score": {
                    "displayName": "Score",
                    "type": "number",
                    "isDisplayable": True,
                },
            }
        }
    )
    api.get_step_records = AsyncMock(
        return_value={
            "records": [
                {
                    "id": [{"name": "source_id", "value": "GENE1"}],
                    "attributes": {"gene_name": "foo"},
                },
            ],
            "meta": {"totalCount": 1},
        }
    )
    api.get_column_distribution = AsyncMock(return_value={"bins": []})
    api.list_analysis_types = AsyncMock(return_value=[{"name": "go-enrichment"}])
    api.get_strategy = AsyncMock(return_value={"stepTree": {}})
    api.get_single_record = AsyncMock(return_value={"id": "GENE1"})
    return api


class TestGetAttributes:
    @pytest.mark.asyncio
    async def test_returns_normalized_attributes(self, mock_api: MagicMock) -> None:
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        result = await svc.get_attributes()
        assert result["recordType"] == "gene"
        attrs = result["attributes"]
        assert len(attrs) == 2
        assert any(a["name"] == "score" and a["isSortable"] for a in attrs)

    @pytest.mark.asyncio
    async def test_calls_get_record_type_info(self, mock_api: MagicMock) -> None:
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        await svc.get_attributes()
        mock_api.get_record_type_info.assert_called_once_with("gene")

    @pytest.mark.asyncio
    async def test_handles_attributes_map_key(self, mock_api: MagicMock) -> None:
        mock_api.get_record_type_info = AsyncMock(
            return_value={
                "attributesMap": {
                    "gene_name": {
                        "displayName": "Gene Name",
                        "type": "string",
                    }
                }
            }
        )
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        result = await svc.get_attributes()
        assert len(result["attributes"]) == 1


class TestGetRecords:
    @pytest.mark.asyncio
    async def test_returns_paginated_records(self, mock_api: MagicMock) -> None:
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        result = await svc.get_records(offset=0, limit=50)
        mock_api.get_step_records.assert_called_once()
        assert "records" in result
        assert "meta" in result

    @pytest.mark.asyncio
    async def test_passes_sorting(self, mock_api: MagicMock) -> None:
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        await svc.get_records(sort="score", direction="DESC")
        call_kwargs = mock_api.get_step_records.call_args[1]
        assert call_kwargs["sorting"] == [
            {"attributeName": "score", "direction": "DESC"}
        ]

    @pytest.mark.asyncio
    async def test_passes_attributes(self, mock_api: MagicMock) -> None:
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        await svc.get_records(attributes=["gene_name", "score"])
        call_kwargs = mock_api.get_step_records.call_args[1]
        assert call_kwargs["attributes"] == ["gene_name", "score"]

    @pytest.mark.asyncio
    async def test_no_sorting_when_sort_is_none(self, mock_api: MagicMock) -> None:
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        await svc.get_records()
        call_kwargs = mock_api.get_step_records.call_args[1]
        assert call_kwargs["sorting"] is None


class TestGetDistribution:
    @pytest.mark.asyncio
    async def test_returns_distribution(self, mock_api: MagicMock) -> None:
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        result = await svc.get_distribution("score")
        mock_api.get_column_distribution.assert_called_once_with(42, "score")
        assert result == {"bins": []}


class TestListAnalysisTypes:
    @pytest.mark.asyncio
    async def test_returns_types(self, mock_api: MagicMock) -> None:
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        result = await svc.list_analysis_types()
        mock_api.list_analysis_types.assert_called_once_with(42)
        assert result == {"analysisTypes": [{"name": "go-enrichment"}]}


class TestGetStrategy:
    @pytest.mark.asyncio
    async def test_returns_strategy(self, mock_api: MagicMock) -> None:
        svc = StepResultsService(mock_api, step_id=42, record_type="gene")
        result = await svc.get_strategy(100)
        mock_api.get_strategy.assert_called_once_with(100)
        assert result == {"stepTree": {}}

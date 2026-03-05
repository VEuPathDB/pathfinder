"""Unit tests for WDK step counts caching."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from veupath_chatbot.domain.strategy.ast import PlanStepNode, StrategyAST


def _simple_ast() -> StrategyAST:
    return StrategyAST(
        record_type="gene",
        root=PlanStepNode(
            search_name="GenesByTextSearch",
            parameters={"text_expression": "kinase"},
            id="step1",
        ),
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the module-level cache before each test."""
    from veupath_chatbot.services.strategies import wdk_bridge

    wdk_bridge._STEP_COUNTS_CACHE.clear()
    yield
    wdk_bridge._STEP_COUNTS_CACHE.clear()


@pytest.mark.asyncio
async def test_all_none_results_are_cached():
    """All-None results must be cached to avoid repeated expensive API calls.

    When the WDK API fails to return counts, compute_step_counts_for_plan
    returns {step_id: None} for every step.  Previously this was never
    cached, causing repeated create-fetch-delete cycles on every call.
    """
    from veupath_chatbot.services.strategies.wdk_bridge import (
        _STEP_COUNTS_CACHE,
        compute_step_counts_for_plan,
    )

    plan = _simple_ast().to_dict()
    ast = _simple_ast()

    mock_api = AsyncMock()
    # Simulate: strategy created but get_strategy returns no estimatedSize
    mock_api.create_strategy.return_value = {"id": 999}
    mock_api.get_strategy.return_value = {"steps": {}}
    mock_api.delete_strategy.return_value = None

    with (
        patch(
            "veupath_chatbot.services.strategies.wdk_bridge.get_strategy_api",
            return_value=mock_api,
        ),
        patch(
            "veupath_chatbot.services.strategies.wdk_bridge.compile_strategy",
            new_callable=AsyncMock,
        ) as mock_compile,
    ):
        from veupath_chatbot.domain.strategy.compile import (
            CompilationResult,
            CompiledStep,
        )
        from veupath_chatbot.integrations.veupathdb.strategy_api.helpers import (
            StepTreeNode,
        )

        mock_compile.return_value = CompilationResult(
            steps=[
                CompiledStep(
                    local_id="step1",
                    wdk_step_id=1,
                    step_type="search",
                    display_name="GenesByTextSearch",
                )
            ],
            step_tree=StepTreeNode(step_id=1),
            root_step_id=1,
        )

        # First call — should hit the API
        result1 = await compute_step_counts_for_plan(plan, ast, "plasmodb")
        assert result1 == {"step1": None}
        assert mock_api.create_strategy.call_count == 1

        # Second call — should hit cache, NOT the API again
        result2 = await compute_step_counts_for_plan(plan, ast, "plasmodb")
        assert result2 == {"step1": None}
        assert mock_api.create_strategy.call_count == 1, (
            "Expected cache hit — API should NOT be called again for all-None results"
        )

    assert len(_STEP_COUNTS_CACHE) == 1

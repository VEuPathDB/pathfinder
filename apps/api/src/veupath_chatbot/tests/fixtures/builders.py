"""Shared builder helpers for test data construction.

Consolidates factory functions that were duplicated across 3+ test files.
Import from here instead of redefining in each test module.
"""

from __future__ import annotations

from veupath_chatbot.domain.parameters.specs import ParamSpecNormalized
from veupath_chatbot.domain.strategy.ast import PlanStepNode
from veupath_chatbot.domain.strategy.ops import CombineOp

# ---------------------------------------------------------------------------
# PlanStepNode builders -- used in test_graph_integrity, test_graph_ops,
# test_strategy_session
# ---------------------------------------------------------------------------


def make_leaf(
    step_id: str,
    name: str = "GenesByTextSearch",
    display: str | None = None,
    parameters: dict | None = None,
) -> PlanStepNode:
    """Create a leaf (search) PlanStepNode."""
    return PlanStepNode(
        search_name=name,
        parameters=parameters if parameters is not None else {},
        display_name=display,
        id=step_id,
    )


def make_combine(
    step_id: str,
    left: PlanStepNode,
    right: PlanStepNode,
    operator: CombineOp = CombineOp.INTERSECT,
) -> PlanStepNode:
    """Create a combine (boolean) PlanStepNode."""
    return PlanStepNode(
        search_name="BooleanQuestion",
        parameters={},
        primary_input=left,
        secondary_input=right,
        operator=operator,
        id=step_id,
    )


def make_transform(
    step_id: str,
    input_step: PlanStepNode,
    name: str = "GenesByOrthologs",
    parameters: dict | None = None,
) -> PlanStepNode:
    """Create a transform (unary) PlanStepNode."""
    return PlanStepNode(
        search_name=name,
        parameters=parameters if parameters is not None else {"organism": "Pf3D7"},
        primary_input=input_step,
        id=step_id,
    )


# ---------------------------------------------------------------------------
# ParamSpecNormalized builder -- used in test_normalizer, test_value_helpers,
# test_canonicalize
# ---------------------------------------------------------------------------


def make_param_spec(
    name: str = "test_param",
    param_type: str = "string",
    allow_empty: bool = False,
    min_selected: int | None = None,
    max_selected: int | None = None,
    vocabulary: dict | list | None = None,
    count_only_leaves: bool = False,
) -> ParamSpecNormalized:
    """Create a ParamSpecNormalized for parameter validation tests."""
    return ParamSpecNormalized(
        name=name,
        param_type=param_type,
        allow_empty_value=allow_empty,
        min_selected_count=min_selected,
        max_selected_count=max_selected,
        vocabulary=vocabulary,
        count_only_leaves=count_only_leaves,
    )

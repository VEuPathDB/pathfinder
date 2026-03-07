"""Canonical serialization helpers for persisted strategy state.

Goal: keep a single, shared definition for how we derive the persisted `steps`
list (StepData dicts) from various inputs (AST, graph snapshots, etc.).
"""

from veupath_chatbot.domain.strategy.ast import StrategyAST, from_dict
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONArray, JSONObject

from .step_builders import build_steps_data_from_ast

logger = get_logger(__name__)


def _parse_plan(plan: JSONObject) -> StrategyAST | None:
    """Parse a plan dict into a StrategyAST, returning None on error."""
    try:
        return from_dict(plan)
    except ValueError, KeyError, TypeError:
        logger.debug("Could not parse plan into AST", exc_info=True)
        return None


def build_steps_data_from_plan(plan: JSONObject) -> JSONArray:
    """Build persisted steps list from a plan dict (AST payload).

    :param plan: Plan dict (AST payload).
    :returns: List of step data dicts.
    """
    ast = _parse_plan(plan)
    if ast is None:
        return []
    return build_steps_data_from_ast(ast)


def count_steps_in_plan(plan: JSONObject) -> int:
    """Count steps in a plan without relying on persisted step lists.

    :param plan: Plan dict (AST payload).
    :returns: Step count.
    """
    ast = _parse_plan(plan)
    if ast is None:
        return 0
    return len(ast.get_all_steps())

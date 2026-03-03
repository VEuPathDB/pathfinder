"""Unit tests for StrategyGraph session operations."""

from __future__ import annotations

from veupath_chatbot.domain.strategy.ast import PlanStepNode, StrategyAST
from veupath_chatbot.domain.strategy.ops import CombineOp
from veupath_chatbot.domain.strategy.session import StrategyGraph


def _make_leaf(step_id: str, search_name: str = "GenesByTextSearch") -> PlanStepNode:
    return PlanStepNode(
        search_name=search_name,
        parameters={"text_expression": step_id},
        id=step_id,
    )


def _make_combine(
    step_id: str,
    left: PlanStepNode,
    right: PlanStepNode,
) -> PlanStepNode:
    return PlanStepNode(
        search_name="GenesBooleanQuestion",
        parameters={},
        primary_input=left,
        secondary_input=right,
        operator=CombineOp.INTERSECT,
        id=step_id,
    )


def _build_graph_with_strategy(n_leaves: int = 2) -> StrategyGraph:
    """Build a StrategyGraph with a simple combine strategy."""
    graph = StrategyGraph("g1", "Test", "plasmodb")
    leaves = [_make_leaf(f"step{i + 1}") for i in range(n_leaves)]
    root = _make_combine("step_combine", leaves[0], leaves[1])
    ast = StrategyAST(record_type="gene", root=root)
    graph.current_strategy = ast
    graph.steps = {s.id: s for s in ast.get_all_steps()}
    graph.recompute_roots()
    graph.last_step_id = root.id
    return graph


class TestUndoRestoresFullGraphState:
    """Undo must restore steps, roots, and last_step_id — not just current_strategy."""

    def test_undo_restores_steps(self) -> None:
        graph = _build_graph_with_strategy()
        assert len(graph.steps) == 3
        graph.save_history("initial 3-step strategy")

        # Add a 4th step
        extra = _make_leaf("step_extra")
        graph.add_step(extra)
        assert len(graph.steps) == 4, "Precondition: 4 steps after add"

        # Build new AST including the extra step
        new_root = _make_combine("step_new_root", graph.current_strategy.root, extra)
        graph.current_strategy = StrategyAST(record_type="gene", root=new_root)
        graph.steps = {s.id: s for s in graph.current_strategy.get_all_steps()}
        graph.recompute_roots()
        graph.last_step_id = new_root.id
        graph.save_history("added 4th step")

        assert len(graph.steps) == 5, "Precondition: 5 steps after combine"

        # Undo
        result = graph.undo()
        assert result is True

        # After undo, steps must reflect the 3-step strategy, not the 5-step one
        assert len(graph.steps) == 3, (
            f"Expected 3 steps after undo, got {len(graph.steps)}: "
            f"{list(graph.steps.keys())}"
        )

    def test_undo_restores_roots(self) -> None:
        graph = _build_graph_with_strategy()
        graph.save_history("initial")
        original_roots = set(graph.roots)

        # Modify graph
        extra = _make_leaf("step_extra")
        graph.add_step(extra)
        new_root = _make_combine("step_new_root", graph.current_strategy.root, extra)
        graph.current_strategy = StrategyAST(record_type="gene", root=new_root)
        graph.steps = {s.id: s for s in graph.current_strategy.get_all_steps()}
        graph.recompute_roots()
        graph.last_step_id = new_root.id
        graph.save_history("modified")

        graph.undo()
        assert graph.roots == original_roots, (
            f"Expected roots {original_roots}, got {graph.roots}"
        )

    def test_undo_restores_last_step_id(self) -> None:
        graph = _build_graph_with_strategy()
        original_last = graph.last_step_id
        graph.save_history("initial")

        extra = _make_leaf("step_extra")
        graph.add_step(extra)
        new_root = _make_combine("step_new_root", graph.current_strategy.root, extra)
        graph.current_strategy = StrategyAST(record_type="gene", root=new_root)
        graph.steps = {s.id: s for s in graph.current_strategy.get_all_steps()}
        graph.recompute_roots()
        graph.last_step_id = new_root.id
        graph.save_history("modified")

        assert graph.last_step_id == "step_new_root"
        graph.undo()
        assert graph.last_step_id == original_last, (
            f"Expected last_step_id={original_last}, got {graph.last_step_id}"
        )

    def test_undo_with_insufficient_history_returns_false(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        assert graph.undo() is False

        graph.save_history("only one")
        assert graph.undo() is False

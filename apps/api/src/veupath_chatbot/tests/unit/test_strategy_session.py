"""Unit tests for StrategyGraph session operations."""

from __future__ import annotations

from veupath_chatbot.domain.strategy.ast import PlanStepNode, StrategyAST
from veupath_chatbot.domain.strategy.ops import CombineOp
from veupath_chatbot.domain.strategy.session import (
    StrategyGraph,
    StrategySession,
    hydrate_graph_from_steps_data,
)
from veupath_chatbot.tests.fixtures.builders import make_combine, make_leaf


def _make_leaf(step_id: str, search_name: str = "GenesByTextSearch") -> PlanStepNode:
    return make_leaf(step_id, name=search_name, parameters={"text_expression": step_id})


def _make_combine(
    step_id: str,
    left: PlanStepNode,
    right: PlanStepNode,
) -> PlanStepNode:
    return make_combine(step_id, left, right)


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


class TestAddStep:
    def test_adds_step_to_graph(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        step = _make_leaf("s1")
        graph.add_step(step)
        assert "s1" in graph.steps
        assert graph.steps["s1"] is step

    def test_step_becomes_root(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        graph.add_step(_make_leaf("s1"))
        assert "s1" in graph.roots

    def test_combine_removes_input_roots(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        left = _make_leaf("s1")
        right = _make_leaf("s2")
        graph.add_step(left)
        graph.add_step(right)
        assert graph.roots == {"s1", "s2"}
        combine = _make_combine("c1", left, right)
        graph.add_step(combine)
        assert graph.roots == {"c1"}

    def test_sets_last_step_id(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        graph.add_step(_make_leaf("s1"))
        assert graph.last_step_id == "s1"
        graph.add_step(_make_leaf("s2"))
        assert graph.last_step_id == "s2"


class TestGetStep:
    def test_returns_step(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        step = _make_leaf("s1")
        graph.add_step(step)
        assert graph.get_step("s1") is step

    def test_returns_none_for_missing(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        assert graph.get_step("nope") is None


class TestRecomputeRoots:
    def test_finds_single_root(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        left = _make_leaf("s1")
        right = _make_leaf("s2")
        combine = _make_combine("c1", left, right)
        graph.steps = {"s1": left, "s2": right, "c1": combine}
        graph.recompute_roots()
        assert graph.roots == {"c1"}

    def test_multiple_disconnected_roots(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        graph.steps = {"s1": _make_leaf("s1"), "s2": _make_leaf("s2")}
        graph.recompute_roots()
        assert graph.roots == {"s1", "s2"}

    def test_empty_graph(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        graph.recompute_roots()
        assert graph.roots == set()


class TestStrategySessionCreateGraph:
    def test_creates_new_graph(self) -> None:
        session = StrategySession("plasmodb")
        graph = session.create_graph("My Strategy", graph_id="g1")
        assert graph.id == "g1"
        assert graph.name == "My Strategy"
        assert session.graph is graph

    def test_returns_existing_graph(self) -> None:
        session = StrategySession("plasmodb")
        g1 = session.create_graph("First")
        g2 = session.create_graph("Second")
        assert g1 is g2
        assert g1.name == "Second"

    def test_auto_generates_id(self) -> None:
        session = StrategySession("plasmodb")
        graph = session.create_graph("Test")
        assert graph.id  # not empty


class TestStrategySessionAddGraph:
    def test_registers_graph(self) -> None:
        session = StrategySession("plasmodb")
        graph = StrategyGraph("g1", "Test", "plasmodb")
        session.add_graph(graph)
        assert session.graph is graph

    def test_ignores_different_graph_when_one_exists(self) -> None:
        session = StrategySession("plasmodb")
        g1 = StrategyGraph("g1", "First", "plasmodb")
        g2 = StrategyGraph("g2", "Second", "plasmodb")
        session.add_graph(g1)
        session.add_graph(g2)
        assert session.graph is g1

    def test_allows_same_graph_id(self) -> None:
        session = StrategySession("plasmodb")
        g1 = StrategyGraph("g1", "First", "plasmodb")
        session.add_graph(g1)
        g1_again = StrategyGraph("g1", "Updated", "plasmodb")
        session.add_graph(g1_again)
        assert session.graph is g1_again


class TestStrategySessionGetGraph:
    def test_returns_active_graph_for_none(self) -> None:
        session = StrategySession("plasmodb")
        graph = session.create_graph("Test", graph_id="g1")
        assert session.get_graph(None) is graph

    def test_returns_matching_graph(self) -> None:
        session = StrategySession("plasmodb")
        graph = session.create_graph("Test", graph_id="g1")
        assert session.get_graph("g1") is graph

    def test_returns_none_for_wrong_id(self) -> None:
        session = StrategySession("plasmodb")
        session.create_graph("Test", graph_id="g1")
        assert session.get_graph("g2") is None

    def test_returns_none_when_empty(self) -> None:
        session = StrategySession("plasmodb")
        assert session.get_graph(None) is None


class TestHydrateGraphFromStepsData:
    def test_hydrates_single_step(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1", "searchName": "GenesByTextSearch", "parameters": {}}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert "s1" in graph.steps
        assert graph.steps["s1"].search_name == "GenesByTextSearch"
        assert graph.roots == {"s1"}

    def test_hydrates_connected_steps(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [
            {"id": "s1", "searchName": "GenesByTextSearch"},
            {"id": "s2", "searchName": "GenesByGoTerm"},
            {
                "id": "c1",
                "searchName": "__combine__",
                "kind": "combine",
                "operator": "INTERSECT",
                "primaryInputStepId": "s1",
                "secondaryInputStepId": "s2",
            },
        ]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.roots == {"c1"}
        assert graph.steps["c1"].primary_input is graph.steps["s1"]
        assert graph.steps["c1"].secondary_input is graph.steps["s2"]

    def test_sets_record_type(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1", "searchName": "S1", "recordType": "gene"}]
        hydrate_graph_from_steps_data(graph, steps_data, record_type="gene")
        assert graph.record_type == "gene"

    def test_sets_last_step_id_from_root(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1", "searchName": "S1"}]
        hydrate_graph_from_steps_data(graph, steps_data, root_step_id="s1")
        assert graph.last_step_id == "s1"

    def test_single_root_auto_sets_last_step_id(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1", "searchName": "S1"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.last_step_id == "s1"

    def test_none_steps_data_is_noop(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        hydrate_graph_from_steps_data(graph, None)
        assert graph.steps == {}

    def test_empty_list_is_noop(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        hydrate_graph_from_steps_data(graph, [])
        assert graph.steps == {}

    def test_skips_steps_without_id(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"searchName": "S1"}, {"id": "s2", "searchName": "S2"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert len(graph.steps) == 1
        assert "s2" in graph.steps

    def test_missing_search_name_defaults(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1", "kind": "combine"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.steps["s1"].search_name == "__combine__"

    def test_hydrates_filters_analyses_reports(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [
            {
                "id": "s1",
                "searchName": "S1",
                "filters": [{"name": "ranked", "value": 5}],
                "analyses": [
                    {"analysisType": "enrichment", "parameters": {"go": "yes"}}
                ],
                "reports": [{"reportName": "tabular", "config": {"sep": ","}}],
            }
        ]
        hydrate_graph_from_steps_data(graph, steps_data)
        step = graph.steps["s1"]
        assert len(step.filters) == 1
        assert step.filters[0].name == "ranked"
        assert len(step.analyses) == 1
        assert step.analyses[0].analysis_type == "enrichment"
        assert len(step.reports) == 1
        assert step.reports[0].report_name == "tabular"

    def test_does_not_overwrite_existing_steps(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        existing = _make_leaf("s1", "OriginalSearch")
        graph.steps["s1"] = existing
        steps_data = [{"id": "s1", "searchName": "NewSearch"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.steps["s1"].search_name == "OriginalSearch"

    def test_record_type_from_step_data(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1", "searchName": "S1", "recordType": "gene"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.record_type == "gene"

    def test_numeric_step_ids(self) -> None:
        """Steps with numeric IDs should be coerced to strings."""
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [
            {"id": 1, "searchName": "S1"},
            {"id": 2, "searchName": "S2"},
            {
                "id": 3,
                "searchName": "__combine__",
                "kind": "combine",
                "primaryInputStepId": 1,
                "secondaryInputStepId": 2,
            },
        ]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert "1" in graph.steps
        assert "2" in graph.steps
        assert "3" in graph.steps
        assert graph.steps["3"].primary_input is graph.steps["1"]

    def test_hydrates_operator_and_colocation(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [
            {
                "id": "s1",
                "searchName": "S1",
                "operator": "INTERSECT",
                "colocationParams": {
                    "upstream": 100,
                    "downstream": 200,
                    "strand": "same",
                },
            }
        ]
        hydrate_graph_from_steps_data(graph, steps_data)
        step = graph.steps["s1"]
        assert step.operator == CombineOp.INTERSECT
        assert step.colocation_params is not None
        assert step.colocation_params.upstream == 100

    def test_invalid_operator_ignored(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1", "searchName": "S1", "operator": "BOGUS"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.steps["s1"].operator is None

    def test_skips_non_dict_items(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = ["not a dict", 42, {"id": "s1", "searchName": "S1"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert len(graph.steps) == 1

    def test_empty_string_step_id_skipped(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        # id=0 is falsy but str(0)="0" is truthy
        # id="" after str() is "" which is falsy -> skipped
        steps_data = [{"id": "", "searchName": "S1"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert len(graph.steps) == 0

    def test_missing_search_name_defaults_to_unknown(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.steps["s1"].search_name == "__unknown__"

    def test_display_name_defaults_to_search_name(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1", "searchName": "GenesByGoTerm"}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.steps["s1"].display_name == "GenesByGoTerm"

    def test_empty_display_name_defaults(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [{"id": "s1", "searchName": "S1", "displayName": "   "}]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.steps["s1"].display_name == "S1"

    def test_record_type_not_overwritten_if_already_set(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        graph.record_type = "transcript"
        steps_data = [{"id": "s1", "searchName": "S1"}]
        hydrate_graph_from_steps_data(graph, steps_data, record_type="gene")
        assert graph.record_type == "transcript"

    def test_multiple_roots_picks_arbitrary_last_step(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [
            {"id": "s1", "searchName": "S1"},
            {"id": "s2", "searchName": "S2"},
        ]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.last_step_id in {"s1", "s2"}

    def test_input_referencing_nonexistent_step_ignored(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        steps_data = [
            {
                "id": "s1",
                "searchName": "S1",
                "primaryInputStepId": "nonexistent",
            }
        ]
        hydrate_graph_from_steps_data(graph, steps_data)
        assert graph.steps["s1"].primary_input is None


class TestSaveHistory:
    def test_saves_when_strategy_exists(self) -> None:
        graph = _build_graph_with_strategy()
        graph.save_history("test")
        assert len(graph.history) == 1
        assert graph.history[0]["description"] == "test"
        assert "strategy" in graph.history[0]

    def test_noop_when_no_strategy(self) -> None:
        graph = StrategyGraph("g1", "Test", "plasmodb")
        graph.save_history("test")
        assert len(graph.history) == 0


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
        assert graph.current_strategy is not None
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
        assert graph.current_strategy is not None
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
        assert graph.current_strategy is not None
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

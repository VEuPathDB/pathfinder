"""Unit tests for services.strategies.step_builders."""

from veupath_chatbot.domain.strategy.ast import (
    PlanStepNode,
    StepAnalysis,
    StepFilter,
    StepReport,
    StrategyAST,
)
from veupath_chatbot.domain.strategy.ops import ColocationParams, CombineOp
from veupath_chatbot.services.strategies.step_builders import (
    _extract_input_ids,
    build_steps_data_from_ast,
)

# ── _extract_input_ids ────────────────────────────────────────────────


class TestExtractInputIds:
    def test_both_inputs(self) -> None:
        step_dict = {
            "primaryInput": {"id": "s1"},
            "secondaryInput": {"id": "s2"},
        }
        primary, secondary = _extract_input_ids(step_dict)
        assert primary == "s1"
        assert secondary == "s2"

    def test_primary_only(self) -> None:
        step_dict = {"primaryInput": {"id": "s1"}}
        primary, secondary = _extract_input_ids(step_dict)
        assert primary == "s1"
        assert secondary is None

    def test_no_inputs(self) -> None:
        step_dict = {}
        primary, secondary = _extract_input_ids(step_dict)
        assert primary is None
        assert secondary is None

    def test_secondary_only_returns_none_both(self) -> None:
        """Secondary without primary returns (None, None)."""
        step_dict = {"secondaryInput": {"id": "s2"}}
        primary, secondary = _extract_input_ids(step_dict)
        assert primary is None
        assert secondary is None

    def test_empty_dicts(self) -> None:
        step_dict = {"primaryInput": {}, "secondaryInput": {}}
        primary, secondary = _extract_input_ids(step_dict)
        assert primary is None
        assert secondary is None

    def test_non_dict_inputs_ignored(self) -> None:
        step_dict = {"primaryInput": "not-a-dict", "secondaryInput": 42}
        primary, secondary = _extract_input_ids(step_dict)
        assert primary is None
        assert secondary is None

    def test_numeric_id_converted_to_str(self) -> None:
        step_dict = {"primaryInput": {"id": 123}}
        primary, secondary = _extract_input_ids(step_dict)
        assert primary == "123"
        assert secondary is None


# ── build_steps_data_from_ast ─────────────────────────────────────────


class TestBuildStepsDataFromAst:
    def test_single_search_step(self) -> None:
        step = PlanStepNode(
            search_name="GenesByTextSearch",
            parameters={"text_expression": "kinase"},
            display_name="Text Search",
            id="s1",
        )
        ast = StrategyAST(record_type="gene", root=step)
        result = build_steps_data_from_ast(ast)
        assert len(result) == 1
        s = result[0]
        assert s["id"] == "s1"
        assert s["kind"] == "search"
        assert s["displayName"] == "Text Search"
        assert s["searchName"] == "GenesByTextSearch"
        assert s["recordType"] == "gene"
        assert s["parameters"] == {"text_expression": "kinase"}
        assert s["resultCount"] is None

    def test_transform_step(self) -> None:
        leaf = PlanStepNode(search_name="GenesByTextSearch", parameters={}, id="s1")
        transform = PlanStepNode(
            search_name="GenesByOrthologs",
            parameters={"organism": "Pf3D7"},
            primary_input=leaf,
            id="t1",
        )
        ast = StrategyAST(record_type="gene", root=transform)
        result = build_steps_data_from_ast(ast)
        assert len(result) == 2
        # Depth-first: leaf first, then transform
        assert result[0]["id"] == "s1"
        assert result[1]["id"] == "t1"
        assert result[1]["kind"] == "transform"
        assert result[1]["primaryInputStepId"] == "s1"
        assert result[1]["secondaryInputStepId"] is None

    def test_combine_step(self) -> None:
        left = PlanStepNode(search_name="S1", parameters={}, id="s1")
        right = PlanStepNode(search_name="S2", parameters={}, id="s2")
        combine = PlanStepNode(
            search_name="BooleanQuestion",
            parameters={},
            primary_input=left,
            secondary_input=right,
            operator=CombineOp.UNION,
            id="c1",
        )
        ast = StrategyAST(record_type="gene", root=combine)
        result = build_steps_data_from_ast(ast)
        assert len(result) == 3
        # Depth-first: left, right, combine
        assert result[0]["id"] == "s1"
        assert result[1]["id"] == "s2"
        assert result[2]["id"] == "c1"
        assert result[2]["kind"] == "combine"
        assert result[2]["operator"] == "UNION"
        assert result[2]["primaryInputStepId"] == "s1"
        assert result[2]["secondaryInputStepId"] == "s2"

    def test_wdk_step_id_from_numeric_id(self) -> None:
        """When step ID is a digit string, wdkStepId is set."""
        step = PlanStepNode(search_name="S1", parameters={}, id="42")
        ast = StrategyAST(record_type="gene", root=step)
        result = build_steps_data_from_ast(ast)
        assert result[0]["wdkStepId"] == 42

    def test_wdk_step_id_none_for_local_id(self) -> None:
        """When step ID is a local UUID-like id, wdkStepId is None."""
        step = PlanStepNode(search_name="S1", parameters={}, id="step_abc123")
        ast = StrategyAST(record_type="gene", root=step)
        result = build_steps_data_from_ast(ast)
        assert result[0]["wdkStepId"] is None

    def test_filters_analyses_reports_included(self) -> None:
        step = PlanStepNode(
            search_name="S1",
            parameters={},
            id="s1",
            filters=[StepFilter(name="ranked", value=5)],
            analyses=[
                StepAnalysis(analysis_type="enrichment", parameters={"go": "yes"})
            ],
            reports=[StepReport(report_name="tabular", config={"sep": ","})],
        )
        ast = StrategyAST(record_type="gene", root=step)
        result = build_steps_data_from_ast(ast)
        s = result[0]
        assert s["filters"] is not None
        assert len(s["filters"]) == 1
        assert s["analyses"] is not None
        assert len(s["analyses"]) == 1
        assert s["reports"] is not None
        assert len(s["reports"]) == 1

    def test_colocation_params_included(self) -> None:
        left = PlanStepNode(search_name="S1", parameters={}, id="s1")
        right = PlanStepNode(search_name="S2", parameters={}, id="s2")
        combine = PlanStepNode(
            search_name="BooleanQuestion",
            parameters={},
            primary_input=left,
            secondary_input=right,
            operator=CombineOp.COLOCATE,
            colocation_params=ColocationParams(
                upstream=1000, downstream=500, strand="same"
            ),
            id="c1",
        )
        ast = StrategyAST(record_type="gene", root=combine)
        result = build_steps_data_from_ast(ast)
        colocation = result[2].get("colocationParams")
        assert colocation is not None
        assert colocation["upstream"] == 1000
        assert colocation["downstream"] == 500
        assert colocation["strand"] == "same"

    def test_record_type_none_when_ast_has_none(self) -> None:
        step = PlanStepNode(search_name="S1", parameters={}, id="s1")
        ast = StrategyAST(record_type="", root=step)
        result = build_steps_data_from_ast(ast)
        assert result[0]["recordType"] is None

    def test_deeply_nested_tree(self) -> None:
        """Test a 4-step tree with nested combines."""
        s1 = PlanStepNode(search_name="S1", parameters={}, id="s1")
        s2 = PlanStepNode(search_name="S2", parameters={}, id="s2")
        s3 = PlanStepNode(search_name="S3", parameters={}, id="s3")
        c1 = PlanStepNode(
            search_name="BQ",
            parameters={},
            primary_input=s1,
            secondary_input=s2,
            operator=CombineOp.INTERSECT,
            id="c1",
        )
        c2 = PlanStepNode(
            search_name="BQ",
            parameters={},
            primary_input=c1,
            secondary_input=s3,
            operator=CombineOp.UNION,
            id="c2",
        )
        ast = StrategyAST(record_type="gene", root=c2)
        result = build_steps_data_from_ast(ast)
        assert len(result) == 5
        ids = [s["id"] for s in result]
        # Depth-first: s1, s2, c1, s3, c2
        assert ids == ["s1", "s2", "c1", "s3", "c2"]

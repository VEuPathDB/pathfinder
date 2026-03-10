"""Unit tests for services.strategies.wdk_bridge pure functions."""

import pytest

from veupath_chatbot.services.strategies.wdk_bridge import (
    _build_node_from_wdk,
    _build_snapshot_from_wdk,
    _extract_estimated_size,
    _extract_operator,
    _extract_record_type,
    _get_step_info,
    _plan_cache_key,
    extract_wdk_is_saved,
    parse_wdk_strategy_id,
)

# ── extract_wdk_is_saved ──────────────────────────────────────────────


class TestExtractWdkIsSaved:
    def test_true_when_saved(self) -> None:
        assert extract_wdk_is_saved({"isSaved": True}) is True

    def test_false_when_not_saved(self) -> None:
        assert extract_wdk_is_saved({"isSaved": False}) is False

    def test_false_when_missing(self) -> None:
        assert extract_wdk_is_saved({}) is False

    def test_false_for_non_bool(self) -> None:
        # Non-bool values are treated as False (isinstance guard)
        assert extract_wdk_is_saved({"isSaved": "yes"}) is False

    def test_false_for_none(self) -> None:
        assert extract_wdk_is_saved({"isSaved": None}) is False

    def test_false_for_non_dict(self) -> None:
        # Technically should not happen, but the guard handles it
        assert extract_wdk_is_saved("not a dict") is False  # type: ignore[arg-type]


# ── parse_wdk_strategy_id ─────────────────────────────────────────────


class TestParseWdkStrategyId:
    def test_valid_int_id(self) -> None:
        assert parse_wdk_strategy_id({"strategyId": 42}) == 42

    def test_string_id_returns_none(self) -> None:
        assert parse_wdk_strategy_id({"strategyId": "42"}) is None

    def test_missing_returns_none(self) -> None:
        assert parse_wdk_strategy_id({}) is None

    def test_none_value_returns_none(self) -> None:
        assert parse_wdk_strategy_id({"strategyId": None}) is None


# ── _extract_record_type ──────────────────────────────────────────────


class TestExtractRecordType:
    def test_valid_record_type(self) -> None:
        assert _extract_record_type({"recordClassName": "gene"}) == "gene"

    def test_strips_whitespace(self) -> None:
        assert _extract_record_type({"recordClassName": "  gene  "}) == "gene"

    def test_missing_raises(self) -> None:
        with pytest.raises(ValueError, match="recordClassName"):
            _extract_record_type({})

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="recordClassName"):
            _extract_record_type({"recordClassName": ""})

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="recordClassName"):
            _extract_record_type({"recordClassName": 42})


# ── _get_step_info ────────────────────────────────────────────────────


class TestGetStepInfo:
    def test_returns_step_dict(self) -> None:
        steps = {"123": {"searchName": "GenesByTextSearch"}}
        result = _get_step_info(steps, 123)
        assert result["searchName"] == "GenesByTextSearch"

    def test_missing_step_raises(self) -> None:
        steps = {"456": {"searchName": "S1"}}
        with pytest.raises(ValueError, match="Step 123 not found"):
            _get_step_info(steps, 123)


# ── _extract_operator ─────────────────────────────────────────────────


class TestExtractOperator:
    def test_extracts_bq_operator(self) -> None:
        assert _extract_operator({"bq_operator": "INTERSECT"}) == "INTERSECT"

    def test_extracts_from_any_operator_key(self) -> None:
        assert _extract_operator({"some_operator_key": "UNION"}) == "UNION"

    def test_list_value_takes_first(self) -> None:
        assert _extract_operator({"bq_operator": ["MINUS"]}) == "MINUS"

    def test_empty_params_returns_none(self) -> None:
        assert _extract_operator({}) is None

    def test_none_params_returns_none(self) -> None:
        assert _extract_operator(None) is None

    def test_no_operator_key_returns_none(self) -> None:
        assert _extract_operator({"foo": "bar", "baz": 42}) is None


# ── _extract_estimated_size ───────────────────────────────────────────


class TestExtractEstimatedSize:
    def test_valid_int(self) -> None:
        assert _extract_estimated_size({"estimatedSize": 42}) == 42

    def test_missing_returns_none(self) -> None:
        assert _extract_estimated_size({}) is None

    def test_string_returns_none(self) -> None:
        assert _extract_estimated_size({"estimatedSize": "42"}) is None

    def test_zero(self) -> None:
        assert _extract_estimated_size({"estimatedSize": 0}) == 0


# ── _plan_cache_key ───────────────────────────────────────────────────


class TestPlanCacheKey:
    def test_deterministic(self) -> None:
        plan = {"recordType": "gene", "root": {"searchName": "S1"}}
        key1 = _plan_cache_key("plasmodb", plan)
        key2 = _plan_cache_key("plasmodb", plan)
        assert key1 == key2

    def test_different_sites_produce_different_keys(self) -> None:
        plan = {"recordType": "gene"}
        key1 = _plan_cache_key("plasmodb", plan)
        key2 = _plan_cache_key("toxodb", plan)
        assert key1 != key2

    def test_different_plans_produce_different_keys(self) -> None:
        key1 = _plan_cache_key("plasmodb", {"recordType": "gene"})
        key2 = _plan_cache_key("plasmodb", {"recordType": "transcript"})
        assert key1 != key2


# ── _build_node_from_wdk ─────────────────────────────────────────────


def _wdk_step(step_id: int, search_name: str, params: dict | None = None) -> dict:
    return {
        "searchName": search_name,
        "searchConfig": {"parameters": params or {}},
    }


class TestBuildNodeFromWdk:
    def test_leaf_step(self) -> None:
        step_tree = {"stepId": 1}
        steps = {"1": _wdk_step(1, "GenesByTextSearch", {"text_expression": "kinase"})}
        node = _build_node_from_wdk(step_tree, steps, "gene")
        assert node.search_name == "GenesByTextSearch"
        assert node.id == "1"
        assert node.parameters == {"text_expression": "kinase"}
        assert node.primary_input is None
        assert node.secondary_input is None

    def test_transform_step(self) -> None:
        step_tree = {
            "stepId": 2,
            "primaryInput": {"stepId": 1},
        }
        steps = {
            "1": _wdk_step(1, "GenesByTextSearch"),
            "2": _wdk_step(2, "GenesByOrthologs", {"organism": "Pf3D7"}),
        }
        node = _build_node_from_wdk(step_tree, steps, "gene")
        assert node.search_name == "GenesByOrthologs"
        assert node.primary_input is not None
        assert node.primary_input.search_name == "GenesByTextSearch"
        assert node.secondary_input is None

    def test_combine_step(self) -> None:
        step_tree = {
            "stepId": 3,
            "primaryInput": {"stepId": 1},
            "secondaryInput": {"stepId": 2},
        }
        steps = {
            "1": _wdk_step(1, "GenesByTextSearch"),
            "2": _wdk_step(2, "GenesByGoTerm"),
            "3": _wdk_step(3, "BooleanQuestion", {"bq_operator": "INTERSECT"}),
        }
        node = _build_node_from_wdk(step_tree, steps, "gene")
        assert node.infer_kind() == "combine"
        assert node.operator is not None
        assert node.operator.value == "INTERSECT"
        assert node.primary_input is not None
        assert node.secondary_input is not None

    def test_missing_step_id_raises(self) -> None:
        with pytest.raises(ValueError, match="stepId"):
            _build_node_from_wdk({"stepId": "not_an_int"}, {}, "gene")

    def test_missing_search_name_raises(self) -> None:
        step_tree = {"stepId": 1}
        steps = {"1": {"searchConfig": {"parameters": {}}}}
        with pytest.raises(ValueError, match="searchName"):
            _build_node_from_wdk(step_tree, steps, "gene")

    def test_missing_search_config_raises(self) -> None:
        step_tree = {"stepId": 1}
        steps = {"1": {"searchName": "S1"}}
        with pytest.raises(ValueError, match="searchConfig"):
            _build_node_from_wdk(step_tree, steps, "gene")

    def test_combine_without_operator_raises(self) -> None:
        step_tree = {
            "stepId": 3,
            "primaryInput": {"stepId": 1},
            "secondaryInput": {"stepId": 2},
        }
        steps = {
            "1": _wdk_step(1, "S1"),
            "2": _wdk_step(2, "S2"),
            "3": _wdk_step(3, "BQ", {}),
        }
        with pytest.raises(ValueError, match="boolean operator"):
            _build_node_from_wdk(step_tree, steps, "gene")

    def test_custom_name_preferred(self) -> None:
        step_tree = {"stepId": 1}
        steps = {
            "1": {
                "searchName": "GenesByTextSearch",
                "searchConfig": {"parameters": {}},
                "customName": "My Custom Step",
                "displayName": "Text Search",
            }
        }
        node = _build_node_from_wdk(step_tree, steps, "gene")
        assert node.display_name == "My Custom Step"

    def test_display_name_fallback(self) -> None:
        step_tree = {"stepId": 1}
        steps = {
            "1": {
                "searchName": "GenesByTextSearch",
                "searchConfig": {"parameters": {}},
                "displayName": "Text Search",
            }
        }
        node = _build_node_from_wdk(step_tree, steps, "gene")
        assert node.display_name == "Text Search"


# ── _build_snapshot_from_wdk ──────────────────────────────────────────


class TestBuildSnapshotFromWdk:
    def test_simple_strategy(self) -> None:
        wdk_strategy = {
            "recordClassName": "gene",
            "name": "My Strategy",
            "description": "Test description",
            "stepTree": {"stepId": 1},
            "steps": {
                "1": _wdk_step(1, "GenesByTextSearch", {"text_expression": "kinase"})
            },
        }
        ast, steps_data, _ = _build_snapshot_from_wdk(wdk_strategy)
        assert ast.record_type == "gene"
        assert ast.name == "My Strategy"
        assert ast.description == "Test description"
        assert ast.root.search_name == "GenesByTextSearch"
        assert len(steps_data) == 1

    def test_combine_strategy(self) -> None:
        wdk_strategy = {
            "recordClassName": "gene",
            "name": "Combined",
            "stepTree": {
                "stepId": 3,
                "primaryInput": {"stepId": 1},
                "secondaryInput": {"stepId": 2},
            },
            "steps": {
                "1": _wdk_step(1, "GenesByTextSearch"),
                "2": _wdk_step(2, "GenesByGoTerm"),
                "3": _wdk_step(3, "BooleanQuestion", {"bq_operator": "UNION"}),
            },
        }
        ast, steps_data, _ = _build_snapshot_from_wdk(wdk_strategy)
        assert ast.root.infer_kind() == "combine"
        assert len(steps_data) == 3

    def test_missing_step_tree_raises(self) -> None:
        with pytest.raises(ValueError, match="stepTree"):
            _build_snapshot_from_wdk({"recordClassName": "gene", "steps": {}})

    def test_missing_steps_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="steps"):
            _build_snapshot_from_wdk(
                {"recordClassName": "gene", "stepTree": {"stepId": 1}}
            )

    def test_wdk_step_ids_populated(self) -> None:
        wdk_strategy = {
            "recordClassName": "gene",
            "stepTree": {"stepId": 42},
            "steps": {"42": _wdk_step(42, "GenesByTextSearch")},
        }
        ast, steps_data, _ = _build_snapshot_from_wdk(wdk_strategy)
        # The step ID should be the string version of the WDK step ID
        assert ast.root.id == "42"
        # steps_data should have wdkStepId populated
        assert steps_data[0]["wdkStepId"] == 42

    def test_estimated_size_from_wdk(self) -> None:
        wdk_strategy = {
            "recordClassName": "gene",
            "stepTree": {"stepId": 1},
            "steps": {
                "1": {
                    "searchName": "GenesByTextSearch",
                    "searchConfig": {"parameters": {}},
                    "estimatedSize": 500,
                }
            },
        }
        _, steps_data, _ = _build_snapshot_from_wdk(wdk_strategy)
        assert steps_data[0]["resultCount"] == 500

    def test_missing_name_is_none(self) -> None:
        wdk_strategy = {
            "recordClassName": "gene",
            "stepTree": {"stepId": 1},
            "steps": {"1": _wdk_step(1, "S1")},
        }
        ast, _, _ = _build_snapshot_from_wdk(wdk_strategy)
        assert ast.name is None

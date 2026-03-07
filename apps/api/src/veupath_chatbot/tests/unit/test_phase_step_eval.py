"""Tests for phase_step_eval.py and _evaluation.py helpers.

Tests focus on pure functions:
- _extract_eval_counts from various result shapes
- _f1 approximation function
- _collect_combine_nodes for tree structure analysis
- _build_subtree_with_operator for operator swaps
"""

from __future__ import annotations

import pytest

from veupath_chatbot.services.experiment.step_analysis._evaluation import (
    _extract_eval_counts,
    _f1,
)
from veupath_chatbot.services.experiment.step_analysis._tree_utils import (
    _build_subtree_with_operator,
    _collect_combine_nodes,
    _node_id,
)


class TestExtractEvalCounts:
    """_extract_eval_counts pulls structured counts from control-test results."""

    def test_complete_result(self) -> None:
        result = {
            "positive": {
                "controlsCount": 10,
                "intersectionCount": 8,
                "intersectionIds": ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"],
            },
            "negative": {
                "controlsCount": 20,
                "intersectionCount": 3,
                "intersectionIds": ["N1", "N2", "N3"],
            },
            "target": {"resultCount": 100},
        }
        counts = _extract_eval_counts(result)
        assert counts.pos_hits == 8
        assert counts.pos_total == 10
        assert counts.neg_hits == 3
        assert counts.neg_total == 20
        assert counts.total_results == 100
        assert len(counts.pos_ids) == 8
        assert len(counts.neg_ids) == 3

    def test_empty_result(self) -> None:
        counts = _extract_eval_counts({})
        assert counts.pos_hits == 0
        assert counts.pos_total == 0
        assert counts.neg_hits == 0
        assert counts.neg_total == 0
        assert counts.total_results == 0
        assert counts.pos_ids == []
        assert counts.neg_ids == []

    def test_none_sections(self) -> None:
        result = {"positive": None, "negative": None, "target": None}
        counts = _extract_eval_counts(result)
        assert counts.pos_hits == 0
        assert counts.total_results == 0

    def test_string_sections(self) -> None:
        """Non-dict sections fall through to empty."""
        result = {"positive": "invalid", "negative": 42, "target": []}
        counts = _extract_eval_counts(result)
        assert counts.pos_hits == 0

    def test_missing_intersection_ids(self) -> None:
        """When intersectionIds is not present, pos_ids is empty."""
        result = {
            "positive": {"controlsCount": 5, "intersectionCount": 3},
            "negative": {"controlsCount": 10, "intersectionCount": 1},
            "target": {"resultCount": 50},
        }
        counts = _extract_eval_counts(result)
        assert counts.pos_hits == 3
        assert counts.pos_ids == []
        assert counts.neg_ids == []

    def test_non_list_intersection_ids(self) -> None:
        """Non-list intersectionIds returns empty list."""
        result = {
            "positive": {
                "controlsCount": 5,
                "intersectionCount": 3,
                "intersectionIds": "G1,G2,G3",
            },
        }
        counts = _extract_eval_counts(result)
        assert counts.pos_ids == []

    def test_intersection_ids_with_non_string_entries(self) -> None:
        """Non-string entries in intersectionIds are converted via str()."""
        result = {
            "positive": {
                "controlsCount": 2,
                "intersectionCount": 2,
                "intersectionIds": [123, None],
            },
        }
        counts = _extract_eval_counts(result)
        assert counts.pos_ids == ["123", "None"]


class TestF1Approximation:
    """_f1 approximates F1 from recall and FPR."""

    def test_perfect_classifier(self) -> None:
        """recall=1, fpr=0 -> specificity=1, precision~=1 -> F1~=1."""
        result = _f1(1.0, 0.0, 10)
        assert result == pytest.approx(1.0)

    def test_zero_recall(self) -> None:
        """recall=0 -> F1=0 regardless of FPR."""
        assert _f1(0.0, 0.5, 10) == 0.0

    def test_zero_recall_and_zero_precision(self) -> None:
        """Both zero -> denom=0 -> F1=0."""
        assert _f1(0.0, 1.0, 10) == 0.0

    def test_no_negatives(self) -> None:
        """When neg_total=0, specificity defaults to 1.0."""
        result = _f1(0.8, 0.5, 0)
        # specificity = 1.0 (because neg_total=0), precision proxy = 1.0
        # F1 = 2 * 1.0 * 0.8 / (1.0 + 0.8) = 1.6 / 1.8
        expected = 2 * 1.0 * 0.8 / (1.0 + 0.8)
        assert result == pytest.approx(expected)

    def test_high_fpr(self) -> None:
        """fpr=1.0 -> specificity=0 -> precision proxy=0 -> F1=0."""
        result = _f1(0.8, 1.0, 10)
        # specificity = 0.0, precision = 0.0, denom = 0.0 + 0.8 = 0.8
        # F1 = 2 * 0.0 * 0.8 / 0.8 = 0.0
        assert result == 0.0

    def test_moderate_values(self) -> None:
        result = _f1(0.7, 0.2, 10)
        # specificity = 0.8, precision proxy = 0.8
        # F1 = 2 * 0.8 * 0.7 / (0.8 + 0.7) = 1.12 / 1.5
        expected = 2 * 0.8 * 0.7 / (0.8 + 0.7)
        assert result == pytest.approx(expected)


class TestCollectCombineNodes:
    """_collect_combine_nodes identifies binary (combine) nodes."""

    def test_single_leaf_no_combine(self) -> None:
        tree = {"id": "s1", "searchName": "A"}
        assert _collect_combine_nodes(tree) == []

    def test_single_combine(self) -> None:
        tree = {
            "id": "root",
            "operator": "INTERSECT",
            "primaryInput": {"id": "s1", "searchName": "A"},
            "secondaryInput": {"id": "s2", "searchName": "B"},
        }
        nodes = _collect_combine_nodes(tree)
        assert len(nodes) == 1
        assert _node_id(nodes[0]) == "root"

    def test_nested_combines(self) -> None:
        tree = {
            "id": "root",
            "operator": "UNION",
            "primaryInput": {
                "id": "mid",
                "operator": "INTERSECT",
                "primaryInput": {"id": "s1", "searchName": "A"},
                "secondaryInput": {"id": "s2", "searchName": "B"},
            },
            "secondaryInput": {"id": "s3", "searchName": "C"},
        }
        nodes = _collect_combine_nodes(tree)
        assert len(nodes) == 2
        ids = {_node_id(n) for n in nodes}
        assert ids == {"root", "mid"}

    def test_transform_node_not_combine(self) -> None:
        """Transform (unary) nodes have primaryInput but no secondaryInput."""
        tree = {
            "id": "root",
            "operator": "UNION",
            "primaryInput": {
                "id": "transform",
                "searchName": "GenesByOrthologs",
                "primaryInput": {"id": "s1", "searchName": "GeneByTaxon"},
            },
            "secondaryInput": {"id": "s2", "searchName": "B"},
        }
        nodes = _collect_combine_nodes(tree)
        assert len(nodes) == 1
        assert _node_id(nodes[0]) == "root"


class TestBuildSubtreeWithOperator:
    """_build_subtree_with_operator clones a subtree with a new operator."""

    def test_changes_operator(self) -> None:
        combine = {
            "id": "root",
            "operator": "INTERSECT",
            "primaryInput": {"id": "s1", "searchName": "A"},
            "secondaryInput": {"id": "s2", "searchName": "B"},
        }
        result = _build_subtree_with_operator(combine, "UNION")
        assert result["operator"] == "UNION"
        assert result["id"] == "root"

    def test_does_not_mutate_original(self) -> None:
        combine = {
            "id": "root",
            "operator": "INTERSECT",
            "primaryInput": {"id": "s1", "searchName": "A"},
            "secondaryInput": {"id": "s2", "searchName": "B"},
        }
        _build_subtree_with_operator(combine, "UNION")
        assert combine["operator"] == "INTERSECT"

    def test_deep_copy_subtree(self) -> None:
        """Modifying the result should not affect the original subtree."""
        combine = {
            "id": "root",
            "operator": "INTERSECT",
            "primaryInput": {"id": "s1", "searchName": "A", "params": {"x": 1}},
            "secondaryInput": {"id": "s2", "searchName": "B"},
        }
        result = _build_subtree_with_operator(combine, "UNION")
        # Modify nested structure in result
        pi = result["primaryInput"]
        assert isinstance(pi, dict)
        pi_params = pi.get("params")
        assert isinstance(pi_params, dict)
        pi_params["x"] = 999

        # Original should be unchanged
        orig_pi = combine["primaryInput"]
        assert isinstance(orig_pi, dict)
        assert orig_pi["params"]["x"] == 1  # type: ignore[index]


class TestNodeId:
    """_node_id extracts the node identifier."""

    def test_id_field(self) -> None:
        assert _node_id({"id": "s1"}) == "s1"

    def test_search_name_fallback(self) -> None:
        assert _node_id({"searchName": "GeneByTaxon"}) == "GeneByTaxon"

    def test_both_prefers_id(self) -> None:
        assert _node_id({"id": "s1", "searchName": "GeneByTaxon"}) == "s1"

    def test_neither_returns_question_mark(self) -> None:
        assert _node_id({}) == "?"

    def test_non_string_id(self) -> None:
        """Non-string IDs are converted via str()."""
        assert _node_id({"id": 42}) == "42"

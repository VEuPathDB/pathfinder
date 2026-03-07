"""Unit tests for step_analysis._evaluation -- pure extraction and metric functions."""

from veupath_chatbot.services.experiment.step_analysis._evaluation import (
    _EvalCounts,
    _extract_eval_counts,
    _f1_from_counts,
)

# ---------------------------------------------------------------------------
# _EvalCounts dataclass
# ---------------------------------------------------------------------------


class TestEvalCounts:
    def test_defaults(self) -> None:
        ec = _EvalCounts()
        assert ec.pos_hits == 0
        assert ec.pos_total == 0
        assert ec.neg_hits == 0
        assert ec.neg_total == 0
        assert ec.total_results == 0
        assert ec.pos_ids == []
        assert ec.neg_ids == []

    def test_custom_values(self) -> None:
        ec = _EvalCounts(pos_hits=5, pos_total=10, neg_hits=2, neg_total=8)
        assert ec.pos_hits == 5
        assert ec.neg_total == 8


# ---------------------------------------------------------------------------
# _extract_eval_counts
# ---------------------------------------------------------------------------


class TestExtractEvalCounts:
    def test_full_result(self) -> None:
        result = {
            "positive": {
                "intersectionCount": 8,
                "controlsCount": 10,
                "intersectionIds": ["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"],
            },
            "negative": {
                "intersectionCount": 3,
                "controlsCount": 20,
                "intersectionIds": ["n1", "n2", "n3"],
            },
            "target": {
                "resultCount": 150,
            },
        }
        ec = _extract_eval_counts(result)
        assert ec.pos_hits == 8
        assert ec.pos_total == 10
        assert ec.neg_hits == 3
        assert ec.neg_total == 20
        assert ec.total_results == 150
        assert len(ec.pos_ids) == 8
        assert len(ec.neg_ids) == 3

    def test_empty_result(self) -> None:
        ec = _extract_eval_counts({})
        assert ec.pos_hits == 0
        assert ec.pos_total == 0
        assert ec.neg_hits == 0
        assert ec.neg_total == 0
        assert ec.total_results == 0
        assert ec.pos_ids == []
        assert ec.neg_ids == []

    def test_none_sections(self) -> None:
        """When positive/negative/target are None."""
        result = {"positive": None, "negative": None, "target": None}
        ec = _extract_eval_counts(result)
        assert ec.pos_hits == 0
        assert ec.neg_hits == 0
        assert ec.total_results == 0

    def test_non_dict_sections_ignored(self) -> None:
        """When positive/negative/target are strings or ints."""
        result = {"positive": "oops", "negative": 42, "target": [1, 2]}
        ec = _extract_eval_counts(result)
        assert ec.pos_hits == 0
        assert ec.neg_hits == 0
        assert ec.total_results == 0

    def test_string_counts_coerced(self) -> None:
        """safe_int should handle string representations of numbers."""
        result = {
            "positive": {
                "intersectionCount": "5",
                "controlsCount": "10",
            },
            "negative": {
                "intersectionCount": "2",
                "controlsCount": "8",
            },
            "target": {"resultCount": "100"},
        }
        ec = _extract_eval_counts(result)
        assert ec.pos_hits == 5
        assert ec.pos_total == 10
        assert ec.neg_hits == 2
        assert ec.neg_total == 8
        assert ec.total_results == 100

    def test_intersection_ids_non_list_returns_empty(self) -> None:
        """When intersectionIds is a string or None."""
        result = {
            "positive": {"intersectionIds": "not_a_list"},
            "negative": {"intersectionIds": None},
        }
        ec = _extract_eval_counts(result)
        assert ec.pos_ids == []
        assert ec.neg_ids == []

    def test_intersection_ids_with_mixed_types(self) -> None:
        """IDs containing ints are converted to strings."""
        result = {
            "positive": {"intersectionIds": [123, "g2", None]},
        }
        ec = _extract_eval_counts(result)
        assert ec.pos_ids == ["123", "g2", "None"]

    def test_only_positive_present(self) -> None:
        result = {
            "positive": {"intersectionCount": 3, "controlsCount": 5},
        }
        ec = _extract_eval_counts(result)
        assert ec.pos_hits == 3
        assert ec.pos_total == 5
        assert ec.neg_hits == 0
        assert ec.neg_total == 0


# ---------------------------------------------------------------------------
# _f1_from_counts
# ---------------------------------------------------------------------------


class TestF1FromCounts:
    def test_perfect_scores(self) -> None:
        """All positives found, no negatives found => F1=1.0."""
        counts = _EvalCounts(pos_hits=10, pos_total=10, neg_hits=0, neg_total=10)
        assert _f1_from_counts(counts) == 1.0

    def test_zero_recall(self) -> None:
        """No positives found => F1=0.0."""
        counts = _EvalCounts(pos_hits=0, pos_total=10, neg_hits=5, neg_total=10)
        assert _f1_from_counts(counts) == 0.0

    def test_both_zero(self) -> None:
        """No positives, no negatives => F1=0.0."""
        counts = _EvalCounts(pos_hits=0, pos_total=0, neg_hits=0, neg_total=0)
        assert _f1_from_counts(counts) == 0.0

    def test_no_negatives(self) -> None:
        """When neg_total=0 and half positives found, precision=1.0."""
        # tp=5, fp=0, fn=5 => precision=1.0, recall=0.5
        # F1 = 2*1.0*0.5/(1.0+0.5) = 2/3
        counts = _EvalCounts(pos_hits=5, pos_total=10, neg_hits=0, neg_total=0)
        expected = 2 * 1.0 * 0.5 / (1.0 + 0.5)
        assert abs(_f1_from_counts(counts) - expected) < 1e-10

    def test_moderate_scores(self) -> None:
        """tp=8, fp=2, fn=2, tn=8 => precision=0.8, recall=0.8 => F1=0.8."""
        counts = _EvalCounts(pos_hits=8, pos_total=10, neg_hits=2, neg_total=10)
        assert abs(_f1_from_counts(counts) - 0.8) < 1e-10

    def test_high_false_positives(self) -> None:
        """Many negatives found => low precision => low F1."""
        # tp=9, fp=9, fn=1, tn=1 => precision=0.5, recall=0.9
        # F1 = 2*0.5*0.9/(0.5+0.9) = 0.9/1.4
        counts = _EvalCounts(pos_hits=9, pos_total=10, neg_hits=9, neg_total=10)
        expected = 2 * 0.5 * 0.9 / (0.5 + 0.9)
        assert abs(_f1_from_counts(counts) - expected) < 1e-10

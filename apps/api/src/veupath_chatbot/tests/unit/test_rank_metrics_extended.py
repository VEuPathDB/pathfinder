"""Bug-hunting tests for rank_metrics.py — edge cases and correctness.

Extends the existing test_experiment_rank_metrics.py with:
- Duplicate gene IDs in results
- Positives not in result list at all
- Single-element result list
- Very large k_values
- All results are positives
- All results are negatives
- Enrichment@K when random_precision is very small
- PR curve sampling correctness
"""

from __future__ import annotations

import pytest

from veupath_chatbot.services.experiment.rank_metrics import compute_rank_metrics
from veupath_chatbot.services.experiment.types import DEFAULT_K_VALUES


class TestRankMetricsEdgeCases:
    """Edge cases not covered by existing tests."""

    def test_single_result_is_positive(self) -> None:
        rm = compute_rank_metrics(["g1"], {"g1"}, set(), k_values=[1])
        assert rm.precision_at_k[1] == 1.0
        assert rm.recall_at_k[1] == 1.0
        assert rm.total_results == 1

    def test_single_result_is_negative(self) -> None:
        rm = compute_rank_metrics(["n1"], {"g1"}, {"n1"}, k_values=[1])
        assert rm.precision_at_k[1] == 0.0
        assert rm.recall_at_k[1] == 0.0

    def test_all_results_are_positives(self) -> None:
        """When every result is a positive control."""
        ids = [f"g{i}" for i in range(10)]
        pos = set(ids)
        rm = compute_rank_metrics(ids, pos, set(), k_values=[5, 10])
        assert rm.precision_at_k[5] == 1.0
        assert rm.precision_at_k[10] == 1.0
        assert rm.recall_at_k[5] == 0.5  # 5/10
        assert rm.recall_at_k[10] == 1.0

    def test_no_positives_in_results(self) -> None:
        """Positives exist but none appear in results."""
        rm = compute_rank_metrics(
            ["n1", "n2", "n3"], {"g1", "g2"}, {"n1", "n2", "n3"}, k_values=[3]
        )
        assert rm.precision_at_k[3] == 0.0
        assert rm.recall_at_k[3] == 0.0

    def test_duplicate_gene_ids_in_results(self) -> None:
        """Duplicate IDs are deduplicated before computing metrics.

        After dedup, ["g1", "g1", "n1"] -> ["g1", "n1"] (total=2).
        At k=2: cumulative_hits=1, P@2=0.5, R@2=1.0.
        """
        rm = compute_rank_metrics(["g1", "g1", "n1"], {"g1"}, {"n1"}, k_values=[2])
        assert rm.total_results == 2
        assert rm.precision_at_k[2] == 0.5
        assert rm.recall_at_k[2] == 1.0

    def test_k_value_of_zero(self) -> None:
        """k=0 should not appear in main loop (k starts at 1).

        The fallback path handles it: effective_k = min(0, total) = 0,
        P@0 = 0/0 which guard says 0.0.
        """
        rm = compute_rank_metrics(["g1", "g2"], {"g1"}, set(), k_values=[0])
        assert rm.precision_at_k[0] == 0.0

    def test_default_k_values_used(self) -> None:
        """When k_values is None, DEFAULT_K_VALUES is used."""
        ids = [f"g{i}" for i in range(200)]
        pos = {f"g{i}" for i in range(10)}
        rm = compute_rank_metrics(ids, pos, set())
        for kv in DEFAULT_K_VALUES:
            assert kv in rm.precision_at_k

    def test_enrichment_when_random_precision_very_small(self) -> None:
        """Enrichment = P@K / random_precision. When random_precision is tiny
        but nonzero, enrichment can be very large."""
        # 1 positive in 10000 results, at top
        ids = ["g1"] + [f"n{i}" for i in range(9999)]
        pos = {"g1"}
        rm = compute_rank_metrics(ids, pos, set(), k_values=[1])
        # P@1 = 1.0, random = 1/10000 = 0.0001
        # enrichment = 1.0 / 0.0001 = 10000.0
        assert rm.enrichment_at_k[1] == pytest.approx(10000.0)

    def test_pr_curve_includes_last_point(self) -> None:
        """PR curve should include the final point (k == total)."""
        ids = [f"g{i}" for i in range(10)]
        pos = {"g0"}
        rm = compute_rank_metrics(ids, pos, set(), k_values=[10])
        # Last point should be (precision_at_total, recall_at_total)
        last_point = rm.pr_curve[-1]
        assert last_point[1] == 1.0  # recall at end should be 1.0

    def test_list_size_vs_recall_monotonic(self) -> None:
        """list_size_vs_recall should be monotonically non-decreasing in recall."""
        ids = [f"g{i}" for i in range(50)]
        pos = {f"g{i}" for i in range(5)}
        rm = compute_rank_metrics(ids, pos, set())
        recalls = [r for _, r in rm.list_size_vs_recall]
        for i in range(1, len(recalls)):
            assert recalls[i] >= recalls[i - 1]

    def test_k_values_larger_than_total_uses_fallback(self) -> None:
        """K values not hit in main loop go through fallback path."""
        rm = compute_rank_metrics(["g1", "n1"], {"g1"}, {"n1"}, k_values=[5, 100])
        # effective_k for 5 = min(5, 2) = 2, hits = 1
        assert rm.precision_at_k[5] == 0.5
        assert rm.precision_at_k[100] == 0.5

    def test_empty_positives_empty_results(self) -> None:
        """Both empty => early return."""
        rm = compute_rank_metrics([], set(), set())
        assert rm.total_results == 0
        assert rm.precision_at_k == {}
        assert rm.recall_at_k == {}
        assert rm.pr_curve == []

    def test_negative_ids_unused_for_rank_metrics(self) -> None:
        """Negative IDs don't affect rank metrics (documented behavior)."""
        rm_no_neg = compute_rank_metrics(
            ["g1", "n1", "g2"], {"g1", "g2"}, set(), k_values=[3]
        )
        rm_with_neg = compute_rank_metrics(
            ["g1", "n1", "g2"], {"g1", "g2"}, {"n1"}, k_values=[3]
        )
        assert rm_no_neg.precision_at_k[3] == rm_with_neg.precision_at_k[3]
        assert rm_no_neg.recall_at_k[3] == rm_with_neg.recall_at_k[3]

"""Tests for gene confidence scoring — pure computation, no I/O."""

from veupath_chatbot.services.gene_sets.confidence import (
    GeneConfidenceScore,
    compute_gene_confidence,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ids(scores: list[GeneConfidenceScore]) -> list[str]:
    return [s.gene_id for s in scores]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestComputeGeneConfidence:
    """Verify composite confidence scoring across classification types."""

    def test_tp_gene_gets_high_score(self) -> None:
        result = compute_gene_confidence(
            tp_ids=["G1"],
            fp_ids=[],
            fn_ids=[],
            tn_ids=[],
        )
        assert len(result) == 1
        assert result[0].gene_id == "G1"
        assert result[0].classification_score == 1.0
        assert result[0].composite_score > 0

    def test_fp_gene_gets_negative_score(self) -> None:
        result = compute_gene_confidence(
            tp_ids=[],
            fp_ids=["G2"],
            fn_ids=[],
            tn_ids=[],
        )
        assert len(result) == 1
        assert result[0].gene_id == "G2"
        assert result[0].classification_score == -1.0
        assert result[0].composite_score < 0

    def test_fn_gene_gets_moderate_negative_score(self) -> None:
        result = compute_gene_confidence(
            tp_ids=[],
            fp_ids=[],
            fn_ids=["G3"],
            tn_ids=[],
        )
        assert result[0].classification_score == -0.5
        assert result[0].composite_score < 0

    def test_tn_gene_gets_zero_classification_score(self) -> None:
        result = compute_gene_confidence(
            tp_ids=[],
            fp_ids=[],
            fn_ids=[],
            tn_ids=["G4"],
        )
        assert result[0].classification_score == 0.0
        assert result[0].composite_score == 0.0

    def test_ensemble_frequency_boosts_score(self) -> None:
        without = compute_gene_confidence(
            tp_ids=["G1"],
            fp_ids=[],
            fn_ids=[],
            tn_ids=[],
        )
        with_ensemble = compute_gene_confidence(
            tp_ids=["G1"],
            fp_ids=[],
            fn_ids=[],
            tn_ids=[],
            ensemble_scores={"G1": 0.9},
        )
        assert with_ensemble[0].ensemble_score == 0.9
        assert with_ensemble[0].composite_score > without[0].composite_score

    def test_enrichment_support_boosts_score(self) -> None:
        without = compute_gene_confidence(
            tp_ids=["G1"],
            fp_ids=[],
            fn_ids=[],
            tn_ids=[],
        )
        with_enrich = compute_gene_confidence(
            tp_ids=["G1"],
            fp_ids=[],
            fn_ids=[],
            tn_ids=[],
            enrichment_gene_counts={"G1": 5},
            max_enrichment_terms=10,
        )
        assert with_enrich[0].enrichment_score == 0.5
        assert with_enrich[0].composite_score > without[0].composite_score

    def test_handles_no_ensemble_or_enrichment(self) -> None:
        result = compute_gene_confidence(
            tp_ids=["G1", "G2"],
            fp_ids=["G3"],
            fn_ids=["G4"],
            tn_ids=["G5"],
        )
        assert len(result) == 5
        for score in result:
            assert score.ensemble_score == 0.0
            assert score.enrichment_score == 0.0

    def test_results_sorted_by_composite_desc(self) -> None:
        result = compute_gene_confidence(
            tp_ids=["TP1"],
            fp_ids=["FP1"],
            fn_ids=["FN1"],
            tn_ids=["TN1"],
        )
        scores = [s.composite_score for s in result]
        assert scores == sorted(scores, reverse=True)
        # TP should be first, FP should be last
        assert result[0].gene_id == "TP1"
        assert result[-1].gene_id == "FP1"

    def test_gene_in_multiple_lists_uses_first_match(self) -> None:
        """If a gene ID appears in multiple lists (shouldn't happen, but be safe),
        it appears only once with the first classification found."""
        result = compute_gene_confidence(
            tp_ids=["G1"],
            fp_ids=["G1"],  # duplicate
            fn_ids=[],
            tn_ids=[],
        )
        # G1 should appear once only — classified as TP (first seen)
        assert len(result) == 1
        assert result[0].gene_id == "G1"
        assert result[0].classification_score == 1.0

    def test_enrichment_clamped_at_1(self) -> None:
        """Enrichment score should never exceed 1.0."""
        result = compute_gene_confidence(
            tp_ids=["G1"],
            fp_ids=[],
            fn_ids=[],
            tn_ids=[],
            enrichment_gene_counts={"G1": 20},
            max_enrichment_terms=5,
        )
        assert result[0].enrichment_score == 1.0

    def test_empty_inputs_returns_empty(self) -> None:
        result = compute_gene_confidence(
            tp_ids=[],
            fp_ids=[],
            fn_ids=[],
            tn_ids=[],
        )
        assert result == []

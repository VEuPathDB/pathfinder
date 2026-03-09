"""Tests for ensemble gene scoring."""

import pytest

from veupath_chatbot.services.gene_sets.ensemble import compute_ensemble_scores


def test_single_gene_set() -> None:
    result = compute_ensemble_scores([["G1", "G2", "G3"]])
    assert len(result) == 3
    assert all(r["frequency"] == 1.0 for r in result)


def test_multiple_gene_sets_frequency() -> None:
    result = compute_ensemble_scores([["G1", "G2"], ["G2", "G3"], ["G2", "G4"]])
    by_id = {r["geneId"]: r for r in result}
    assert by_id["G2"]["frequency"] == 1.0  # in all 3
    assert by_id["G1"]["frequency"] == pytest.approx(1 / 3)
    assert by_id["G3"]["frequency"] == pytest.approx(1 / 3)
    assert by_id["G4"]["frequency"] == pytest.approx(1 / 3)


def test_count_and_total_fields() -> None:
    result = compute_ensemble_scores([["G1", "G2"], ["G2", "G3"]])
    by_id = {r["geneId"]: r for r in result}
    assert by_id["G2"]["count"] == 2
    assert by_id["G2"]["total"] == 2
    assert by_id["G1"]["count"] == 1
    assert by_id["G1"]["total"] == 2


def test_sorted_by_frequency_desc() -> None:
    result = compute_ensemble_scores([["G1", "G2"], ["G2", "G3"]])
    assert result[0]["geneId"] == "G2"


def test_positive_controls_flagged() -> None:
    result = compute_ensemble_scores([["G1", "G2"]], positive_controls=["G1"])
    by_id = {r["geneId"]: r for r in result}
    assert by_id["G1"]["inPositives"] is True
    assert by_id["G2"]["inPositives"] is False


def test_empty_gene_sets() -> None:
    result = compute_ensemble_scores([])
    assert result == []


def test_no_positive_controls() -> None:
    result = compute_ensemble_scores([["G1"]])
    assert result[0]["inPositives"] is False


def test_stable_sort_order_for_equal_frequency() -> None:
    """Genes with equal frequency should be sorted alphabetically by gene ID."""
    result = compute_ensemble_scores([["B", "A", "C"]])
    ids = [r["geneId"] for r in result]
    assert ids == ["A", "B", "C"]

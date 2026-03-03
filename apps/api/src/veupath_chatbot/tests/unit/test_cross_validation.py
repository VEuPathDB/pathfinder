"""Tests for cross-validation metric utilities."""

from __future__ import annotations

import math

from veupath_chatbot.services.experiment.cross_validation import (
    _average_metrics,
    _std_metrics,
)
from veupath_chatbot.services.experiment.types import (
    ConfusionMatrix,
    ExperimentMetrics,
)


def _make_metrics(
    sensitivity: float, specificity: float, precision: float
) -> ExperimentMetrics:
    """Build a minimal ExperimentMetrics with specified key values."""
    cm = ConfusionMatrix(
        true_positives=1, false_positives=0, true_negatives=1, false_negatives=0
    )
    return ExperimentMetrics(
        confusion_matrix=cm,
        sensitivity=sensitivity,
        specificity=specificity,
        precision=precision,
        negative_predictive_value=0.5,
        false_positive_rate=1 - specificity,
        false_negative_rate=1 - sensitivity,
        f1_score=0.8,
        mcc=0.6,
        balanced_accuracy=(sensitivity + specificity) / 2,
        youdens_j=sensitivity + specificity - 1,
        total_results=10,
        total_positives=5,
        total_negatives=5,
    )


class TestStdMetrics:
    def test_returns_empty_for_single_fold(self) -> None:
        m = _make_metrics(0.9, 0.8, 0.7)
        assert _std_metrics([m], m) == {}

    def test_returns_correct_keys(self) -> None:
        m1 = _make_metrics(0.9, 0.8, 0.7)
        m2 = _make_metrics(0.7, 0.6, 0.5)
        mean = _average_metrics([m1, m2])
        result = _std_metrics([m1, m2], mean)
        assert set(result.keys()) == {
            "sensitivity",
            "specificity",
            "precision",
            "f1Score",
            "mcc",
            "balancedAccuracy",
        }

    def test_std_values_are_correct(self) -> None:
        m1 = _make_metrics(0.9, 0.8, 0.7)
        m2 = _make_metrics(0.7, 0.6, 0.5)
        mean = _average_metrics([m1, m2])
        result = _std_metrics([m1, m2], mean)
        # Sensitivity std: std([0.9, 0.7]) = sqrt(((0.9-0.8)^2 + (0.7-0.8)^2) / 1) = sqrt(0.02)
        expected_sens_std = math.sqrt(0.02)
        assert abs(result["sensitivity"] - expected_sens_std) < 1e-10

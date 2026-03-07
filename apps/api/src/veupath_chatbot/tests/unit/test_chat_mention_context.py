"""Unit tests for services.chat.mention_context — pure helpers."""

from veupath_chatbot.services.chat.mention_context import _format_metrics, _truncate
from veupath_chatbot.services.experiment.types import ConfusionMatrix, ExperimentMetrics


class TestTruncate:
    def test_short_string_unchanged(self):
        assert _truncate("hello", 10) == "hello"

    def test_exact_length_unchanged(self):
        assert _truncate("12345", 5) == "12345"

    def test_long_string_truncated_with_ellipsis(self):
        result = _truncate("a" * 100, 10)
        assert result == "aaaaaaa..."
        assert len(result) == 10

    def test_empty_string(self):
        assert _truncate("", 5) == ""

    def test_max_len_3_edge(self):
        # max_len < 4: too small for ellipsis, just hard-truncate
        result = _truncate("abcdef", 3)
        assert result == "abc"
        assert len(result) == 3

    def test_max_len_0(self):
        result = _truncate("abcdef", 0)
        assert result == ""
        assert len(result) == 0

    def test_max_len_1(self):
        result = _truncate("abcdef", 1)
        assert result == "a"
        assert len(result) == 1

    def test_max_len_2(self):
        result = _truncate("abcdef", 2)
        assert result == "ab"
        assert len(result) == 2

    def test_max_len_4(self):
        result = _truncate("abcdef", 4)
        assert result == "a..."
        assert len(result) == 4

    def test_one_char_over(self):
        result = _truncate("abcdef", 5)
        assert result == "ab..."
        assert len(result) == 5


class TestFormatMetrics:
    def test_output_is_markdown_table(self):
        cm = ConfusionMatrix(
            true_positives=10,
            false_positives=2,
            true_negatives=85,
            false_negatives=3,
        )
        metrics = ExperimentMetrics(
            confusion_matrix=cm,
            sensitivity=0.7692,
            specificity=0.9770,
            precision=0.8333,
            f1_score=0.8000,
            mcc=0.7500,
            balanced_accuracy=0.8731,
            total_results=100,
        )

        result = _format_metrics(metrics)

        assert "| Metric | Value |" in result
        assert "| Sensitivity | 0.7692 |" in result
        assert "| Specificity | 0.9770 |" in result
        assert "| Precision | 0.8333 |" in result
        assert "| F1 Score | 0.8000 |" in result
        assert "| MCC | 0.7500 |" in result
        assert "| Balanced Accuracy | 0.8731 |" in result
        assert "| Total Results | 100 |" in result
        assert "TP=10" in result
        assert "FP=2" in result
        assert "FN=3" in result
        assert "TN=85" in result

    def test_zero_metrics(self):
        cm = ConfusionMatrix(
            true_positives=0,
            false_positives=0,
            true_negatives=0,
            false_negatives=0,
        )
        metrics = ExperimentMetrics(
            confusion_matrix=cm,
            sensitivity=0.0,
            specificity=0.0,
            precision=0.0,
            f1_score=0.0,
            mcc=0.0,
            balanced_accuracy=0.0,
        )

        result = _format_metrics(metrics)
        assert "| Sensitivity | 0.0000 |" in result
        assert "TP=0" in result
        assert "| Total Results | 0 |" in result

    def test_result_is_string(self):
        cm = ConfusionMatrix(
            true_positives=5,
            false_positives=1,
            true_negatives=90,
            false_negatives=4,
        )
        metrics = ExperimentMetrics(
            confusion_matrix=cm,
            sensitivity=0.5556,
            specificity=0.9890,
            precision=0.8333,
            f1_score=0.6667,
            mcc=0.6500,
            balanced_accuracy=0.7723,
        )

        result = _format_metrics(metrics)
        assert isinstance(result, str)
        # Table should have multiple lines
        lines = result.strip().split("\n")
        assert len(lines) >= 8  # header + separator + 7 data rows

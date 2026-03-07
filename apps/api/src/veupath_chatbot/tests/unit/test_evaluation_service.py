"""Tests for the evaluation service (services/experiment/evaluation.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from veupath_chatbot.platform.errors import ValidationError
from veupath_chatbot.services.experiment.evaluation import (
    _extract_control_counts,
    compute_step_contributions,
    compute_sweep_values,
    format_metrics_dict,
    generate_sweep_events,
    re_evaluate,
    run_sweep_point,
    validate_sweep_parameter,
)
from veupath_chatbot.services.experiment.types import (
    ConfusionMatrix,
    Experiment,
    ExperimentConfig,
    ExperimentMetrics,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(**overrides: object) -> ExperimentConfig:
    defaults = {
        "site_id": "PlasmoDB",
        "record_type": "transcript",
        "search_name": "GenesByTaxon",
        "parameters": {"organism": "Plasmodium falciparum 3D7", "threshold": "0.5"},
        "positive_controls": ["PF3D7_0100100", "PF3D7_0100200"],
        "negative_controls": ["PF3D7_9999999"],
        "controls_search_name": "GeneByLocusTag",
        "controls_param_name": "ds_gene_ids",
        "controls_value_format": "newline",
    }
    defaults.update(overrides)
    return ExperimentConfig(**defaults)  # type: ignore[arg-type]


def _make_experiment(**overrides: object) -> Experiment:
    config_overrides = overrides.pop("config_overrides", {})
    defaults: dict[str, object] = {
        "id": "exp-001",
        "config": _make_config(**config_overrides),  # type: ignore[arg-type]
        "user_id": "user-1",
        "status": "completed",
    }
    defaults.update(overrides)
    return Experiment(**defaults)  # type: ignore[arg-type]


def _make_metrics(
    sens: float = 0.8,
    spec: float = 0.9,
    prec: float = 0.75,
    f1: float = 0.77,
    mcc: float = 0.7,
    ba: float = 0.85,
    fpr: float = 0.1,
    total: int = 100,
) -> ExperimentMetrics:
    return ExperimentMetrics(
        confusion_matrix=ConfusionMatrix(
            true_positives=8,
            false_positives=1,
            true_negatives=9,
            false_negatives=2,
        ),
        sensitivity=sens,
        specificity=spec,
        precision=prec,
        f1_score=f1,
        mcc=mcc,
        balanced_accuracy=ba,
        false_positive_rate=fpr,
        total_results=total,
    )


# ---------------------------------------------------------------------------
# compute_sweep_values
# ---------------------------------------------------------------------------


class TestComputeSweepValues:
    def test_numeric_basic(self) -> None:
        vals = compute_sweep_values(
            sweep_type="numeric",
            values=None,
            min_value=0.0,
            max_value=1.0,
            steps=3,
        )
        assert len(vals) == 3
        assert float(vals[0]) == pytest.approx(0.0)
        assert float(vals[1]) == pytest.approx(0.5)
        assert float(vals[2]) == pytest.approx(1.0)

    def test_numeric_single_step(self) -> None:
        vals = compute_sweep_values(
            sweep_type="numeric",
            values=None,
            min_value=5.0,
            max_value=10.0,
            steps=1,
        )
        assert len(vals) == 1
        assert float(vals[0]) == pytest.approx(5.0)

    def test_numeric_missing_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            compute_sweep_values(
                sweep_type="numeric",
                values=None,
                min_value=None,
                max_value=1.0,
                steps=5,
            )
        with pytest.raises(ValidationError):
            compute_sweep_values(
                sweep_type="numeric",
                values=None,
                min_value=0.0,
                max_value=None,
                steps=5,
            )

    def test_categorical_basic(self) -> None:
        vals = compute_sweep_values(
            sweep_type="categorical",
            values=["a", "b", "c"],
            min_value=None,
            max_value=None,
            steps=10,
        )
        assert vals == ["a", "b", "c"]

    def test_categorical_empty_raises(self) -> None:
        with pytest.raises(ValidationError):
            compute_sweep_values(
                sweep_type="categorical",
                values=[],
                min_value=None,
                max_value=None,
                steps=10,
            )
        with pytest.raises(ValidationError):
            compute_sweep_values(
                sweep_type="categorical",
                values=None,
                min_value=None,
                max_value=None,
                steps=10,
            )


# ---------------------------------------------------------------------------
# validate_sweep_parameter
# ---------------------------------------------------------------------------


class TestValidateSweepParameter:
    def test_valid_param(self) -> None:
        exp = _make_experiment()
        # Should not raise
        validate_sweep_parameter(exp, "threshold")

    def test_missing_param_raises(self) -> None:
        exp = _make_experiment()
        with pytest.raises(ValidationError):
            validate_sweep_parameter(exp, "not_a_param")


# ---------------------------------------------------------------------------
# format_metrics_dict
# ---------------------------------------------------------------------------


class TestFormatMetricsDict:
    def test_keys_present(self) -> None:
        m = _make_metrics()
        result = format_metrics_dict(m)
        expected_keys = {
            "sensitivity",
            "specificity",
            "precision",
            "f1Score",
            "mcc",
            "balancedAccuracy",
            "totalResults",
            "falsePositiveRate",
        }
        assert set(result.keys()) == expected_keys

    def test_values_rounded(self) -> None:
        m = _make_metrics(sens=0.12345678)
        result = format_metrics_dict(m)
        assert result["sensitivity"] == 0.1235

    def test_total_results_is_int(self) -> None:
        m = _make_metrics(total=42)
        result = format_metrics_dict(m)
        assert result["totalResults"] == 42
        assert isinstance(result["totalResults"], int)


# ---------------------------------------------------------------------------
# _extract_control_counts
# ---------------------------------------------------------------------------


class TestExtractControlCounts:
    def test_full_result(self) -> None:
        result = {
            "target": {"resultCount": 100},
            "positive": {"intersectionCount": 8},
            "negative": {"intersectionCount": 3},
        }
        total, pos, neg = _extract_control_counts(result)
        assert total == 100
        assert pos == 8
        assert neg == 3

    def test_missing_sections(self) -> None:
        total, pos, neg = _extract_control_counts({})
        assert total == 0
        assert pos == 0
        assert neg == 0

    def test_none_sections(self) -> None:
        result = {"target": None, "positive": None, "negative": None}
        total, pos, neg = _extract_control_counts(result)
        assert total == 0
        assert pos == 0
        assert neg == 0

    def test_non_dict_sections(self) -> None:
        result = {"target": "bad", "positive": 42, "negative": []}
        total, pos, neg = _extract_control_counts(result)
        assert total == 0
        assert pos == 0
        assert neg == 0

    def test_float_counts(self) -> None:
        result = {
            "target": {"resultCount": 100.0},
            "positive": {"intersectionCount": 8.0},
            "negative": {"intersectionCount": 3.0},
        }
        total, pos, neg = _extract_control_counts(result)
        assert total == 100
        assert pos == 8
        assert neg == 3


# ---------------------------------------------------------------------------
# run_sweep_point
# ---------------------------------------------------------------------------


class TestRunSweepPoint:
    @pytest.mark.asyncio
    async def test_successful_numeric_point(self) -> None:
        exp = _make_experiment()
        mock_result = {
            "positive": {"intersectionCount": 2, "controlsCount": 2},
            "negative": {"intersectionCount": 0, "controlsCount": 1},
            "target": {"resultCount": 50},
        }
        with patch(
            "veupath_chatbot.services.experiment.evaluation.run_positive_negative_controls",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            point = await run_sweep_point(
                exp=exp,
                param_name="threshold",
                value="0.75",
                is_categorical=False,
            )

        assert point["value"] == pytest.approx(0.75)
        assert point["metrics"] is not None
        assert "error" not in point

    @pytest.mark.asyncio
    async def test_successful_categorical_point(self) -> None:
        exp = _make_experiment()
        mock_result = {
            "positive": {"intersectionCount": 1, "controlsCount": 2},
            "negative": {"intersectionCount": 1, "controlsCount": 1},
            "target": {"resultCount": 30},
        }
        with patch(
            "veupath_chatbot.services.experiment.evaluation.run_positive_negative_controls",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            point = await run_sweep_point(
                exp=exp,
                param_name="organism",
                value="some_org",
                is_categorical=True,
            )

        assert point["value"] == "some_org"
        assert point["metrics"] is not None

    @pytest.mark.asyncio
    async def test_failure_returns_error(self) -> None:
        exp = _make_experiment()
        with patch(
            "veupath_chatbot.services.experiment.evaluation.run_positive_negative_controls",
            new_callable=AsyncMock,
            side_effect=RuntimeError("WDK down"),
        ):
            point = await run_sweep_point(
                exp=exp,
                param_name="threshold",
                value="0.5",
                is_categorical=False,
            )

        assert point["metrics"] is None
        assert "WDK down" in point["error"]


# ---------------------------------------------------------------------------
# re_evaluate
# ---------------------------------------------------------------------------


class TestReEvaluate:
    @pytest.mark.asyncio
    async def test_single_mode(self) -> None:
        exp = _make_experiment()
        mock_result = {
            "positive": {"intersectionCount": 2, "controlsCount": 2},
            "negative": {"intersectionCount": 0, "controlsCount": 1},
            "target": {"resultCount": 50},
        }
        mock_genes = ([], [], [], [])

        with (
            patch(
                "veupath_chatbot.services.experiment.evaluation.run_positive_negative_controls",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch(
                "veupath_chatbot.services.experiment.evaluation.extract_and_enrich_genes",
                new_callable=AsyncMock,
                return_value=mock_genes,
            ),
            patch(
                "veupath_chatbot.services.experiment.evaluation.get_experiment_store",
            ) as mock_store_fn,
        ):
            mock_store = MagicMock()
            mock_store_fn.return_value = mock_store
            result = await re_evaluate(exp)

        assert isinstance(result, dict)
        mock_store.save.assert_called_once_with(exp)
        assert exp.metrics is not None

    @pytest.mark.asyncio
    async def test_tree_mode(self) -> None:
        exp = _make_experiment(
            config_overrides={
                "mode": "multi-step",
                "step_tree": {"searchName": "X", "primaryInput": {"searchName": "Y"}},
            }
        )
        mock_result = {
            "positive": {"intersectionCount": 1, "controlsCount": 2},
            "negative": {"intersectionCount": 0, "controlsCount": 1},
            "target": {"resultCount": 20},
        }
        mock_genes = ([], [], [], [])

        with (
            patch(
                "veupath_chatbot.services.experiment.step_analysis.run_controls_against_tree",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_tree_fn,
            patch(
                "veupath_chatbot.services.experiment.evaluation.extract_and_enrich_genes",
                new_callable=AsyncMock,
                return_value=mock_genes,
            ),
            patch(
                "veupath_chatbot.services.experiment.evaluation.get_experiment_store",
            ) as mock_store_fn,
        ):
            mock_store = MagicMock()
            mock_store_fn.return_value = mock_store
            result = await re_evaluate(exp)

        mock_tree_fn.assert_called_once()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# compute_step_contributions
# ---------------------------------------------------------------------------


class TestComputeStepContributions:
    @pytest.mark.asyncio
    async def test_basic_tree(self) -> None:
        exp = _make_experiment()
        tree = {
            "searchName": "root",
            "operator": "INTERSECT",
            "primaryInput": {
                "searchName": "LeafA",
                "displayName": "Leaf A",
                "parameters": {"p": "1"},
            },
            "secondaryInput": {
                "searchName": "LeafB",
                "displayName": "Leaf B",
                "parameters": {"p": "2"},
            },
        }
        mock_result = {
            "positive": {"intersectionCount": 2, "controlsCount": 2},
            "negative": {"intersectionCount": 0, "controlsCount": 1},
            "target": {"resultCount": 10},
        }

        with patch(
            "veupath_chatbot.services.experiment.evaluation.run_positive_negative_controls",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            contribs = await compute_step_contributions(exp, tree)

        assert len(contribs) == 2
        assert contribs[0]["stepSearchName"] == "LeafA"
        assert contribs[1]["stepSearchName"] == "LeafB"
        assert contribs[0]["totalResults"] == 10
        assert contribs[0]["positiveControlHits"] == 2

    @pytest.mark.asyncio
    async def test_skips_invalid_leaves(self) -> None:
        exp = _make_experiment()
        tree = {
            "searchName": "",  # invalid
            "parameters": {},
        }

        contribs = await compute_step_contributions(exp, tree)
        assert len(contribs) == 0

    @pytest.mark.asyncio
    async def test_handles_failure(self) -> None:
        exp = _make_experiment()
        tree = {"searchName": "Failing", "parameters": {"x": "1"}}

        with patch(
            "veupath_chatbot.services.experiment.evaluation.run_positive_negative_controls",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            contribs = await compute_step_contributions(exp, tree)

        assert len(contribs) == 1
        assert contribs[0]["totalResults"] == 0
        assert contribs[0]["stepName"] == "Failing"


# ---------------------------------------------------------------------------
# generate_sweep_events
# ---------------------------------------------------------------------------


class TestGenerateSweepEvents:
    @pytest.mark.asyncio
    async def test_emits_point_and_complete_events(self) -> None:
        exp = _make_experiment()
        mock_result = {
            "positive": {"intersectionCount": 2, "controlsCount": 2},
            "negative": {"intersectionCount": 0, "controlsCount": 1},
            "target": {"resultCount": 50},
        }

        with (
            patch(
                "veupath_chatbot.services.experiment.evaluation.cleanup_before_sweep",
                new_callable=AsyncMock,
            ),
            patch(
                "veupath_chatbot.services.experiment.evaluation.run_positive_negative_controls",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            events: list[str] = []
            async for event in generate_sweep_events(
                exp=exp,
                param_name="threshold",
                sweep_type="numeric",
                sweep_values=["0.0", "0.5", "1.0"],
            ):
                events.append(event)

        # 3 sweep_point events + 1 sweep_complete
        point_events = [e for e in events if "sweep_point" in e]
        complete_events = [e for e in events if "sweep_complete" in e]
        assert len(point_events) == 3
        assert len(complete_events) == 1

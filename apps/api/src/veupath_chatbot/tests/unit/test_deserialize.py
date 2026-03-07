"""Tests for experiment JSON deserialization."""

from __future__ import annotations

import pytest

from veupath_chatbot.services.experiment._deserialize import experiment_from_json
from veupath_chatbot.services.experiment.types import (
    EnrichmentResult,
    EnrichmentTerm,
    Experiment,
    ExperimentConfig,
    GeneInfo,
    experiment_to_json,
)


def _minimal_json() -> dict:
    """Minimal valid experiment JSON."""
    return {
        "id": "exp-001",
        "config": {
            "siteId": "plasmo",
            "recordType": "gene",
            "searchName": "GenesByText",
            "parameters": {"text": "kinase"},
            "positiveControls": ["g1", "g2"],
            "negativeControls": ["n1"],
            "controlsSearchName": "GeneByLocusTag",
            "controlsParamName": "single_gene_id",
        },
        "status": "completed",
        "createdAt": "2025-01-01T00:00:00",
    }


class TestExperimentFromJson:
    def test_minimal_deserialization(self) -> None:
        exp = experiment_from_json(_minimal_json())
        assert exp.id == "exp-001"
        assert exp.config.site_id == "plasmo"
        assert exp.config.record_type == "gene"
        assert exp.config.search_name == "GenesByText"
        assert exp.config.positive_controls == ["g1", "g2"]
        assert exp.config.negative_controls == ["n1"]
        assert exp.status == "completed"

    def test_defaults_applied(self) -> None:
        exp = experiment_from_json(_minimal_json())
        assert exp.config.mode == "single"
        assert exp.config.controls_value_format == "newline"
        assert exp.config.enable_cross_validation is False
        assert exp.config.k_folds == 5
        assert exp.config.enrichment_types == []
        assert exp.is_primary_benchmark is False

    def test_gene_lists(self) -> None:
        d = _minimal_json()
        d["truePositiveGenes"] = [
            {"id": "g1", "name": "Gene1", "organism": "Pf", "product": "kinase"},
        ]
        d["falseNegativeGenes"] = [{"id": "g2"}]
        d["falsePositiveGenes"] = [{"id": "n1"}]
        d["trueNegativeGenes"] = [{"id": "n2"}]
        exp = experiment_from_json(d)

        assert len(exp.true_positive_genes) == 1
        assert exp.true_positive_genes[0].id == "g1"
        assert exp.true_positive_genes[0].name == "Gene1"
        assert len(exp.false_negative_genes) == 1
        assert len(exp.false_positive_genes) == 1
        assert len(exp.true_negative_genes) == 1

    def test_enrichment_deduplication(self) -> None:
        """Duplicate analysis_type entries should be deduplicated (keep last)."""
        d = _minimal_json()
        d["enrichmentResults"] = [
            {
                "analysisType": "go_process",
                "terms": [],
                "totalGenesAnalyzed": 50,
                "backgroundSize": 1000,
            },
            {
                "analysisType": "pathway",
                "terms": [],
                "totalGenesAnalyzed": 60,
                "backgroundSize": 2000,
            },
            {
                "analysisType": "go_process",
                "terms": [],
                "totalGenesAnalyzed": 80,
                "backgroundSize": 3000,
            },
        ]
        exp = experiment_from_json(d)
        # Should keep the last go_process (80) and pathway (60)
        assert len(exp.enrichment_results) == 2
        types = [er.analysis_type for er in exp.enrichment_results]
        assert "go_process" in types
        assert "pathway" in types
        go = next(
            er for er in exp.enrichment_results if er.analysis_type == "go_process"
        )
        assert go.total_genes_analyzed == 80

    def test_metrics_deserialization(self) -> None:
        d = _minimal_json()
        d["metrics"] = {
            "confusionMatrix": {
                "truePositives": 8,
                "falsePositives": 2,
                "trueNegatives": 18,
                "falseNegatives": 2,
            },
            "sensitivity": 0.8,
            "specificity": 0.9,
            "precision": 0.8,
            "f1Score": 0.8,
            "mcc": 0.7,
            "balancedAccuracy": 0.85,
        }
        exp = experiment_from_json(d)
        assert exp.metrics is not None
        assert exp.metrics.sensitivity == 0.8
        assert exp.metrics.confusion_matrix.true_positives == 8

    def test_rank_metrics_deserialization(self) -> None:
        d = _minimal_json()
        d["rankMetrics"] = {
            "precisionAtK": {"10": 0.5, "50": 0.3},
            "recallAtK": {"10": 0.2, "50": 0.6},
            "enrichmentAtK": {"10": 2.0, "50": 1.5},
            "prCurve": [[0.5, 0.2], [0.3, 0.6]],
            "listSizeVsRecall": [[10, 0.2], [50, 0.6]],
            "totalResults": 100,
        }
        exp = experiment_from_json(d)
        assert exp.rank_metrics is not None
        assert exp.rank_metrics.total_results == 100

    def test_optional_fields(self) -> None:
        d = _minimal_json()
        d["error"] = "Something went wrong"
        d["totalTimeSeconds"] = 12.34
        d["batchId"] = "batch-001"
        d["benchmarkId"] = "bench-001"
        d["controlSetLabel"] = "Apicoplast genes"
        d["isPrimaryBenchmark"] = True
        d["wdkStrategyId"] = 42
        d["wdkStepId"] = 99
        d["notes"] = "Test notes"
        exp = experiment_from_json(d)

        assert exp.error == "Something went wrong"
        assert exp.total_time_seconds == 12.34
        assert exp.batch_id == "batch-001"
        assert exp.benchmark_id == "bench-001"
        assert exp.control_set_label == "Apicoplast genes"
        assert exp.is_primary_benchmark is True
        assert exp.wdk_strategy_id == 42
        assert exp.wdk_step_id == 99
        assert exp.notes == "Test notes"

    def test_robustness_deserialization(self) -> None:
        d = _minimal_json()
        d["robustness"] = {
            "nIterations": 100,
            "metricCis": {
                "sensitivity": {
                    "lower": 0.7,
                    "mean": 0.8,
                    "upper": 0.9,
                    "std": 0.05,
                },
            },
            "rankMetricCis": {},
            "topKStability": 0.85,
            "negativeSetSensitivity": [],
        }
        exp = experiment_from_json(d)
        assert exp.robustness is not None
        assert exp.robustness.n_iterations == 100
        assert exp.robustness.top_k_stability == 0.85
        assert "sensitivity" in exp.robustness.metric_cis

    def test_step_analysis_deserialization(self) -> None:
        d = _minimal_json()
        d["stepAnalysis"] = {
            "stepEvaluations": [],
            "operatorComparisons": [],
            "stepContributions": [],
            "parameterSensitivities": [],
        }
        exp = experiment_from_json(d)
        assert exp.step_analysis is not None

    def test_optimization_specs_deserialization(self) -> None:
        d = _minimal_json()
        d["config"]["optimizationSpecs"] = [
            {"name": "score", "type": "numeric", "min": 0.0, "max": 1.0, "step": 0.1},
        ]
        exp = experiment_from_json(d)
        assert exp.config.optimization_specs is not None
        assert len(exp.config.optimization_specs) == 1
        assert exp.config.optimization_specs[0].name == "score"

    def test_multi_step_config(self) -> None:
        d = _minimal_json()
        d["config"]["mode"] = "multi-step"
        d["config"]["stepTree"] = {
            "id": "root",
            "searchName": "GenesByText",
            "parameters": {"text": "kinase"},
        }
        exp = experiment_from_json(d)
        assert exp.config.mode == "multi-step"
        assert isinstance(exp.config.step_tree, dict)

    def test_import_mode_config(self) -> None:
        d = _minimal_json()
        d["config"]["mode"] = "import"
        d["config"]["sourceStrategyId"] = "12345"
        exp = experiment_from_json(d)
        assert exp.config.mode == "import"
        assert exp.config.source_strategy_id == "12345"

    def test_null_threshold_knobs(self) -> None:
        """thresholdKnobs/operatorKnobs can be null (not just missing)."""
        d = _minimal_json()
        d["config"]["thresholdKnobs"] = None
        d["config"]["operatorKnobs"] = None
        exp = experiment_from_json(d)
        assert exp.config.threshold_knobs is None
        assert exp.config.operator_knobs is None

    def test_empty_threshold_knobs(self) -> None:
        """Empty arrays should become None."""
        d = _minimal_json()
        d["config"]["thresholdKnobs"] = []
        d["config"]["operatorKnobs"] = []
        exp = experiment_from_json(d)
        assert exp.config.threshold_knobs is None
        assert exp.config.operator_knobs is None

    def test_missing_config_key_raises(self) -> None:
        """Missing 'config' key should raise KeyError."""
        d = {"id": "exp-001", "status": "completed"}
        with pytest.raises(KeyError):
            experiment_from_json(d)

    def test_extra_fields_ignored(self) -> None:
        """Extra/unknown fields in the JSON should be silently ignored."""
        d = _minimal_json()
        d["futureField"] = "should not crash"
        d["config"]["futureConfigField"] = "also fine"
        exp = experiment_from_json(d)
        assert exp.id == "exp-001"


class TestRoundtrip:
    def test_serialize_deserialize_roundtrip(self) -> None:
        """An experiment should survive to_json -> from_json."""
        cfg = ExperimentConfig(
            site_id="plasmo",
            record_type="gene",
            search_name="GenesByText",
            parameters={"text": "kinase"},
            positive_controls=["g1", "g2"],
            negative_controls=["n1"],
            controls_search_name="GeneByLocusTag",
            controls_param_name="single_gene_id",
            name="Roundtrip test",
        )
        exp = Experiment(id="rt-001", config=cfg, status="completed")
        exp.true_positive_genes = [GeneInfo(id="g1", name="Gene1")]
        exp.false_negative_genes = [GeneInfo(id="g2")]
        exp.enrichment_results = [
            EnrichmentResult(
                analysis_type="go_process",
                terms=[
                    EnrichmentTerm(
                        term_id="GO:001",
                        term_name="Transport",
                        gene_count=5,
                        background_count=100,
                        fold_enrichment=2.5,
                        odds_ratio=1.5,
                        p_value=0.001,
                        fdr=0.01,
                        bonferroni=0.05,
                    )
                ],
                total_genes_analyzed=50,
                background_size=1000,
            )
        ]

        serialized = experiment_to_json(exp)
        restored = experiment_from_json(serialized)

        assert restored.id == exp.id
        assert restored.config.site_id == exp.config.site_id
        assert restored.config.name == exp.config.name
        assert len(restored.true_positive_genes) == 1
        assert restored.true_positive_genes[0].id == "g1"
        assert restored.true_positive_genes[0].name == "Gene1"
        assert len(restored.enrichment_results) == 1
        assert restored.enrichment_results[0].analysis_type == "go_process"
        assert restored.enrichment_results[0].terms[0].term_id == "GO:001"

"""Tests for gene set overlap analysis."""

from veupath_chatbot.services.experiment.overlap import compute_gene_set_overlap
from veupath_chatbot.services.experiment.types import (
    Experiment,
    ExperimentConfig,
    GeneInfo,
)


def _cfg(site_id: str = "plasmo") -> ExperimentConfig:
    return ExperimentConfig(
        site_id=site_id,
        record_type="gene",
        search_name="GenesByText",
        parameters={},
        positive_controls=[],
        negative_controls=[],
        controls_search_name="",
        controls_param_name="",
        name="Test",
    )


def _exp(
    exp_id: str,
    tp: list[str],
    fp: list[str],
    name: str = "Test",
) -> Experiment:
    e = Experiment(id=exp_id, config=_cfg())
    e.config.name = name
    e.true_positive_genes = [GeneInfo(id=g) for g in tp]
    e.false_positive_genes = [GeneInfo(id=g) for g in fp]
    return e


class TestComputeGeneSetOverlap:
    def test_two_identical_experiments(self) -> None:
        e1 = _exp("e1", tp=["g1", "g2"], fp=["g3"])
        e2 = _exp("e2", tp=["g1", "g2"], fp=["g3"])
        result = compute_gene_set_overlap([e1, e2], ["e1", "e2"])

        assert len(result["pairwise"]) == 1
        pair = result["pairwise"][0]
        assert pair["jaccard"] == 1.0
        assert pair["intersection"] == 3
        assert pair["uniqueA"] == []
        assert pair["uniqueB"] == []

    def test_two_disjoint_experiments(self) -> None:
        e1 = _exp("e1", tp=["g1", "g2"], fp=[])
        e2 = _exp("e2", tp=["g3", "g4"], fp=[])
        result = compute_gene_set_overlap([e1, e2], ["e1", "e2"])

        pair = result["pairwise"][0]
        assert pair["jaccard"] == 0.0
        assert pair["intersection"] == 0
        assert pair["union"] == 4

    def test_partial_overlap(self) -> None:
        e1 = _exp("e1", tp=["g1", "g2"], fp=["g3"])
        e2 = _exp("e2", tp=["g2", "g3"], fp=["g4"])
        result = compute_gene_set_overlap([e1, e2], ["e1", "e2"])

        pair = result["pairwise"][0]
        # Shared: g2, g3 -> 2
        # Union: g1, g2, g3, g4 -> 4
        assert pair["intersection"] == 2
        assert pair["union"] == 4
        assert pair["jaccard"] == 0.5
        assert sorted(pair["sharedGenes"]) == ["g2", "g3"]

    def test_three_experiments_pairwise(self) -> None:
        e1 = _exp("e1", tp=["g1"], fp=[])
        e2 = _exp("e2", tp=["g2"], fp=[])
        e3 = _exp("e3", tp=["g3"], fp=[])
        result = compute_gene_set_overlap([e1, e2, e3], ["e1", "e2", "e3"])

        # 3 choose 2 = 3 pairwise comparisons
        assert len(result["pairwise"]) == 3

    def test_universal_genes(self) -> None:
        e1 = _exp("e1", tp=["g1", "g2"], fp=[])
        e2 = _exp("e2", tp=["g1", "g3"], fp=[])
        e3 = _exp("e3", tp=["g1", "g4"], fp=[])
        result = compute_gene_set_overlap([e1, e2, e3], ["e1", "e2", "e3"])

        # g1 is in all three
        assert result["universalGenes"] == ["g1"]

    def test_per_experiment_summary(self) -> None:
        e1 = _exp("e1", tp=["g1", "g2"], fp=["g3"])
        e2 = _exp("e2", tp=["g2"], fp=["g4"])
        result = compute_gene_set_overlap([e1, e2], ["e1", "e2"])

        per_exp = {p["experimentId"]: p for p in result["perExperiment"]}
        assert per_exp["e1"]["totalGenes"] == 3
        # g2 is shared, g1 and g3 are unique
        assert per_exp["e1"]["sharedGenes"] == 1
        assert per_exp["e1"]["uniqueGenes"] == 2

    def test_gene_membership(self) -> None:
        e1 = _exp("e1", tp=["g1", "g2"], fp=[])
        e2 = _exp("e2", tp=["g1"], fp=[])
        result = compute_gene_set_overlap([e1, e2], ["e1", "e2"])

        membership = {m["geneId"]: m for m in result["geneMembership"]}
        assert membership["g1"]["foundIn"] == 2
        assert membership["g2"]["foundIn"] == 1

    def test_total_unique_genes(self) -> None:
        e1 = _exp("e1", tp=["g1", "g2"], fp=[])
        e2 = _exp("e2", tp=["g2", "g3"], fp=[])
        result = compute_gene_set_overlap([e1, e2], ["e1", "e2"])

        assert result["totalUniqueGenes"] == 3

    def test_empty_experiments(self) -> None:
        e1 = _exp("e1", tp=[], fp=[])
        e2 = _exp("e2", tp=[], fp=[])
        result = compute_gene_set_overlap([e1, e2], ["e1", "e2"])

        pair = result["pairwise"][0]
        assert pair["jaccard"] == 0.0
        assert pair["intersection"] == 0
        assert pair["union"] == 0

    def test_labels_from_config_name(self) -> None:
        e1 = _exp("e1", tp=["g1"], fp=[], name="Alpha")
        e2 = _exp("e2", tp=["g2"], fp=[], name="Beta")
        result = compute_gene_set_overlap([e1, e2], ["e1", "e2"])

        assert result["experimentLabels"]["e1"] == "Alpha"
        assert result["experimentLabels"]["e2"] == "Beta"
        assert result["pairwise"][0]["labelA"] == "Alpha"
        assert result["pairwise"][0]["labelB"] == "Beta"

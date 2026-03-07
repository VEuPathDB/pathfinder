"""Tests for ExperimentConfig.is_tree_mode property."""

from veupath_chatbot.services.experiment.types import ExperimentConfig


def _base_config(**overrides: object) -> ExperimentConfig:
    """Create a minimal ExperimentConfig with sensible defaults."""
    defaults: dict[str, object] = {
        "site_id": "PlasmoDB",
        "record_type": "gene",
        "search_name": "GenesByTaxon",
        "parameters": {},
        "positive_controls": [],
        "negative_controls": [],
        "controls_search_name": "GeneByLocusTag",
        "controls_param_name": "single_gene_id",
    }
    defaults.update(overrides)
    return ExperimentConfig(**defaults)  # type: ignore[arg-type]


class TestIsTreeMode:
    def test_single_mode_returns_false(self) -> None:
        config = _base_config(mode="single")
        assert config.is_tree_mode is False

    def test_multi_step_without_tree_returns_false(self) -> None:
        config = _base_config(mode="multi-step", step_tree=None)
        assert config.is_tree_mode is False

    def test_multi_step_with_non_dict_tree_returns_false(self) -> None:
        config = _base_config(mode="multi-step", step_tree="not_a_dict")
        assert config.is_tree_mode is False

    def test_multi_step_with_dict_tree_returns_true(self) -> None:
        config = _base_config(mode="multi-step", step_tree={"root": {}})
        assert config.is_tree_mode is True

    def test_import_with_dict_tree_returns_true(self) -> None:
        config = _base_config(mode="import", step_tree={"root": {}})
        assert config.is_tree_mode is True

    def test_import_without_tree_returns_false(self) -> None:
        config = _base_config(mode="import", step_tree=None)
        assert config.is_tree_mode is False

"""Tests for batch experiment controls override logic.

Verifies that:
- None controls → falls back to base controls (default behavior)
- Explicit empty list → uses empty list (user explicitly cleared controls)
- Explicit list → uses the provided list
"""

from __future__ import annotations

from veupath_chatbot.services.experiment.types import (
    BatchExperimentConfig,
    BatchOrganismTarget,
    ExperimentConfig,
)


def _base_config(
    positive: list[str] | None = None, negative: list[str] | None = None
) -> ExperimentConfig:
    return ExperimentConfig(
        site_id="plasmodb",
        record_type="gene",
        search_name="GenesByTaxon",
        parameters={"organism": "P. falciparum"},
        positive_controls=positive or ["PF3D7_1133400"],
        negative_controls=negative or ["PF3D7_0000001"],
        controls_search_name="GeneByLocusTag",
        controls_param_name="single_gene_id",
    )


def _resolve_controls(
    target: BatchOrganismTarget, base: ExperimentConfig
) -> tuple[list[str], list[str]]:
    """Replicate the resolution logic from streaming.py."""
    pos = (
        target.positive_controls
        if target.positive_controls is not None
        else list(base.positive_controls)
    )
    neg = (
        target.negative_controls
        if target.negative_controls is not None
        else list(base.negative_controls)
    )
    return pos, neg


class TestBatchControlsOverride:
    """Verify BatchOrganismTarget controls resolution."""

    def test_none_falls_back_to_base(self) -> None:
        """When controls are None (not specified), use base controls."""
        base = _base_config()
        target = BatchOrganismTarget(organism="P. vivax")
        assert target.positive_controls is None
        assert target.negative_controls is None
        pos, neg = _resolve_controls(target, base)
        assert pos == base.positive_controls
        assert neg == base.negative_controls

    def test_explicit_empty_list_overrides_base(self) -> None:
        """When user explicitly sets controls to [], do NOT fall back to base."""
        base = _base_config()
        target = BatchOrganismTarget(
            organism="P. vivax",
            positive_controls=[],
            negative_controls=[],
        )
        pos, neg = _resolve_controls(target, base)
        assert pos == []
        assert neg == []

    def test_explicit_list_overrides_base(self) -> None:
        """When user provides specific controls, use those."""
        base = _base_config()
        target = BatchOrganismTarget(
            organism="P. vivax",
            positive_controls=["PVX_GENE1"],
            negative_controls=["PVX_GENE2"],
        )
        pos, neg = _resolve_controls(target, base)
        assert pos == ["PVX_GENE1"]
        assert neg == ["PVX_GENE2"]

    def test_mixed_override(self) -> None:
        """One field overridden (even to empty), other falls back to base."""
        base = _base_config()
        target = BatchOrganismTarget(
            organism="P. vivax",
            positive_controls=[],  # explicitly empty
            # negative_controls not set → None → use base
        )
        pos, neg = _resolve_controls(target, base)
        assert pos == []
        assert neg == base.negative_controls

    def test_batch_config_roundtrip(self) -> None:
        """Full BatchExperimentConfig with multiple targets."""
        base = _base_config()
        batch = BatchExperimentConfig(
            base_config=base,
            organism_param_name="organism",
            target_organisms=[
                BatchOrganismTarget(organism="P. vivax"),  # use base
                BatchOrganismTarget(organism="P. knowlesi", positive_controls=[]),
                BatchOrganismTarget(
                    organism="P. berghei",
                    positive_controls=["PBANKA_001"],
                    negative_controls=["PBANKA_999"],
                ),
            ],
        )
        results = [_resolve_controls(t, base) for t in batch.target_organisms]

        # P. vivax: falls back
        assert results[0] == (base.positive_controls, base.negative_controls)
        # P. knowlesi: explicit empty positive, fallback negative
        assert results[1] == ([], base.negative_controls)
        # P. berghei: explicit overrides
        assert results[2] == (["PBANKA_001"], ["PBANKA_999"])

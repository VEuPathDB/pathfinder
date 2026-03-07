"""Extended tests for seed gene lists — cross-list integrity and edge cases."""

from __future__ import annotations

import pytest

from veupath_chatbot.services.experiment.seed.definitions import SEEDS
from veupath_chatbot.services.experiment.seed.gene_lists import (
    CRYPTO_DNA_REPLICATION,
    CRYPTO_KINASES,
    CRYPTO_RIBOSOMAL,
    PLASMO_KINASES,
    PLASMO_RIBOSOMAL,
    TOXO_KINASES,
    TOXO_RIBOSOMAL,
    TRITRYP_KINASES,
    TRITRYP_RIBOSOMAL,
)

# ---------------------------------------------------------------------------
# Cross-list overlap: positives from different functional categories
# ---------------------------------------------------------------------------


class TestCrossListOverlap:
    def test_crypto_kinases_and_replication_no_overlap(self):
        """The CpIowaII UNION seed uses kinases + replication as positives.
        Ensure no overlap so the union is meaningful."""
        overlap = set(CRYPTO_KINASES) & set(CRYPTO_DNA_REPLICATION)
        assert len(overlap) == 0, f"Overlap: {overlap}"

    def test_crypto_replication_and_ribosomal_no_overlap(self):
        overlap = set(CRYPTO_DNA_REPLICATION) & set(CRYPTO_RIBOSOMAL)
        assert len(overlap) == 0, f"Overlap: {overlap}"


# ---------------------------------------------------------------------------
# Seed positive/negative control sizes
# ---------------------------------------------------------------------------


class TestSeedControlSizes:
    def test_all_seeds_have_at_least_5_positives(self):
        for seed in SEEDS:
            assert len(seed.control_set.positive_ids) >= 5, (
                f"Seed '{seed.name}' has only {len(seed.control_set.positive_ids)} positives"
            )

    def test_all_seeds_have_at_least_5_negatives(self):
        for seed in SEEDS:
            assert len(seed.control_set.negative_ids) >= 5, (
                f"Seed '{seed.name}' has only {len(seed.control_set.negative_ids)} negatives"
            )


# ---------------------------------------------------------------------------
# Gene list sizes are consistent (20 each for the main lists)
# ---------------------------------------------------------------------------


class TestGeneListSizes:
    @pytest.mark.parametrize(
        "gene_list,name,expected_size",
        [
            (PLASMO_KINASES, "PLASMO_KINASES", 20),
            (PLASMO_RIBOSOMAL, "PLASMO_RIBOSOMAL", 20),
            (TOXO_KINASES, "TOXO_KINASES", 20),
            (TOXO_RIBOSOMAL, "TOXO_RIBOSOMAL", 20),
            (CRYPTO_KINASES, "CRYPTO_KINASES", 20),
            (CRYPTO_RIBOSOMAL, "CRYPTO_RIBOSOMAL", 20),
            (TRITRYP_KINASES, "TRITRYP_KINASES", 20),
            (TRITRYP_RIBOSOMAL, "TRITRYP_RIBOSOMAL", 20),
        ],
    )
    def test_gene_list_exact_size(self, gene_list, name, expected_size):
        assert len(gene_list) == expected_size, (
            f"{name} has {len(gene_list)} entries, expected {expected_size}"
        )


# ---------------------------------------------------------------------------
# Seed step tree IDs are unique within each tree
# ---------------------------------------------------------------------------


class TestStepTreeIdUniqueness:
    def _collect_ids(self, node: dict) -> list[str]:
        ids = []
        node_id = node.get("id")
        if node_id:
            ids.append(node_id)
        if "primaryInput" in node:
            ids.extend(self._collect_ids(node["primaryInput"]))
        if "secondaryInput" in node:
            ids.extend(self._collect_ids(node["secondaryInput"]))
        return ids

    def test_all_seed_step_ids_unique_within_tree(self):
        for seed in SEEDS:
            ids = self._collect_ids(seed.step_tree)
            assert len(ids) == len(set(ids)), (
                f"Seed '{seed.name}' has duplicate step IDs: "
                f"{[i for i in ids if ids.count(i) > 1]}"
            )


# ---------------------------------------------------------------------------
# Gene ID format consistency
# ---------------------------------------------------------------------------


class TestGeneIdFormats:
    def test_plasmo_ribosomal_ids_start_with_pf3d7(self):
        for gene_id in PLASMO_RIBOSOMAL:
            assert gene_id.startswith("PF3D7_"), f"Unexpected prefix: {gene_id}"

    def test_toxo_ribosomal_ids_start_with_tgme49(self):
        for gene_id in TOXO_RIBOSOMAL:
            assert gene_id.startswith("TGME49_"), f"Unexpected prefix: {gene_id}"

    def test_crypto_ribosomal_ids_start_with_cgd(self):
        for gene_id in CRYPTO_RIBOSOMAL:
            assert gene_id.lower().startswith("cgd"), f"Unexpected prefix: {gene_id}"

    def test_tritryp_ribosomal_ids_start_with_lmjf(self):
        for gene_id in TRITRYP_RIBOSOMAL:
            assert gene_id.startswith("LmjF."), f"Unexpected prefix: {gene_id}"

    def test_crypto_dna_replication_ids_start_with_cgd(self):
        for gene_id in CRYPTO_DNA_REPLICATION:
            assert gene_id.startswith("cgd"), f"Unexpected prefix: {gene_id}"

    def test_no_gene_ids_have_whitespace(self):
        """Ensure no gene ID has leading/trailing whitespace."""
        all_lists = [
            PLASMO_KINASES,
            PLASMO_RIBOSOMAL,
            TOXO_KINASES,
            TOXO_RIBOSOMAL,
            CRYPTO_KINASES,
            CRYPTO_RIBOSOMAL,
            CRYPTO_DNA_REPLICATION,
            TRITRYP_KINASES,
            TRITRYP_RIBOSOMAL,
        ]
        for gene_list in all_lists:
            for gene_id in gene_list:
                assert gene_id == gene_id.strip(), (
                    f"Gene ID has whitespace: {gene_id!r}"
                )


# ---------------------------------------------------------------------------
# Seed control sets: positive IDs should be drawn from the correct organism
# ---------------------------------------------------------------------------


class TestSeedControlOrganismConsistency:
    def test_plasmodb_seeds_use_plasmo_gene_ids(self):
        for seed in SEEDS:
            if seed.site_id != "plasmodb":
                continue
            for gid in seed.control_set.positive_ids:
                assert gid.startswith("PF3D7_"), (
                    f"Seed '{seed.name}' (plasmodb) has non-Plasmo positive: {gid}"
                )
            for gid in seed.control_set.negative_ids:
                assert gid.startswith("PF3D7_"), (
                    f"Seed '{seed.name}' (plasmodb) has non-Plasmo negative: {gid}"
                )

    def test_toxodb_seeds_use_toxo_gene_ids(self):
        for seed in SEEDS:
            if seed.site_id != "toxodb":
                continue
            for gid in seed.control_set.positive_ids:
                assert gid.startswith("TGME49_"), (
                    f"Seed '{seed.name}' (toxodb) has non-Toxo positive: {gid}"
                )
            for gid in seed.control_set.negative_ids:
                assert gid.startswith("TGME49_"), (
                    f"Seed '{seed.name}' (toxodb) has non-Toxo negative: {gid}"
                )

    def test_cryptodb_seeds_use_crypto_gene_ids(self):
        for seed in SEEDS:
            if seed.site_id != "cryptodb":
                continue
            for gid in seed.control_set.positive_ids:
                assert gid.lower().startswith("cgd"), (
                    f"Seed '{seed.name}' (cryptodb) has non-Crypto positive: {gid}"
                )
            for gid in seed.control_set.negative_ids:
                assert gid.lower().startswith("cgd"), (
                    f"Seed '{seed.name}' (cryptodb) has non-Crypto negative: {gid}"
                )

    def test_tritrypdb_seeds_use_tritryp_gene_ids(self):
        for seed in SEEDS:
            if seed.site_id != "tritrypdb":
                continue
            for gid in seed.control_set.positive_ids:
                assert gid.startswith("LmjF."), (
                    f"Seed '{seed.name}' (tritrypdb) has non-TriTryp positive: {gid}"
                )
            for gid in seed.control_set.negative_ids:
                assert gid.startswith("LmjF."), (
                    f"Seed '{seed.name}' (tritrypdb) has non-TriTryp negative: {gid}"
                )

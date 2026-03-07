"""Unit tests for services.experiment.seed — definitions and gene_lists."""

import json

import pytest

from veupath_chatbot.services.experiment.seed.definitions import (
    SEEDS,
    ControlSetDef,
    SeedDef,
    _ec_kinase_params,
    _go_search_params,
    _org,
)
from veupath_chatbot.services.experiment.seed.gene_lists import (
    CP_ORG,
    CRYPTO_DNA_REPLICATION,
    CRYPTO_KINASES,
    CRYPTO_RIBOSOMAL,
    LM_ORG,
    PF_EC_SOURCES,
    PF_ORG,
    PLASMO_KINASES,
    PLASMO_RIBOSOMAL,
    TG_EC_SOURCES,
    TG_ORG,
    TOXO_KINASES,
    TOXO_RIBOSOMAL,
    TRITRYP_KINASES,
    TRITRYP_RIBOSOMAL,
)

# ---------------------------------------------------------------------------
# gene_lists.py — organism constants and gene ID data integrity
# ---------------------------------------------------------------------------


class TestOrganismConstants:
    def test_plasmodium_org(self):
        assert PF_ORG == "Plasmodium falciparum 3D7"

    def test_toxoplasma_org(self):
        assert TG_ORG == "Toxoplasma gondii ME49"

    def test_cryptosporidium_org(self):
        assert CP_ORG == "Cryptosporidium parvum Iowa II"

    def test_leishmania_org(self):
        assert LM_ORG == "Leishmania major strain Friedlin"


class TestECSources:
    def test_plasmodium_ec_sources(self):
        assert isinstance(PF_EC_SOURCES, list)
        assert len(PF_EC_SOURCES) > 0
        assert "GeneDB" in PF_EC_SOURCES

    def test_toxoplasma_ec_sources(self):
        assert isinstance(TG_EC_SOURCES, list)
        assert len(TG_EC_SOURCES) > 0
        assert "KEGG_Enzyme" in TG_EC_SOURCES


class TestGeneListIntegrity:
    """Verify gene lists contain valid, non-empty, non-duplicated IDs."""

    @pytest.mark.parametrize(
        "gene_list,name",
        [
            (PLASMO_KINASES, "PLASMO_KINASES"),
            (PLASMO_RIBOSOMAL, "PLASMO_RIBOSOMAL"),
            (TOXO_KINASES, "TOXO_KINASES"),
            (TOXO_RIBOSOMAL, "TOXO_RIBOSOMAL"),
            (CRYPTO_KINASES, "CRYPTO_KINASES"),
            (CRYPTO_RIBOSOMAL, "CRYPTO_RIBOSOMAL"),
            (CRYPTO_DNA_REPLICATION, "CRYPTO_DNA_REPLICATION"),
            (TRITRYP_KINASES, "TRITRYP_KINASES"),
            (TRITRYP_RIBOSOMAL, "TRITRYP_RIBOSOMAL"),
        ],
    )
    def test_gene_list_non_empty(self, gene_list, name):
        assert len(gene_list) > 0, f"{name} is empty"

    @pytest.mark.parametrize(
        "gene_list,name",
        [
            (PLASMO_KINASES, "PLASMO_KINASES"),
            (PLASMO_RIBOSOMAL, "PLASMO_RIBOSOMAL"),
            (TOXO_KINASES, "TOXO_KINASES"),
            (TOXO_RIBOSOMAL, "TOXO_RIBOSOMAL"),
            (CRYPTO_KINASES, "CRYPTO_KINASES"),
            (CRYPTO_RIBOSOMAL, "CRYPTO_RIBOSOMAL"),
            (CRYPTO_DNA_REPLICATION, "CRYPTO_DNA_REPLICATION"),
            (TRITRYP_KINASES, "TRITRYP_KINASES"),
            (TRITRYP_RIBOSOMAL, "TRITRYP_RIBOSOMAL"),
        ],
    )
    def test_gene_list_no_duplicates(self, gene_list, name):
        assert len(gene_list) == len(set(gene_list)), f"{name} contains duplicate IDs"

    @pytest.mark.parametrize(
        "gene_list,name",
        [
            (PLASMO_KINASES, "PLASMO_KINASES"),
            (PLASMO_RIBOSOMAL, "PLASMO_RIBOSOMAL"),
            (TOXO_KINASES, "TOXO_KINASES"),
            (TOXO_RIBOSOMAL, "TOXO_RIBOSOMAL"),
            (CRYPTO_KINASES, "CRYPTO_KINASES"),
            (CRYPTO_RIBOSOMAL, "CRYPTO_RIBOSOMAL"),
            (CRYPTO_DNA_REPLICATION, "CRYPTO_DNA_REPLICATION"),
            (TRITRYP_KINASES, "TRITRYP_KINASES"),
            (TRITRYP_RIBOSOMAL, "TRITRYP_RIBOSOMAL"),
        ],
    )
    def test_gene_list_all_strings(self, gene_list, name):
        for gene_id in gene_list:
            assert isinstance(gene_id, str), f"{name} contains non-string: {gene_id!r}"
            assert gene_id.strip() == gene_id, (
                f"{name} contains whitespace-padded ID: {gene_id!r}"
            )
            assert len(gene_id) > 0, f"{name} contains empty string"

    def test_plasmo_kinases_have_20_entries(self):
        assert len(PLASMO_KINASES) == 20

    def test_plasmo_ribosomal_have_20_entries(self):
        assert len(PLASMO_RIBOSOMAL) == 20

    def test_plasmo_kinases_ids_start_with_pf3d7(self):
        for gene_id in PLASMO_KINASES:
            assert gene_id.startswith("PF3D7_"), f"Unexpected prefix: {gene_id}"

    def test_toxo_ids_start_with_tgme49(self):
        for gene_id in TOXO_KINASES:
            assert gene_id.startswith("TGME49_"), f"Unexpected prefix: {gene_id}"

    def test_crypto_ids_start_with_cgd(self):
        for gene_id in CRYPTO_KINASES:
            assert gene_id.lower().startswith("cgd"), f"Unexpected prefix: {gene_id}"

    def test_tritryp_ids_start_with_lmjf(self):
        for gene_id in TRITRYP_KINASES:
            assert gene_id.startswith("LmjF."), f"Unexpected prefix: {gene_id}"

    def test_kinase_ribosomal_no_overlap(self):
        """Positive and negative controls must not overlap."""
        for kinases, ribosomal, org in [
            (PLASMO_KINASES, PLASMO_RIBOSOMAL, "plasmo"),
            (TOXO_KINASES, TOXO_RIBOSOMAL, "toxo"),
            (CRYPTO_KINASES, CRYPTO_RIBOSOMAL, "crypto"),
            (TRITRYP_KINASES, TRITRYP_RIBOSOMAL, "tritryp"),
        ]:
            overlap = set(kinases) & set(ribosomal)
            assert len(overlap) == 0, f"{org} kinases and ribosomal overlap: {overlap}"


# ---------------------------------------------------------------------------
# definitions.py — helper functions
# ---------------------------------------------------------------------------


class TestOrgHelper:
    def test_org_returns_json_array(self):
        result = _org(["Plasmodium falciparum 3D7"])
        parsed = json.loads(result)
        assert parsed == ["Plasmodium falciparum 3D7"]

    def test_org_multiple_names(self):
        result = _org(["Org A", "Org B"])
        parsed = json.loads(result)
        assert parsed == ["Org A", "Org B"]

    def test_org_empty_list(self):
        result = _org([])
        parsed = json.loads(result)
        assert parsed == []


class TestGoSearchParams:
    def test_returns_expected_keys(self):
        params = _go_search_params("Plasmodium falciparum 3D7", "GO:0004672")
        assert set(params.keys()) == {
            "organism",
            "go_term_evidence",
            "go_term_slim",
            "go_typeahead",
            "go_term",
        }

    def test_organism_is_json_array(self):
        params = _go_search_params("Plasmodium falciparum 3D7", "GO:0004672")
        parsed = json.loads(params["organism"])
        assert parsed == ["Plasmodium falciparum 3D7"]

    def test_go_term_id(self):
        params = _go_search_params("Some org", "GO:0003735")
        assert params["go_term"] == "GO:0003735"
        parsed_typeahead = json.loads(params["go_typeahead"])
        assert parsed_typeahead == ["GO:0003735"]

    def test_evidence_includes_curated_and_computed(self):
        params = _go_search_params("Org", "GO:0000001")
        evidence = json.loads(params["go_term_evidence"])
        assert "Curated" in evidence
        assert "Computed" in evidence

    def test_go_term_slim_is_no(self):
        params = _go_search_params("Org", "GO:0000001")
        assert params["go_term_slim"] == "No"


class TestEcKinaseParams:
    def test_returns_expected_keys(self):
        params = _ec_kinase_params("Org", ["GeneDB", "KEGG"])
        assert set(params.keys()) == {
            "organism",
            "ec_source",
            "ec_number_pattern",
            "ec_wildcard",
        }

    def test_ec_number_pattern(self):
        params = _ec_kinase_params("Org", ["GeneDB"])
        assert params["ec_number_pattern"] == "2.7.11.1"

    def test_ec_wildcard_is_no(self):
        params = _ec_kinase_params("Org", ["GeneDB"])
        assert params["ec_wildcard"] == "No"

    def test_ec_source_is_json_array(self):
        params = _ec_kinase_params("Org", ["GeneDB", "KEGG_Enzyme"])
        parsed = json.loads(params["ec_source"])
        assert parsed == ["GeneDB", "KEGG_Enzyme"]

    def test_organism_is_json_array(self):
        params = _ec_kinase_params("Org", ["GeneDB"])
        parsed = json.loads(params["organism"])
        assert parsed == ["Org"]


# ---------------------------------------------------------------------------
# definitions.py — dataclasses
# ---------------------------------------------------------------------------


class TestControlSetDef:
    def test_fields(self):
        cs = ControlSetDef(
            name="Test",
            positive_ids=["a", "b"],
            negative_ids=["c"],
            provenance_notes="notes",
            tags=["tag1"],
        )
        assert cs.name == "Test"
        assert cs.positive_ids == ["a", "b"]
        assert cs.negative_ids == ["c"]
        assert cs.provenance_notes == "notes"
        assert cs.tags == ["tag1"]

    def test_tags_default_empty(self):
        cs = ControlSetDef(
            name="X",
            positive_ids=[],
            negative_ids=[],
            provenance_notes="",
        )
        assert cs.tags == []


class TestSeedDef:
    def test_fields(self):
        sd = SeedDef(
            name="Test Seed",
            description="A test",
            site_id="plasmodb",
            step_tree={"id": "s1"},
            control_set=ControlSetDef(
                name="CS",
                positive_ids=["p1"],
                negative_ids=["n1"],
                provenance_notes="notes",
            ),
        )
        assert sd.name == "Test Seed"
        assert sd.site_id == "plasmodb"
        assert sd.record_type == "transcript"  # default

    def test_record_type_override(self):
        sd = SeedDef(
            name="X",
            description="",
            site_id="toxodb",
            step_tree={},
            control_set=ControlSetDef(
                name="CS", positive_ids=[], negative_ids=[], provenance_notes=""
            ),
            record_type="gene",
        )
        assert sd.record_type == "gene"


# ---------------------------------------------------------------------------
# SEEDS list — structural validation
# ---------------------------------------------------------------------------


class TestSeedsList:
    def test_seeds_is_non_empty(self):
        assert len(SEEDS) > 0

    def test_all_seeds_are_seed_def(self):
        for seed in SEEDS:
            assert isinstance(seed, SeedDef), f"Expected SeedDef, got {type(seed)}"

    def test_all_seeds_have_required_fields(self):
        for seed in SEEDS:
            assert seed.name, "Seed missing name"
            assert seed.description, f"Seed '{seed.name}' missing description"
            assert seed.site_id, f"Seed '{seed.name}' missing site_id"
            assert seed.step_tree, f"Seed '{seed.name}' missing step_tree"
            assert seed.control_set, f"Seed '{seed.name}' missing control_set"

    def test_all_control_sets_have_positive_and_negative(self):
        for seed in SEEDS:
            cs = seed.control_set
            assert len(cs.positive_ids) > 0, (
                f"Seed '{seed.name}' has no positive controls"
            )
            assert len(cs.negative_ids) > 0, (
                f"Seed '{seed.name}' has no negative controls"
            )

    def test_all_control_sets_no_overlap(self):
        for seed in SEEDS:
            cs = seed.control_set
            overlap = set(cs.positive_ids) & set(cs.negative_ids)
            assert len(overlap) == 0, (
                f"Seed '{seed.name}' has overlapping controls: {overlap}"
            )

    def test_all_step_trees_have_id(self):
        for seed in SEEDS:
            assert "id" in seed.step_tree, f"Seed '{seed.name}' step_tree missing 'id'"

    def test_known_site_ids(self):
        known = {"plasmodb", "toxodb", "cryptodb", "tritrypdb"}
        for seed in SEEDS:
            assert seed.site_id in known, (
                f"Seed '{seed.name}' has unknown site_id: {seed.site_id}"
            )

    def test_all_seed_names_unique(self):
        names = [s.name for s in SEEDS]
        assert len(names) == len(set(names)), "Duplicate seed names found"

    @pytest.mark.parametrize("site_id", ["plasmodb", "toxodb", "cryptodb", "tritrypdb"])
    def test_each_site_has_at_least_one_seed(self, site_id):
        site_seeds = [s for s in SEEDS if s.site_id == site_id]
        assert len(site_seeds) > 0, f"No seeds for site {site_id}"

    def test_step_tree_leaf_nodes_have_search_name(self):
        """Every leaf node in a step tree must have a searchName."""

        def _check_leaves(node, seed_name):
            has_primary = "primaryInput" in node
            has_secondary = "secondaryInput" in node
            if not has_primary and not has_secondary:
                # This is a leaf node
                assert "searchName" in node, (
                    f"Seed '{seed_name}' leaf node '{node.get('id')}' "
                    f"missing searchName"
                )
            if has_primary:
                _check_leaves(node["primaryInput"], seed_name)
            if has_secondary:
                _check_leaves(node["secondaryInput"], seed_name)

        for seed in SEEDS:
            _check_leaves(seed.step_tree, seed.name)

    def test_combine_nodes_have_operator(self):
        """Any node with both primaryInput and secondaryInput must have an operator."""

        def _check_operators(node, seed_name):
            has_primary = "primaryInput" in node
            has_secondary = "secondaryInput" in node
            if has_primary and has_secondary:
                assert "operator" in node, (
                    f"Seed '{seed_name}' combine node '{node.get('id')}' "
                    f"missing operator"
                )
                assert node["operator"] in ("INTERSECT", "UNION", "MINUS"), (
                    f"Seed '{seed_name}' invalid operator: {node.get('operator')}"
                )
            if has_primary:
                _check_operators(node["primaryInput"], seed_name)
            if has_secondary:
                _check_operators(node["secondaryInput"], seed_name)

        for seed in SEEDS:
            _check_operators(seed.step_tree, seed.name)

    def test_all_provenance_notes_non_empty(self):
        for seed in SEEDS:
            assert seed.control_set.provenance_notes.strip(), (
                f"Seed '{seed.name}' has empty provenance_notes"
            )

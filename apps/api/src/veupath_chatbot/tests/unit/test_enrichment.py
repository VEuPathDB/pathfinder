"""Tests for enrichment analysis helpers.

Verifies parameter names match VEuPathDB WDK step analysis plugins
(``stepAnalysisPlugins.xml`` / ``GoEnrichmentPlugin.java``).
"""

import pytest

from veupath_chatbot.services.experiment.enrichment import (
    _ANALYSIS_TYPE_MAP,
    _GO_ONTOLOGY_MAP,
    _extract_analysis_rows,
    _extract_default_params,
    _extract_vocab_values,
    _parse_enrichment_terms,
    _parse_result_genes_html,
    encode_vocab_params,
    infer_enrichment_type,
    is_enrichment_analysis,
    parse_enrichment_from_raw,
    upsert_enrichment_result,
)
from veupath_chatbot.services.experiment.types import EnrichmentResult


class TestAnalysisTypeMaps:
    """Verify constants match WDK stepAnalysisPlugins.xml plugin names."""

    def test_go_types_map_to_go_enrichment(self) -> None:
        for key in ("go_function", "go_component", "go_process"):
            assert _ANALYSIS_TYPE_MAP[key] == "go-enrichment"

    def test_pathway_maps_to_pathway_enrichment(self) -> None:
        assert _ANALYSIS_TYPE_MAP["pathway"] == "pathway-enrichment"

    def test_word_maps_to_word_enrichment(self) -> None:
        assert _ANALYSIS_TYPE_MAP["word"] == "word-enrichment"

    def test_go_ontology_values_match_wdk(self) -> None:
        assert _GO_ONTOLOGY_MAP["go_function"] == "Molecular Function"
        assert _GO_ONTOLOGY_MAP["go_component"] == "Cellular Component"
        assert _GO_ONTOLOGY_MAP["go_process"] == "Biological Process"

    def test_go_ontology_keys_subset_of_analysis_map(self) -> None:
        assert set(_GO_ONTOLOGY_MAP.keys()).issubset(set(_ANALYSIS_TYPE_MAP.keys()))


class TestEncodeVocabParams:
    """encode_vocab_params encodes vocabulary params as JSON arrays.

    WDK ``AbstractEnumParam.convertToTerms()`` does
    ``new JSONArray(stableValue)`` — vocab param values MUST be
    JSON-encoded arrays.  Only ``single-pick-vocabulary`` and
    ``multi-pick-vocabulary`` types (from ``EnumParamFormatter.getParamType()``)
    need this encoding.  All other types (``number``, ``string``, ``filter``,
    ``input-step``, ``input-dataset``, etc.) are left as-is.
    """

    def test_encodes_user_params_after_merge(self) -> None:
        """User-supplied plain strings must be encoded after merge.

        This is the critical bug: ``_merge_analysis_params`` was doing
        ``{**defaults, **user_params}``, letting plain-string user params
        override properly-encoded defaults.  ``encode_vocab_params``
        re-encodes all vocab params using the form metadata.
        """
        from veupath_chatbot.tests.fixtures.wdk_responses import (
            pathway_enrichment_form_response,
        )

        form = pathway_enrichment_form_response()
        # Simulate what happens: user sends plain strings from frontend
        merged = {
            "organism": "Plasmodium falciparum 3D7",  # plain string (from user)
            "pathwaysSources": '["KEGG","MetaCyc"]',  # already JSON array
            "pValueCutoff": "0.05",
            "exact_match_only": "Yes",  # plain string (from user)
            "exclude_incomplete_ec": "No",  # plain string (from user)
        }
        result = encode_vocab_params(merged, form)

        assert result["organism"] == '["Plasmodium falciparum 3D7"]'
        assert result["exact_match_only"] == '["Yes"]'
        assert result["exclude_incomplete_ec"] == '["No"]'
        assert result["pathwaysSources"] == '["KEGG","MetaCyc"]'  # unchanged
        assert result["pValueCutoff"] == "0.05"  # number — unchanged

    def test_does_not_double_encode(self) -> None:
        """Values already encoded as JSON arrays are left alone."""
        from veupath_chatbot.tests.fixtures.wdk_responses import (
            pathway_enrichment_form_response,
        )

        form = pathway_enrichment_form_response()
        merged = {
            "organism": '["Plasmodium falciparum 3D7"]',  # already encoded
            "exact_match_only": '["Yes"]',
            "pValueCutoff": "0.05",
        }
        result = encode_vocab_params(merged, form)
        assert result["organism"] == '["Plasmodium falciparum 3D7"]'
        assert result["exact_match_only"] == '["Yes"]'

    def test_handles_missing_form_metadata(self) -> None:
        """When form metadata is empty/invalid, params are returned as-is."""
        merged = {"organism": "Plasmodium falciparum 3D7"}
        assert encode_vocab_params(merged, {}) == merged
        assert encode_vocab_params(merged, None) == merged

    def test_handles_params_not_in_form(self) -> None:
        """Params not listed in form metadata are left untouched."""
        from veupath_chatbot.tests.fixtures.wdk_responses import (
            pathway_enrichment_form_response,
        )

        form = pathway_enrichment_form_response()
        merged = {
            "organism": "Plasmodium falciparum 3D7",
            "unknownParam": "some value",
        }
        result = encode_vocab_params(merged, form)
        assert result["organism"] == '["Plasmodium falciparum 3D7"]'
        assert result["unknownParam"] == "some value"


class TestExtractDefaultParams:
    """_extract_default_params extracts name/initialDisplayValue from WDK form metadata.

    WDK's ``ParamFormatter.java`` uses ``initialDisplayValue`` as the
    stable default value field (via ``JsonKeys.INITIAL_DISPLAY_VALUE``).
    """

    def test_extracts_and_encodes_enum_params(self) -> None:
        """Single-pick enum/vocab params are wrapped in JSON arrays.

        WDK pathway-enrichment ``organism`` has ``initialDisplayValue``
        of ``"Plasmodium falciparum 3D7"`` (plain string), but the plugin
        does ``AbstractEnumParam.convertToTerms(params.get("organism"))``
        which calls ``new JSONArray(stableValue)`` — requires JSON array.
        """
        from veupath_chatbot.tests.fixtures.wdk_responses import (
            pathway_enrichment_form_response,
        )

        form = pathway_enrichment_form_response()
        result = _extract_default_params(form)

        # Enum/vocab params must be JSON arrays
        assert result["organism"] == '["Plasmodium falciparum 3D7"]'
        assert result["exact_match_only"] == '["Yes"]'
        assert result["exclude_incomplete_ec"] == '["No"]'

        # Multi-pick enum already comes as JSON array — must stay as-is
        assert result["pathwaysSources"] == '["KEGG","MetaCyc"]'

        # NumberParam stays as plain string
        assert result["pValueCutoff"] == "0.05"

    def test_extracts_go_enrichment_params(self) -> None:
        from veupath_chatbot.tests.fixtures.wdk_responses import (
            go_enrichment_form_response,
        )

        form = go_enrichment_form_response()
        result = _extract_default_params(form)

        assert result["goAssociationsOntologies"] == '["Biological Process"]'
        assert result["goEvidenceCodes"] == '["Computed","Curated"]'
        assert result["pValueCutoff"] == "0.05"
        assert result["organism"] == '["Plasmodium falciparum 3D7"]'

    def test_extracts_from_valid_form(self) -> None:
        """Legacy form without type info: values are kept as-is."""
        form = {
            "parameters": [
                {
                    "name": "goAssociationsOntologies",
                    "initialDisplayValue": "Biological Process",
                },
                {"name": "pValueCutoff", "initialDisplayValue": "0.05"},
                {
                    "name": "organism",
                    "initialDisplayValue": "Plasmodium falciparum 3D7",
                },
            ]
        }
        result = _extract_default_params(form)
        assert result == {
            "goAssociationsOntologies": "Biological Process",
            "pValueCutoff": "0.05",
            "organism": "Plasmodium falciparum 3D7",
        }

    def test_skips_none_initial_display_value(self) -> None:
        """Parameters with None initialDisplayValue are omitted (WDK rejects empty)."""
        form = {"parameters": [{"name": "pValueCutoff", "initialDisplayValue": None}]}
        result = _extract_default_params(form)
        assert result == {}

    def test_skips_missing_initial_display_value(self) -> None:
        """Parameters without initialDisplayValue are omitted."""
        form = {"parameters": [{"name": "pValueCutoff"}]}
        result = _extract_default_params(form)
        assert result == {}

    def test_skips_invalid_entries(self) -> None:
        form = {
            "parameters": [
                {"name": "valid", "initialDisplayValue": "x"},
                {"name": "", "initialDisplayValue": "y"},
                {"name": None, "initialDisplayValue": "z"},
                {"initialDisplayValue": "no name"},
                "not a dict",
            ]
        }
        result = _extract_default_params(form)
        assert result == {"valid": "x"}

    def test_handles_no_parameters_key(self) -> None:
        assert _extract_default_params({}) == {}

    def test_handles_non_list_parameters(self) -> None:
        assert _extract_default_params({"parameters": "bad"}) == {}

    def test_handles_non_dict_input(self) -> None:
        assert _extract_default_params(None) == {}
        assert _extract_default_params([]) == {}
        assert _extract_default_params("string") == {}


class TestExtractVocabValues:
    """_extract_vocab_values extracts allowed values from WDK param vocabulary."""

    def test_extracts_ontology_values_from_go_form(self) -> None:
        """Real WDK GO enrichment form has vocabulary triples: [value, display, null]."""
        form = {
            "searchData": {
                "parameters": [
                    {
                        "name": "goAssociationsOntologies",
                        "type": "single-pick-vocabulary",
                        "vocabulary": [
                            ["Cellular Component", "Cellular Component", None],
                            ["Molecular Function", "Molecular Function", None],
                        ],
                    },
                ]
            }
        }
        values = _extract_vocab_values(form, "goAssociationsOntologies")
        assert values == ["Cellular Component", "Molecular Function"]

    def test_extracts_all_three_ontologies(self) -> None:
        """PlasmoDB has all 3 GO ontologies available."""
        form = {
            "searchData": {
                "parameters": [
                    {
                        "name": "goAssociationsOntologies",
                        "type": "single-pick-vocabulary",
                        "vocabulary": [
                            ["Biological Process", "Biological Process", None],
                            ["Cellular Component", "Cellular Component", None],
                            ["Molecular Function", "Molecular Function", None],
                        ],
                    },
                ]
            }
        }
        values = _extract_vocab_values(form, "goAssociationsOntologies")
        assert "Biological Process" in values
        assert "Cellular Component" in values
        assert "Molecular Function" in values

    def test_returns_empty_for_missing_param(self) -> None:
        form = {"searchData": {"parameters": [{"name": "other", "vocabulary": []}]}}
        assert _extract_vocab_values(form, "goAssociationsOntologies") == []

    def test_returns_empty_for_no_vocabulary(self) -> None:
        form = {"searchData": {"parameters": [{"name": "goAssociationsOntologies"}]}}
        assert _extract_vocab_values(form, "goAssociationsOntologies") == []

    def test_returns_empty_for_none_input(self) -> None:
        assert _extract_vocab_values(None, "anything") == []

    def test_returns_empty_for_empty_dict(self) -> None:
        assert _extract_vocab_values({}, "anything") == []

    def test_handles_form_without_search_data_wrapper(self) -> None:
        """Form metadata may or may not have the searchData wrapper."""
        form = {
            "parameters": [
                {
                    "name": "organism",
                    "type": "single-pick-vocabulary",
                    "vocabulary": [
                        ["Plasmodium falciparum 3D7", "P. falciparum 3D7", None],
                    ],
                },
            ]
        }
        values = _extract_vocab_values(form, "organism")
        assert values == ["Plasmodium falciparum 3D7"]


class TestParseEnrichmentTerms:
    """_parse_enrichment_terms handles both WDK row formats."""

    def test_parses_standard_wdk_rows(self) -> None:
        rows = [
            {
                "ID": "GO:0003735",
                "Description": "structural constituent of ribosome",
                "ResultCount": 42,
                "BgdCount": 100,
                "FoldEnrich": 3.14,
                "OddsRatio": 2.5,
                "PValue": 0.001,
                "BenjaminiHochberg": 0.01,
                "Bonferroni": 0.05,
                "ResultIDList": "PF3D7_0100100,PF3D7_0831900",
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.term_id == "GO:0003735"
        assert t.term_name == "structural constituent of ribosome"
        assert t.gene_count == 42
        assert t.background_count == 100
        assert t.fold_enrichment == pytest.approx(3.14)
        assert t.odds_ratio == pytest.approx(2.5)
        assert t.p_value == pytest.approx(0.001)
        assert t.fdr == pytest.approx(0.01)
        assert t.bonferroni == pytest.approx(0.05)
        assert t.genes == ["PF3D7_0100100", "PF3D7_0831900"]

    def test_parses_alternative_key_names(self) -> None:
        rows = [
            {
                "id": "GO:0005840",
                "description": "ribosome",
                "resultCount": 10,
                "bgdCount": 50,
                "foldEnrichment": 2.0,
                "oddsRatio": 1.5,
                "pValue": 0.05,
                "benjamini": 0.1,
                "bonferroni": 0.2,
                "genes": ["G1", "G2"],
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.term_id == "GO:0005840"
        assert t.genes == ["G1", "G2"]

    def test_handles_empty_list(self) -> None:
        assert _parse_enrichment_terms([]) == []

    def test_skips_non_dict_entries(self) -> None:
        rows: list = [{"ID": "GO:1", "Description": "x"}, "bad", None]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1

    def test_parses_wdk_go_enrichment_rows(self) -> None:
        """WDK GO enrichment uses goId, goTerm, resultGenes (HTML), bgdGenes, foldEnrich."""
        rows = [
            {
                "goId": "GO:0006260",
                "goTerm": "DNA replication",
                "resultGenes": "<a href='/a/app/search/transcript/GeneByLocusTag?param.ds_gene_ids.idList=PF3D7_0111300,PF3D7_0215800,&autoRun=1'>2</a>",
                "bgdGenes": "46",
                "foldEnrich": "3.48",
                "oddsRatio": "9.46",
                "pValue": "3.40e-13",
                "benjamini": "4.58e-10",
                "bonferroni": "4.58e-10",
                "percentInResult": "69.6",
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.term_id == "GO:0006260"
        assert t.term_name == "DNA replication"
        assert t.gene_count == 2
        assert t.background_count == 46
        assert t.fold_enrichment == pytest.approx(3.48)
        assert t.odds_ratio == pytest.approx(9.46)
        assert t.p_value == pytest.approx(3.40e-13)
        assert t.fdr == pytest.approx(4.58e-10)
        assert t.bonferroni == pytest.approx(4.58e-10)
        assert t.genes == ["PF3D7_0111300", "PF3D7_0215800"]

    def test_infinity_odds_ratio_becomes_zero(self) -> None:
        """WDK returns 'Infinity' for oddsRatio when denominator is zero."""
        rows = [
            {
                "goId": "GO:0009060",
                "goTerm": "aerobic respiration",
                "resultGenes": "<a href='?idList=G1,&autoRun=1'>1</a>",
                "bgdGenes": "0",
                "foldEnrich": "Infinity",
                "oddsRatio": "Infinity",
                "pValue": "0.001",
                "benjamini": "0.01",
                "bonferroni": "0.05",
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.fold_enrichment == 0.0
        assert t.odds_ratio == 0.0

    def test_parses_word_enrichment_rows(self) -> None:
        """WDK Word enrichment uses 'word' as ID and 'descrip' as description."""
        rows = [
            {
                "word": "kinase",
                "descrip": "Protein kinase activity",
                "bgdGenes": "300",
                "resultGenes": "<a href='?idList=G1,G2,&autoRun=1'>2</a>",
                "foldEnrich": "4.2",
                "oddsRatio": "3.1",
                "pValue": "0.003",
                "benjamini": "0.02",
                "bonferroni": "0.04",
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.term_id == "kinase"
        assert t.term_name == "Protein kinase activity"
        assert t.gene_count == 2
        assert t.background_count == 300
        assert t.fold_enrichment == pytest.approx(4.2)
        assert t.genes == ["G1", "G2"]

    def test_parses_word_enrichment_no_descrip(self) -> None:
        """Word enrichment with no 'descrip' uses 'word' for both ID and name."""
        rows = [
            {
                "word": "ribosome",
                "bgdGenes": "50",
                "resultGenes": "<a href='?idList=G1,&autoRun=1'>1</a>",
                "foldEnrich": "2.0",
                "oddsRatio": "1.5",
                "pValue": "0.05",
                "benjamini": "0.1",
                "bonferroni": "0.2",
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        assert terms[0].term_id == "ribosome"
        assert terms[0].term_name == "ribosome"

    def test_parses_pathway_enrichment_rows(self) -> None:
        """Pathway enrichment uses pathwayId and pathwayName."""
        rows = [
            {
                "pathwayId": "ec01100",
                "pathwayName": "Metabolic pathways",
                "bgdGenes": "200",
                "resultGenes": "<a href='?idList=G1,G2,G3,&autoRun=1'>3</a>",
                "foldEnrich": "2.5",
                "oddsRatio": "1.8",
                "pValue": "0.01",
                "benjamini": "0.05",
                "bonferroni": "0.1",
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        assert terms[0].term_id == "ec01100"
        assert terms[0].term_name == "Metabolic pathways"
        assert terms[0].gene_count == 3
        assert terms[0].genes == ["G1", "G2", "G3"]


class TestParseResultGenesHtml:
    """_parse_result_genes_html extracts count and gene IDs from WDK HTML links."""

    def test_extracts_count_and_genes(self) -> None:
        html = "<a href='/search?param.ds_gene_ids.idList=GENE_A,GENE_B,GENE_C,&autoRun=1'>3</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 3
        assert genes == ["GENE_A", "GENE_B", "GENE_C"]

    def test_handles_no_trailing_comma(self) -> None:
        html = "<a href='?idList=G1,G2&autoRun=1'>2</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 2
        assert genes == ["G1", "G2"]

    def test_handles_empty_html(self) -> None:
        count, genes = _parse_result_genes_html("")
        assert count == 0
        assert genes == []

    def test_handles_no_idlist(self) -> None:
        html = "<a href='/search'>5</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 5
        assert genes == []


class TestExtractAnalysisRows:
    """_extract_analysis_rows handles multiple WDK response formats."""

    def test_extracts_from_result_data(self) -> None:
        result = {"resultData": [{"goId": "GO:1"}, {"goId": "GO:2"}]}
        rows = _extract_analysis_rows(result)
        assert len(rows) == 2

    def test_extracts_from_rows_key(self) -> None:
        result = {"rows": [{"id": "1"}]}
        assert len(_extract_analysis_rows(result)) == 1

    def test_extracts_from_data_key(self) -> None:
        result = {"data": [{"id": "1"}]}
        assert len(_extract_analysis_rows(result)) == 1

    def test_prefers_result_data_over_rows(self) -> None:
        """resultData takes precedence (enrichment plugins use it)."""
        result = {"resultData": [{"goId": "GO:1"}], "rows": [{"id": "other"}]}
        rows = _extract_analysis_rows(result)
        assert rows[0].get("goId") == "GO:1"

    def test_returns_empty_for_non_dict(self) -> None:
        assert _extract_analysis_rows(None) == []
        assert _extract_analysis_rows([]) == []

    def test_filters_non_dict_entries(self) -> None:
        result = {"resultData": [{"goId": "GO:1"}, "bad", None]}
        rows = _extract_analysis_rows(result)
        assert len(rows) == 1


class TestInferEnrichmentType:
    """infer_enrichment_type resolves WDK analysis names to EnrichmentAnalysisType."""

    def test_go_enrichment_from_params(self) -> None:
        assert (
            infer_enrichment_type(
                "go-enrichment",
                {"goAssociationsOntologies": "Molecular Function"},
                {},
            )
            == "go_function"
        )

    def test_go_enrichment_from_result_ontologies(self) -> None:
        assert (
            infer_enrichment_type(
                "go-enrichment",
                {},
                {"goOntologies": ["Cellular Component"]},
            )
            == "go_component"
        )

    def test_go_enrichment_defaults_to_go_process(self) -> None:
        assert infer_enrichment_type("go-enrichment", {}, {}) == "go_process"

    def test_pathway_enrichment(self) -> None:
        assert infer_enrichment_type("pathway-enrichment", {}, {}) == "pathway"

    def test_word_enrichment(self) -> None:
        assert infer_enrichment_type("word-enrichment", {}, {}) == "word"


class TestIsEnrichmentAnalysis:
    def test_recognizes_enrichment_names(self) -> None:
        assert is_enrichment_analysis("go-enrichment")
        assert is_enrichment_analysis("pathway-enrichment")
        assert is_enrichment_analysis("word-enrichment")

    def test_rejects_non_enrichment(self) -> None:
        assert not is_enrichment_analysis("word-cloud")
        assert not is_enrichment_analysis("some-other-analysis")


class TestParseEnrichmentFromRaw:
    """parse_enrichment_from_raw converts raw WDK JSON to EnrichmentResult."""

    def test_full_go_enrichment_result(self) -> None:
        raw = {
            "goOntologies": ["Biological Process"],
            "resultData": [
                {
                    "goId": "GO:0006260",
                    "goTerm": "DNA replication",
                    "resultGenes": "<a href='?idList=G1,G2,&autoRun=1'>2</a>",
                    "bgdGenes": "46",
                    "foldEnrich": "3.48",
                    "oddsRatio": "9.46",
                    "pValue": "3.40e-13",
                    "benjamini": "4.58e-10",
                    "bonferroni": "4.58e-10",
                },
            ],
        }
        er = parse_enrichment_from_raw("go-enrichment", {}, raw)
        assert er.analysis_type == "go_process"
        assert len(er.terms) == 1
        assert er.terms[0].term_id == "GO:0006260"
        assert er.terms[0].genes == ["G1", "G2"]


class TestUpsertEnrichmentResult:
    """upsert_enrichment_result replaces existing results of the same analysis_type."""

    def _make_result(self, analysis_type, n_terms=1):
        return EnrichmentResult(
            analysis_type=analysis_type,
            terms=[],
            total_genes_analyzed=n_terms,
            background_size=0,
        )

    def test_appends_new_type(self) -> None:
        results: list[EnrichmentResult] = []
        upsert_enrichment_result(results, self._make_result("go_process", 10))
        assert len(results) == 1
        assert results[0].total_genes_analyzed == 10

    def test_replaces_existing_type(self) -> None:
        results = [self._make_result("go_process", 5)]
        upsert_enrichment_result(results, self._make_result("go_process", 20))
        assert len(results) == 1
        assert results[0].total_genes_analyzed == 20

    def test_preserves_other_types(self) -> None:
        results = [
            self._make_result("go_process", 5),
            self._make_result("pathway", 10),
        ]
        upsert_enrichment_result(results, self._make_result("go_process", 20))
        assert len(results) == 2
        types = [r.analysis_type for r in results]
        assert types == ["go_process", "pathway"]
        assert results[0].total_genes_analyzed == 20
        assert results[1].total_genes_analyzed == 10

    def test_multiple_upserts(self) -> None:
        results: list[EnrichmentResult] = []
        upsert_enrichment_result(results, self._make_result("go_process"))
        upsert_enrichment_result(results, self._make_result("pathway"))
        upsert_enrichment_result(results, self._make_result("word"))
        upsert_enrichment_result(results, self._make_result("go_process", 99))
        upsert_enrichment_result(results, self._make_result("pathway", 88))
        assert len(results) == 3
        assert results[0].total_genes_analyzed == 99
        assert results[1].total_genes_analyzed == 88

"""Extended tests for enrichment service and enrichment parsing.

Covers: empty gene lists, large result sets, missing/malformed enrichment
result fields, GO ontology parameter inference, vocabulary param encoding,
HTML gene link parsing, and edge cases in enrichment term extraction.
"""

from veupath_chatbot.services.experiment.enrichment import (
    _encode_vocab_value,
    _extract_analysis_rows,
    _extract_default_params,
    _parse_enrichment_terms,
    _parse_result_genes_html,
    encode_vocab_params,
    infer_enrichment_type,
    is_enrichment_analysis,
    parse_enrichment_from_raw,
    upsert_enrichment_result,
)
from veupath_chatbot.services.experiment.types import (
    EnrichmentResult,
    EnrichmentTerm,
)

# ===========================================================================
# is_enrichment_analysis
# ===========================================================================


class TestIsEnrichmentAnalysis:
    """Check if a WDK analysis name is an enrichment plugin."""

    def test_go_enrichment(self) -> None:
        assert is_enrichment_analysis("go-enrichment") is True

    def test_pathway_enrichment(self) -> None:
        assert is_enrichment_analysis("pathway-enrichment") is True

    def test_word_enrichment(self) -> None:
        assert is_enrichment_analysis("word-enrichment") is True

    def test_unknown_analysis(self) -> None:
        assert is_enrichment_analysis("custom-analysis") is False

    def test_empty_string(self) -> None:
        assert is_enrichment_analysis("") is False

    def test_case_sensitive(self) -> None:
        """WDK analysis names are case-sensitive."""
        assert is_enrichment_analysis("GO-ENRICHMENT") is False
        assert is_enrichment_analysis("Go-Enrichment") is False


# ===========================================================================
# infer_enrichment_type
# ===========================================================================


class TestInferEnrichmentType:
    """Infer enrichment type from WDK analysis name and params."""

    def test_pathway(self) -> None:
        assert infer_enrichment_type("pathway-enrichment", {}, {}) == "pathway"

    def test_word(self) -> None:
        assert infer_enrichment_type("word-enrichment", {}, {}) == "word"

    def test_go_biological_process(self) -> None:
        result = infer_enrichment_type(
            "go-enrichment",
            {"goAssociationsOntologies": "Biological Process"},
            {},
        )
        assert result == "go_process"

    def test_go_molecular_function(self) -> None:
        result = infer_enrichment_type(
            "go-enrichment",
            {"goAssociationsOntologies": "Molecular Function"},
            {},
        )
        assert result == "go_function"

    def test_go_cellular_component(self) -> None:
        result = infer_enrichment_type(
            "go-enrichment",
            {"goAssociationsOntologies": "Cellular Component"},
            {},
        )
        assert result == "go_component"

    def test_go_defaults_to_process(self) -> None:
        """If GO ontology can't be determined, default to go_process."""
        result = infer_enrichment_type("go-enrichment", {}, {})
        assert result == "go_process"

    def test_go_ontology_from_result(self) -> None:
        """If params don't have ontology, check result goOntologies field."""
        result = infer_enrichment_type(
            "go-enrichment",
            {},
            {"goOntologies": ["Molecular Function"]},
        )
        assert result == "go_function"

    def test_go_param_takes_priority_over_result(self) -> None:
        """Parameter ontology takes priority over result ontology."""
        result = infer_enrichment_type(
            "go-enrichment",
            {"goAssociationsOntologies": "Biological Process"},
            {"goOntologies": ["Molecular Function"]},
        )
        assert result == "go_process"


# ===========================================================================
# _extract_analysis_rows
# ===========================================================================


class TestExtractAnalysisRows:
    """Extract tabular rows from various WDK analysis result formats."""

    def test_result_data_key(self) -> None:
        result = {"resultData": [{"goId": "GO:0001"}]}
        rows = _extract_analysis_rows(result)
        assert len(rows) == 1

    def test_rows_key(self) -> None:
        result = {"rows": [{"word": "kinase"}]}
        rows = _extract_analysis_rows(result)
        assert len(rows) == 1

    def test_data_key(self) -> None:
        result = {"data": [{"id": "KEGG:001"}]}
        rows = _extract_analysis_rows(result)
        assert len(rows) == 1

    def test_results_key(self) -> None:
        result = {"results": [{"term": "GO:0001"}]}
        rows = _extract_analysis_rows(result)
        assert len(rows) == 1

    def test_empty_result(self) -> None:
        rows = _extract_analysis_rows({})
        assert rows == []

    def test_non_dict_result(self) -> None:
        rows = _extract_analysis_rows("not a dict")
        assert rows == []

    def test_none_result(self) -> None:
        rows = _extract_analysis_rows(None)
        assert rows == []

    def test_filters_non_dict_rows(self) -> None:
        result = {"resultData": [{"goId": "GO:0001"}, "not_a_dict", 42, None]}
        rows = _extract_analysis_rows(result)
        assert len(rows) == 1

    def test_empty_result_data(self) -> None:
        result = {"resultData": []}
        rows = _extract_analysis_rows(result)
        assert rows == []


# ===========================================================================
# _parse_result_genes_html
# ===========================================================================


class TestParseResultGenesHtml:
    """Parse gene count and IDs from WDK enrichment HTML links."""

    def test_standard_go_enrichment_link(self) -> None:
        html = (
            "<a href='showQuestion.do?questionFullName=InternalQuestions."
            "GenesByLocusTag&param.ds_gene_ids.idList=PF3D7_0100100,"
            "PF3D7_0200200&autoRun=1'>2</a>"
        )
        count, genes = _parse_result_genes_html(html)
        assert count == 2
        assert genes == ["PF3D7_0100100", "PF3D7_0200200"]

    def test_single_gene(self) -> None:
        html = "<a href='...?param.ds_gene_ids.idList=PF3D7_0100100&autoRun=1'>1</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 1
        assert genes == ["PF3D7_0100100"]

    def test_no_genes_in_link(self) -> None:
        html = "<a href='noparams'>5</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 5
        assert genes == []

    def test_empty_html(self) -> None:
        count, genes = _parse_result_genes_html("")
        assert count == 0
        assert genes == []

    def test_plain_number(self) -> None:
        """If the HTML is just a number without tags, no match."""
        count, genes = _parse_result_genes_html("42")
        assert count == 0
        assert genes == []


# ===========================================================================
# _parse_enrichment_terms
# ===========================================================================


class TestParseEnrichmentTerms:
    """Parse enrichment result rows into structured terms."""

    def test_go_enrichment_row(self) -> None:
        """Standard GO enrichment result row."""
        rows = [
            {
                "goId": "GO:0006412",
                "goTerm": "translation",
                "resultGenes": "<a href='...?param.ds_gene_ids.idList=G1,G2'>2</a>",
                "bgdGenes": 500,
                "foldEnrich": 2.5,
                "pValue": 0.001,
                "benjamini": 0.01,
                "bonferroni": 0.05,
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.term_id == "GO:0006412"
        assert t.term_name == "translation"
        assert t.gene_count == 2
        assert t.genes == ["G1", "G2"]
        assert t.background_count == 500
        assert t.fold_enrichment == 2.5
        assert t.p_value == 0.001

    def test_pathway_enrichment_row(self) -> None:
        rows = [
            {
                "pathwayId": "KEGG:001",
                "pathwayName": "Glycolysis",
                "ResultCount": 10,
                "bgdCount": 1000,
                "foldEnrichment": 3.0,
                "PValue": 0.0001,
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.term_id == "KEGG:001"
        assert t.term_name == "Glycolysis"
        assert t.gene_count == 10

    def test_word_enrichment_row(self) -> None:
        rows = [
            {
                "word": "kinase",
                "descrip": "protein kinase activity",
                "ResultCount": 50,
                "bgdCount": 5000,
                "foldEnrich": 1.8,
                "PValue": 0.05,
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.term_id == "kinase"
        assert t.term_name == "protein kinase activity"
        assert t.gene_count == 50

    def test_empty_rows(self) -> None:
        terms = _parse_enrichment_terms([])
        assert terms == []

    def test_non_dict_rows_skipped(self) -> None:
        terms = _parse_enrichment_terms(["not_a_dict", 42])
        assert terms == []

    def test_row_with_result_id_list(self) -> None:
        """Gene IDs provided as comma-separated string."""
        rows = [
            {
                "ID": "GO:001",
                "Description": "test",
                "ResultCount": 3,
                "ResultIDList": "G1, G2, G3",
                "PValue": 0.01,
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert terms[0].genes == ["G1", "G2", "G3"]

    def test_row_with_genes_list(self) -> None:
        """Gene IDs provided as a list."""
        rows = [
            {
                "ID": "GO:001",
                "Description": "test",
                "ResultCount": 2,
                "genes": ["G1", "G2"],
                "PValue": 0.01,
            }
        ]
        terms = _parse_enrichment_terms(rows)
        assert terms[0].genes == ["G1", "G2"]

    def test_missing_optional_fields_have_defaults(self) -> None:
        """Rows with minimal fields should still parse without errors."""
        rows = [{"ID": "GO:001"}]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.term_id == "GO:001"
        assert t.term_name == ""
        assert t.gene_count == 0
        assert t.p_value == 1.0  # default
        assert t.fdr == 1.0
        assert t.bonferroni == 1.0


# ===========================================================================
# _extract_default_params
# ===========================================================================


class TestExtractDefaultParams:
    """Extract default parameter values from WDK form metadata."""

    def test_standard_form_metadata(self) -> None:
        form_meta = {
            "searchData": {
                "parameters": [
                    {
                        "name": "organism",
                        "initialDisplayValue": "Plasmodium falciparum 3D7",
                        "type": "single-pick-vocabulary",
                    },
                    {
                        "name": "pValueCutoff",
                        "initialDisplayValue": "0.05",
                        "type": "number",
                    },
                ],
            },
        }
        defaults = _extract_default_params(form_meta)
        # Vocab param should be JSON array encoded
        assert defaults["organism"] == '["Plasmodium falciparum 3D7"]'
        # Number param should be plain string
        assert defaults["pValueCutoff"] == "0.05"

    def test_empty_form_metadata(self) -> None:
        defaults = _extract_default_params({})
        assert defaults == {}

    def test_none_form_metadata(self) -> None:
        defaults = _extract_default_params(None)
        assert defaults == {}

    def test_param_with_none_default_skipped(self) -> None:
        form_meta = {
            "searchData": {
                "parameters": [
                    {
                        "name": "optional_param",
                        "initialDisplayValue": None,
                        "type": "string",
                    },
                ],
            },
        }
        defaults = _extract_default_params(form_meta)
        assert "optional_param" not in defaults

    def test_param_with_empty_name_skipped(self) -> None:
        form_meta = {
            "searchData": {
                "parameters": [
                    {"name": "", "initialDisplayValue": "value", "type": "string"},
                ],
            },
        }
        defaults = _extract_default_params(form_meta)
        assert defaults == {}


# ===========================================================================
# _encode_vocab_value
# ===========================================================================


class TestEncodeVocabValue:
    """Ensure vocabulary params are JSON array strings."""

    def test_plain_string_wrapped(self) -> None:
        assert (
            _encode_vocab_value("Plasmodium falciparum") == '["Plasmodium falciparum"]'
        )

    def test_already_json_array_passes_through(self) -> None:
        already = '["Plasmodium falciparum"]'
        assert _encode_vocab_value(already) == already

    def test_empty_string_wrapped(self) -> None:
        assert _encode_vocab_value("") == '[""]'

    def test_string_starting_with_bracket_but_not_json(self) -> None:
        """A string starting with '[' that is not valid JSON gets wrapped.

        The function attempts ``json.loads`` and, on failure, falls through
        to wrapping the raw string as ``json.dumps([value])`` so WDK always
        receives a valid JSON array.
        """
        val = "[not valid json"
        assert _encode_vocab_value(val) == '["[not valid json"]'


# ===========================================================================
# encode_vocab_params
# ===========================================================================


class TestEncodeVocabParams:
    """Vocabulary param encoding with form metadata."""

    def test_vocab_params_encoded(self) -> None:
        form_meta = {
            "searchData": {
                "parameters": [
                    {"name": "organism", "type": "single-pick-vocabulary"},
                    {"name": "threshold", "type": "number"},
                ],
            },
        }
        params = {"organism": "Pf3D7", "threshold": "0.05"}
        result = encode_vocab_params(params, form_meta)
        assert result["organism"] == '["Pf3D7"]'
        assert result["threshold"] == "0.05"

    def test_multi_pick_vocab_encoded(self) -> None:
        form_meta = {
            "searchData": {
                "parameters": [
                    {"name": "codes", "type": "multi-pick-vocabulary"},
                ],
            },
        }
        params = {"codes": "IDA"}
        result = encode_vocab_params(params, form_meta)
        assert result["codes"] == '["IDA"]'

    def test_already_encoded_vocab_passes_through(self) -> None:
        form_meta = {
            "searchData": {
                "parameters": [
                    {"name": "organism", "type": "single-pick-vocabulary"},
                ],
            },
        }
        params = {"organism": '["Pf3D7"]'}
        result = encode_vocab_params(params, form_meta)
        assert result["organism"] == '["Pf3D7"]'

    def test_no_form_metadata_returns_params_unchanged(self) -> None:
        params = {"organism": "Pf3D7"}
        result = encode_vocab_params(params, None)
        assert result == params

    def test_non_string_value_not_encoded(self) -> None:
        """Only string values get vocabulary encoding."""
        form_meta = {
            "searchData": {
                "parameters": [
                    {"name": "organism", "type": "single-pick-vocabulary"},
                ],
            },
        }
        params = {"organism": ["Pf3D7"]}
        result = encode_vocab_params(params, form_meta)
        # List is not a string, so no encoding applied
        assert result["organism"] == ["Pf3D7"]


# ===========================================================================
# upsert_enrichment_result
# ===========================================================================


class TestUpsertEnrichmentResult:
    """Replace or append enrichment results by analysis type."""

    def test_append_new_type(self) -> None:
        results: list[EnrichmentResult] = []
        new = EnrichmentResult(
            analysis_type="go_process",
            terms=[],
            total_genes_analyzed=100,
            background_size=5000,
        )
        upsert_enrichment_result(results, new)
        assert len(results) == 1

    def test_replace_existing_type(self) -> None:
        old = EnrichmentResult(
            analysis_type="go_process",
            terms=[],
            total_genes_analyzed=100,
            background_size=5000,
        )
        results = [old]
        new = EnrichmentResult(
            analysis_type="go_process",
            terms=[
                EnrichmentTerm(
                    term_id="GO:001",
                    term_name="test",
                    gene_count=5,
                    background_count=500,
                    fold_enrichment=2.0,
                    odds_ratio=0.0,
                    p_value=0.01,
                    fdr=0.05,
                    bonferroni=0.1,
                    genes=[],
                )
            ],
            total_genes_analyzed=200,
            background_size=5000,
        )
        upsert_enrichment_result(results, new)
        assert len(results) == 1
        assert results[0].total_genes_analyzed == 200
        assert len(results[0].terms) == 1

    def test_does_not_replace_different_type(self) -> None:
        old = EnrichmentResult(
            analysis_type="go_process",
            terms=[],
            total_genes_analyzed=100,
            background_size=5000,
        )
        results = [old]
        new = EnrichmentResult(
            analysis_type="pathway",
            terms=[],
            total_genes_analyzed=50,
            background_size=3000,
        )
        upsert_enrichment_result(results, new)
        assert len(results) == 2


# ===========================================================================
# parse_enrichment_from_raw
# ===========================================================================


class TestParseEnrichmentFromRaw:
    """Parse raw WDK analysis result into structured EnrichmentResult."""

    def test_go_enrichment_with_results(self) -> None:
        result = {
            "resultSize": 100,
            "backgroundSize": 5000,
            "resultData": [
                {
                    "goId": "GO:0006412",
                    "goTerm": "translation",
                    "resultGenes": "<a href='...?param.ds_gene_ids.idList=G1,G2'>2</a>",
                    "bgdGenes": 500,
                    "foldEnrich": 2.5,
                    "pValue": 0.001,
                    "benjamini": 0.01,
                    "bonferroni": 0.05,
                },
            ],
        }
        er = parse_enrichment_from_raw(
            "go-enrichment",
            {"goAssociationsOntologies": "Biological Process"},
            result,
        )
        assert er.analysis_type == "go_process"
        assert er.total_genes_analyzed == 100
        assert er.background_size == 5000
        assert len(er.terms) == 1
        assert er.terms[0].term_id == "GO:0006412"

    def test_empty_result(self) -> None:
        result = {"resultSize": 0, "backgroundSize": 0, "resultData": []}
        er = parse_enrichment_from_raw("go-enrichment", {}, result)
        assert er.terms == []
        assert er.total_genes_analyzed == 0

    def test_non_dict_result(self) -> None:
        er = parse_enrichment_from_raw("go-enrichment", {}, "not_a_dict")
        assert er.terms == []
        assert er.total_genes_analyzed == 0
        assert er.background_size == 0

    def test_alternative_size_field_names(self) -> None:
        """Some WDK deployments use different field names for sizes."""
        result = {
            "totalResults": 150,
            "bgdSize": 6000,
            "resultData": [],
        }
        er = parse_enrichment_from_raw("pathway-enrichment", {}, result)
        assert er.total_genes_analyzed == 150
        assert er.background_size == 6000

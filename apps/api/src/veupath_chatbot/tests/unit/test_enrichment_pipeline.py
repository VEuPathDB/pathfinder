"""Bug-hunting tests for enrichment.py — edge cases, empty inputs, type confusion.

Focuses on areas the existing test_enrichment.py does NOT cover:
- Empty / malformed result payloads
- parse_enrichment_from_raw with non-dict results
- _parse_enrichment_terms with mixed missing fields
- _parse_result_genes_html with pathological inputs
- infer_enrichment_type with unexpected combo of params & result
- _encode_vocab_value edge cases
- upsert_enrichment_result mutation ordering
"""

from __future__ import annotations

from veupath_chatbot.services.experiment.enrichment import (
    _encode_vocab_value,
    _extract_analysis_rows,
    _extract_default_params,
    _parse_enrichment_terms,
    _parse_result_genes_html,
    infer_enrichment_type,
    parse_enrichment_from_raw,
    upsert_enrichment_result,
)
from veupath_chatbot.services.experiment.types import EnrichmentResult


class TestParseResultGenesHtmlEdgeCases:
    """Edge cases for the HTML-link gene extraction regex."""

    def test_multiple_links_takes_first_count(self) -> None:
        """If WDK returns multiple <a> tags, the regex picks the first match."""
        html = "<a href='?idList=G1&x'>5</a> more text <a href='?idList=G2&x'>3</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 5
        assert genes == ["G1"]

    def test_count_zero_in_link(self) -> None:
        html = "<a href='?idList=&autoRun=1'>0</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 0
        assert genes == []

    def test_genes_with_whitespace(self) -> None:
        """Gene IDs with surrounding whitespace should be stripped."""
        html = "<a href='?idList= G1 , G2 ,&autoRun=1'>2</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 2
        assert genes == ["G1", "G2"]

    def test_single_gene_no_comma(self) -> None:
        html = "<a href='?idList=PF3D7_0100100&autoRun=1'>1</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 1
        assert genes == ["PF3D7_0100100"]

    def test_malformed_html_no_href(self) -> None:
        html = "<span>42</span>"
        count, genes = _parse_result_genes_html(html)
        assert count == 42
        assert genes == []

    def test_idlist_with_special_chars_in_gene_ids(self) -> None:
        """Gene IDs can contain dots, underscores, etc."""
        html = "<a href='?idList=TGME49_123.1,TGGT1_456.2&autoRun=1'>2</a>"
        count, genes = _parse_result_genes_html(html)
        assert count == 2
        assert genes == ["TGME49_123.1", "TGGT1_456.2"]


class TestParseEnrichmentTermsEdgeCases:
    """Edge cases for _parse_enrichment_terms not covered elsewhere."""

    def test_all_fields_missing_produces_defaults(self) -> None:
        """A row with no recognized keys still produces a term with defaults."""
        rows = [{"unknownField": "value"}]
        terms = _parse_enrichment_terms(rows)
        assert len(terms) == 1
        t = terms[0]
        assert t.term_id == ""
        assert t.term_name == ""
        assert t.gene_count == 0
        assert t.background_count == 0
        assert t.fold_enrichment == 0.0
        assert t.odds_ratio == 0.0
        assert t.p_value == 1.0  # default for pValue
        assert t.fdr == 1.0  # default for BenjaminiHochberg
        assert t.bonferroni == 1.0  # default for Bonferroni
        assert t.genes == []

    def test_result_count_as_string(self) -> None:
        """ResultCount can be a string from some WDK plugins."""
        rows = [{"ID": "T1", "ResultCount": "42"}]
        terms = _parse_enrichment_terms(rows)
        assert terms[0].gene_count == 42

    def test_result_genes_numeric_string_no_html(self) -> None:
        """resultGenes as a numeric string (no HTML) goes through safe_int.

        BUG NOTE: If resultGenes is a non-numeric string like "gene1",
        safe_int returns 0, which silently loses the gene count. This is
        an acceptable edge case since WDK always returns either HTML or
        a number for resultGenes.
        """
        rows = [{"ID": "T1", "resultGenes": "15"}]
        terms = _parse_enrichment_terms(rows)
        assert terms[0].gene_count == 15

    def test_result_genes_plain_text_no_html_returns_zero(self) -> None:
        """resultGenes as a plain non-numeric string returns gene_count=0.

        This is a known edge case: if resultGenes is a gene ID string
        rather than HTML or a number, safe_int falls back to 0.
        """
        rows = [{"ID": "T1", "resultGenes": "not_a_number"}]
        terms = _parse_enrichment_terms(rows)
        assert terms[0].gene_count == 0

    def test_genes_from_list_field(self) -> None:
        """Gene list from explicit 'genes' field as a list of objects."""
        rows = [{"ID": "T1", "genes": [123, "G2", None]}]
        terms = _parse_enrichment_terms(rows)
        # None entries are filtered because list comprehension checks `g is not None`
        # Wait — the code does [str(g) for g in genes_raw] with isinstance check
        # Actually for list: genes = [str(g) for g in genes_raw]
        assert "123" in terms[0].genes
        assert "G2" in terms[0].genes
        # None gets str()-ified to "None"
        assert "None" in terms[0].genes

    def test_genes_from_comma_separated_string(self) -> None:
        """Gene list from 'ResultIDList' as comma-separated string."""
        rows = [{"ID": "T1", "ResultIDList": "G1, G2, G3"}]
        terms = _parse_enrichment_terms(rows)
        assert terms[0].genes == ["G1", "G2", "G3"]

    def test_genes_from_empty_string(self) -> None:
        """Empty ResultIDList string produces no genes."""
        rows = [{"ID": "T1", "ResultIDList": ""}]
        terms = _parse_enrichment_terms(rows)
        assert terms[0].genes == []

    def test_nan_pvalue_handled(self) -> None:
        """NaN in p-value defaults to 1.0 (not significant).

        When WDK returns "NaN" for pValue, safe_float detects the non-finite
        value and falls back to default=1.0.  This is correct because NaN
        means "not computed", which should be treated as not significant.
        """
        rows = [{"ID": "T1", "pValue": "NaN"}]
        terms = _parse_enrichment_terms(rows)
        assert terms[0].p_value == 1.0

    def test_negative_infinity_fold_enrichment(self) -> None:
        """-Infinity in fold enrichment should be replaced by default (0.0)."""
        rows = [{"ID": "T1", "foldEnrich": "-Infinity"}]
        terms = _parse_enrichment_terms(rows)
        assert terms[0].fold_enrichment == 0.0


class TestParseEnrichmentFromRawEdgeCases:
    """parse_enrichment_from_raw with edge-case inputs."""

    def test_non_dict_result(self) -> None:
        """When result is not a dict (e.g. list or None), total/bg should be 0."""
        er = parse_enrichment_from_raw("go-enrichment", {}, None)
        assert er.total_genes_analyzed == 0
        assert er.background_size == 0
        assert er.terms == []

    def test_result_as_list(self) -> None:
        """A list result produces no terms and zero totals."""
        er = parse_enrichment_from_raw("go-enrichment", {}, [{"goId": "GO:1"}])
        assert er.total_genes_analyzed == 0
        assert er.background_size == 0
        assert er.terms == []

    def test_empty_dict_result(self) -> None:
        """Empty dict result: no rows, no totals."""
        er = parse_enrichment_from_raw("pathway-enrichment", {}, {})
        assert er.analysis_type == "pathway"
        assert er.terms == []
        assert er.total_genes_analyzed == 0
        assert er.background_size == 0

    def test_alternative_total_keys(self) -> None:
        """Uses 'resultSize' first, falls back to 'totalResults'."""
        er = parse_enrichment_from_raw(
            "pathway-enrichment",
            {},
            {"totalResults": 42, "bgdSize": 1000, "resultData": []},
        )
        assert er.total_genes_analyzed == 42
        assert er.background_size == 1000

    def test_result_size_takes_precedence(self) -> None:
        """'resultSize' takes precedence over 'totalResults'."""
        er = parse_enrichment_from_raw(
            "pathway-enrichment",
            {},
            {"resultSize": 99, "totalResults": 42, "resultData": []},
        )
        assert er.total_genes_analyzed == 99


class TestInferEnrichmentTypeEdgeCases:
    """infer_enrichment_type with unusual parameter combos."""

    def test_go_enrichment_with_json_array_ontology(self) -> None:
        """WDK vocab params arrive as JSON array strings like '["Molecular Function"]'.

        The code unwraps the JSON array to extract the ontology name so it
        matches _REVERSE_GO_ONTOLOGY correctly.
        """
        result = infer_enrichment_type(
            "go-enrichment",
            {"goAssociationsOntologies": '["Molecular Function"]'},
            {},
        )
        assert result == "go_function"

    def test_go_enrichment_prefers_params_over_result(self) -> None:
        """When params has ontology, result ontology is ignored."""
        result = infer_enrichment_type(
            "go-enrichment",
            {"goAssociationsOntologies": "Cellular Component"},
            {"goOntologies": ["Molecular Function"]},
        )
        assert result == "go_component"

    def test_go_enrichment_result_ontologies_empty_list(self) -> None:
        """Empty goOntologies list falls back to go_process."""
        result = infer_enrichment_type(
            "go-enrichment",
            {},
            {"goOntologies": []},
        )
        assert result == "go_process"

    def test_unknown_wdk_analysis_name(self) -> None:
        """Unknown analysis name falls back to go_process (via _REVERSE_GO_ONTOLOGY)."""
        result = infer_enrichment_type("unknown-analysis", {}, {})
        # Not in _WDK_TO_ANALYSIS_TYPE, not in _REVERSE_GO_ONTOLOGY
        assert result == "go_process"


class TestEncodeVocabValue:
    """_encode_vocab_value wraps plain strings as JSON arrays."""

    def test_wraps_plain_string(self) -> None:
        assert _encode_vocab_value("hello") == '["hello"]'

    def test_does_not_double_wrap_array(self) -> None:
        assert _encode_vocab_value('["hello"]') == '["hello"]'

    def test_empty_string(self) -> None:
        assert _encode_vocab_value("") == '[""]'

    def test_string_starting_with_bracket_but_not_json(self) -> None:
        """A string starting with '[' but not valid JSON is wrapped as a JSON array.

        The code validates JSON before returning as-is; invalid JSON is
        wrapped in an array like any other plain string.
        """
        result = _encode_vocab_value("[not json")
        assert result == '["[not json"]'


class TestExtractAnalysisRowsEdgeCases:
    """Additional _extract_analysis_rows edge cases."""

    def test_results_key_fallback(self) -> None:
        """Falls back to 'results' key when others are absent."""
        result = {"results": [{"id": "1"}, {"id": "2"}]}
        rows = _extract_analysis_rows(result)
        assert len(rows) == 2

    def test_non_list_rows_returns_empty(self) -> None:
        """When resultData is not a list, returns empty."""
        result = {"resultData": "not a list"}
        rows = _extract_analysis_rows(result)
        assert rows == []

    def test_string_input(self) -> None:
        assert _extract_analysis_rows("string") == []

    def test_integer_input(self) -> None:
        assert _extract_analysis_rows(42) == []


class TestExtractDefaultParamsEdgeCases:
    """Additional _extract_default_params edge cases."""

    def test_searchdata_wrapper(self) -> None:
        """WDK wraps analysis form data under 'searchData'."""
        form = {
            "searchData": {
                "parameters": [
                    {"name": "pValueCutoff", "initialDisplayValue": "0.05"},
                ]
            }
        }
        result = _extract_default_params(form)
        assert result == {"pValueCutoff": "0.05"}

    def test_numeric_initial_display_value(self) -> None:
        """initialDisplayValue as a number is converted to string."""
        form = {
            "parameters": [
                {"name": "cutoff", "initialDisplayValue": 0.05},
            ]
        }
        result = _extract_default_params(form)
        assert result["cutoff"] == "0.05"

    def test_boolean_initial_display_value(self) -> None:
        """initialDisplayValue as a boolean is converted to string."""
        form = {
            "parameters": [
                {"name": "flag", "initialDisplayValue": True},
            ]
        }
        result = _extract_default_params(form)
        assert result["flag"] == "True"


class TestUpsertEnrichmentResultEdgeCases:
    """Edge cases for upsert_enrichment_result mutation."""

    def test_upsert_into_empty_list(self) -> None:
        results: list[EnrichmentResult] = []
        new = EnrichmentResult(
            analysis_type="word", terms=[], total_genes_analyzed=5, background_size=0
        )
        upsert_enrichment_result(results, new)
        assert len(results) == 1
        assert results[0] is new

    def test_upsert_replaces_correct_index(self) -> None:
        """When there are multiple types, only the matching one is replaced."""
        r1 = EnrichmentResult(
            analysis_type="go_process",
            terms=[],
            total_genes_analyzed=1,
            background_size=0,
        )
        r2 = EnrichmentResult(
            analysis_type="pathway", terms=[], total_genes_analyzed=2, background_size=0
        )
        r3 = EnrichmentResult(
            analysis_type="word", terms=[], total_genes_analyzed=3, background_size=0
        )
        results = [r1, r2, r3]

        new_pathway = EnrichmentResult(
            analysis_type="pathway",
            terms=[],
            total_genes_analyzed=99,
            background_size=0,
        )
        upsert_enrichment_result(results, new_pathway)

        assert len(results) == 3
        assert results[0].total_genes_analyzed == 1  # unchanged
        assert results[1].total_genes_analyzed == 99  # replaced
        assert results[2].total_genes_analyzed == 3  # unchanged

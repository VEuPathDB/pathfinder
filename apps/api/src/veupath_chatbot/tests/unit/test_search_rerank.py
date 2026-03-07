"""Tests for search reranking utilities."""

from __future__ import annotations

from veupath_chatbot.services.search_rerank import (
    ScoredResult,
    _build_wildcard_ids,
    _default_organism_scorer,
    analyse_query,
    dedup_and_sort,
    score_field_quality,
    score_text_match,
)

# ---------------------------------------------------------------------------
# score_text_match
# ---------------------------------------------------------------------------


class TestScoreTextMatch:
    def test_exact_match(self) -> None:
        assert score_text_match("PF3D7_1234500", "PF3D7_1234500") == 1.0

    def test_prefix_match(self) -> None:
        score = score_text_match("PF3D7", "PF3D7_1234500")
        assert score == 0.95

    def test_substring_match(self) -> None:
        score = score_text_match("1234", "PF3D7_1234500")
        assert score == 0.80

    def test_empty_query(self) -> None:
        assert score_text_match("", "something") == 0.0

    def test_empty_value(self) -> None:
        assert score_text_match("query", "") == 0.0

    def test_case_insensitive(self) -> None:
        assert score_text_match("pf3d7", "PF3D7") == 1.0

    def test_fuzzy_match(self) -> None:
        score = score_text_match("malaira", "malaria")
        assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# score_field_quality
# ---------------------------------------------------------------------------


class TestScoreFieldQuality:
    def test_primary_field_gives_1(self) -> None:
        assert score_field_quality(["gene_source_id"]) == 1.0

    def test_secondary_field_gives_negative(self) -> None:
        assert score_field_quality(["gene_Notes"]) == -0.5

    def test_unknown_field_gives_zero(self) -> None:
        assert score_field_quality(["some_other_field"]) == 0.0

    def test_empty_gives_zero(self) -> None:
        assert score_field_quality([]) == 0.0

    def test_primary_takes_priority(self) -> None:
        # If both primary and secondary fields match, primary wins
        assert score_field_quality(["gene_Notes", "gene_source_id"]) == 1.0


# ---------------------------------------------------------------------------
# ScoredResult & dedup_and_sort
# ---------------------------------------------------------------------------


class TestDedupAndSort:
    def test_deduplicates_keeping_highest(self) -> None:
        results = [
            ScoredResult(result={"id": "a"}, score=0.5, source="s1"),
            ScoredResult(result={"id": "a"}, score=0.9, source="s2"),
            ScoredResult(result={"id": "b"}, score=0.7, source="s1"),
        ]
        deduped = dedup_and_sort(results, key_fn=lambda r: str(r.get("id", "")))
        assert len(deduped) == 2
        # Highest score first
        assert deduped[0].score == 0.9
        assert deduped[1].score == 0.7

    def test_sorts_by_descending_score(self) -> None:
        results = [
            ScoredResult(result={"id": "a"}, score=0.3),
            ScoredResult(result={"id": "b"}, score=0.9),
            ScoredResult(result={"id": "c"}, score=0.6),
        ]
        deduped = dedup_and_sort(results, key_fn=lambda r: str(r.get("id", "")))
        scores = [sr.score for sr in deduped]
        assert scores == [0.9, 0.6, 0.3]

    def test_skips_empty_keys(self) -> None:
        results = [
            ScoredResult(result={"id": ""}, score=0.5),
            ScoredResult(result={"id": "a"}, score=0.5),
        ]
        deduped = dedup_and_sort(results, key_fn=lambda r: str(r.get("id", "")))
        assert len(deduped) == 1
        assert deduped[0].result["id"] == "a"

    def test_empty_input(self) -> None:
        assert dedup_and_sort([], key_fn=lambda r: str(r.get("id", ""))) == []


# ---------------------------------------------------------------------------
# _build_wildcard_ids
# ---------------------------------------------------------------------------


class TestBuildWildcardIds:
    def test_empty_query(self) -> None:
        assert _build_wildcard_ids("") == ()

    def test_query_with_underscore(self) -> None:
        result = _build_wildcard_ids("PF3D7_123")
        assert result == ("PF3D7_123*",)

    def test_query_without_underscore(self) -> None:
        result = _build_wildcard_ids("pfal")
        # Should produce PFAL_*, PFAL*, pfal*
        assert "PFAL_*" in result
        assert "PFAL*" in result
        assert "pfal*" in result

    def test_already_uppercase(self) -> None:
        result = _build_wildcard_ids("PFAL")
        assert "PFAL_*" in result
        assert "PFAL*" in result
        # No duplicate for lowercase since upper == q
        assert len(result) == 2

    def test_no_duplicates(self) -> None:
        result = _build_wildcard_ids("abc")
        assert len(result) == len(set(result))


# ---------------------------------------------------------------------------
# analyse_query
# ---------------------------------------------------------------------------


class TestAnalyseQuery:
    def test_empty_query(self) -> None:
        intent = analyse_query("", [])
        assert intent.raw == ""
        assert intent.is_gene_id_like is False

    def test_gene_id_like(self) -> None:
        intent = analyse_query("PF3D7_1234", ["Plasmodium falciparum 3D7"])
        assert intent.is_gene_id_like is True
        assert len(intent.wildcard_ids) > 0

    def test_non_gene_id(self) -> None:
        intent = analyse_query("malaria treatment", [])
        assert intent.is_gene_id_like is False
        assert intent.wildcard_ids == ()

    def test_organism_detection(self) -> None:
        orgs = ["Plasmodium falciparum 3D7", "Toxoplasma gondii ME49"]
        intent = analyse_query("Plasmodium falciparum", orgs)
        assert intent.implied_organism is not None
        assert "falciparum" in intent.implied_organism.lower()
        assert intent.implied_organism_score > 0.6

    def test_no_organism_match_below_threshold(self) -> None:
        orgs = ["Plasmodium falciparum 3D7"]
        intent = analyse_query("xyz unrelated", orgs)
        assert intent.implied_organism is None
        assert intent.implied_organism_score == 0.0


# ---------------------------------------------------------------------------
# _default_organism_scorer
# ---------------------------------------------------------------------------


class TestDefaultOrganismScorer:
    def test_exact_match(self) -> None:
        assert _default_organism_scorer("abc", "abc") == 1.0

    def test_substring_match(self) -> None:
        assert (
            _default_organism_scorer("falciparum", "Plasmodium falciparum 3D7") == 0.7
        )

    def test_no_match(self) -> None:
        assert _default_organism_scorer("xyz", "abc") == 0.0

"""Unit tests for services.wdk.record_types.resolve_record_type."""

from veupath_chatbot.services.wdk.record_types import resolve_record_type

# -- Exact match (urlSegment / plain string) --------------------------------


class TestExactMatch:
    def test_plain_string_exact(self) -> None:
        result = resolve_record_type(["gene", "transcript"], "gene")
        assert result == "gene"

    def test_dict_url_segment_exact(self) -> None:
        available = [{"urlSegment": "gene", "name": "Gene", "displayName": "Genes"}]
        assert resolve_record_type(available, "gene") == "gene"

    def test_dict_name_field_exact(self) -> None:
        """When urlSegment is absent, falls back to 'name' via wdk_entity_name."""
        available = [{"name": "Gene"}]
        assert resolve_record_type(available, "Gene") == "Gene"


# -- Case-insensitive matching ----------------------------------------------


class TestCaseInsensitive:
    def test_uppercase_input(self) -> None:
        result = resolve_record_type(["gene", "transcript"], "GENE")
        assert result == "gene"

    def test_mixed_case_input(self) -> None:
        result = resolve_record_type(["gene"], "GeNe")
        assert result == "gene"

    def test_dict_case_insensitive(self) -> None:
        available = [{"urlSegment": "gene", "name": "Gene", "displayName": "Genes"}]
        assert resolve_record_type(available, "GENE") == "gene"


# -- Whitespace trimming ---------------------------------------------------


class TestWhitespace:
    def test_leading_trailing_whitespace(self) -> None:
        result = resolve_record_type(["gene"], "  gene  ")
        assert result == "gene"

    def test_whitespace_only_input_no_match(self) -> None:
        result = resolve_record_type(["gene"], "   ")
        assert result is None


# -- Display name matching -------------------------------------------------


class TestDisplayName:
    def test_single_display_name_match(self) -> None:
        available = [
            {"urlSegment": "gene", "name": "Gene", "displayName": "Genes"},
            {"urlSegment": "transcript", "name": "Transcript", "displayName": "EST"},
        ]
        assert resolve_record_type(available, "Genes") == "gene"

    def test_ambiguous_display_name_returns_none(self) -> None:
        """Multiple record types with same displayName -> no match."""
        available = [
            {"urlSegment": "gene", "name": "Gene", "displayName": "Records"},
            {
                "urlSegment": "transcript",
                "name": "Transcript",
                "displayName": "Records",
            },
        ]
        assert resolve_record_type(available, "Records") is None

    def test_display_name_case_insensitive(self) -> None:
        available = [{"urlSegment": "gene", "name": "Gene", "displayName": "Genes"}]
        assert resolve_record_type(available, "genes") == "gene"


# -- Name field strategy 2 -------------------------------------------------


class TestNameFieldMatch:
    def test_match_by_name_when_url_segment_differs(self) -> None:
        """Strategy 2: match raw 'name' field when urlSegment doesn't match."""
        available = [
            {"urlSegment": "gene", "name": "GeneRecord", "displayName": "Genes"}
        ]
        # "GeneRecord" doesn't match urlSegment ("gene"), so strategy 1 fails.
        # Strategy 2 checks the raw "name" field.
        assert resolve_record_type(available, "GeneRecord") == "gene"


# -- Plural forms / partial input ------------------------------------------


class TestPluralAndPartial:
    def test_plural_s_via_display_name(self) -> None:
        """Plural form matches when it's the displayName."""
        available = [
            {"urlSegment": "gene", "name": "Gene", "displayName": "Genes"},
        ]
        assert resolve_record_type(available, "Genes") == "gene"

    def test_partial_input_no_match(self) -> None:
        """Partial substrings do NOT match (strict equality only)."""
        result = resolve_record_type(["gene", "transcript"], "gen")
        assert result is None


# -- No match scenarios ----------------------------------------------------


class TestNoMatch:
    def test_nonexistent_type_returns_none(self) -> None:
        result = resolve_record_type(["gene", "transcript"], "nonexistent")
        assert result is None

    def test_empty_available_types(self) -> None:
        assert resolve_record_type([], "gene") is None

    def test_empty_input(self) -> None:
        assert resolve_record_type(["gene"], "") is None


# -- Edge cases: non-string/non-dict entries skipped -----------------------


class TestEdgeCases:
    def test_non_string_non_dict_entries_skipped(self) -> None:
        result = resolve_record_type([42, None, True, "gene"], "gene")  # type: ignore[list-item]
        assert result == "gene"

    def test_dict_without_url_segment_or_name(self) -> None:
        """Dict with no urlSegment/name -> wdk_entity_name returns ''."""
        available: list[dict[str, str]] = [{"displayName": "Genes"}]
        assert resolve_record_type(available, "Genes") is None

    def test_prefers_url_segment_over_name(self) -> None:
        available = [{"urlSegment": "gene", "name": "GeneInternal"}]
        assert resolve_record_type(available, "gene") == "gene"

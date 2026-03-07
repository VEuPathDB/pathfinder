"""Tests for catalog_tools.py and query_validation.py edge cases.

Covers: empty inputs, boundary conditions, tokenization edge cases,
and the CatalogTools delegation layer.
"""

from veupath_chatbot.ai.tools.query_validation import (
    VAGUE_RECORD_TYPE_TOKENS,
    record_type_query_error,
    search_query_error,
    tokenize_query,
)

# ---------------------------------------------------------------------------
# tokenize_query edge cases
# ---------------------------------------------------------------------------


class TestTokenizeQuery:
    def test_empty_string(self):
        assert tokenize_query("") == []

    def test_none_coerces_to_empty(self):
        # tokenize_query uses (text or ""), so None becomes ""
        assert tokenize_query(None) == []

    def test_single_short_token_excluded(self):
        """Tokens shorter than 3 chars should be excluded."""
        result = tokenize_query("a ab")
        # "a" is too short (1 char), "ab" is too short (2 chars)
        assert result == []

    def test_three_char_token_included(self):
        """Tokens of exactly 3 chars should be included."""
        result = tokenize_query("abc")
        assert result == ["abc"]

    def test_dots_and_dashes_preserved(self):
        """Dots and dashes within tokens should be preserved."""
        result = tokenize_query("RNA-seq 3D7")
        assert "rna-seq" in result
        assert "3d7" in result

    def test_special_chars_split_tokens(self):
        result = tokenize_query("kinase (ATP-binding)")
        assert "kinase" in result
        assert "atp-binding" in result

    def test_all_lowercase(self):
        result = tokenize_query("KINASE EXPRESSION")
        assert result == ["kinase", "expression"]

    def test_numeric_tokens(self):
        result = tokenize_query("123 456")
        assert result == ["123", "456"]


# ---------------------------------------------------------------------------
# record_type_query_error edge cases
# ---------------------------------------------------------------------------


class TestRecordTypeQueryError:
    def test_empty_string_returns_none(self):
        """Empty query is allowed (returns all record types)."""
        assert record_type_query_error("") is None

    def test_whitespace_only_returns_none(self):
        """Whitespace-only is equivalent to empty."""
        assert record_type_query_error("   ") is None

    def test_single_short_word_rejected(self):
        """A single short word yields zero valid tokens -> rejected."""
        err = record_type_query_error("ab")
        assert err is not None
        assert err["error"] == "query_too_vague"

    def test_two_specific_words_accepted(self):
        result = record_type_query_error("gametocyte RNA-seq")
        assert result is None

    def test_all_vague_tokens_rejected(self):
        """All tokens from VAGUE_RECORD_TYPE_TOKENS should be rejected."""
        vague_query = " ".join(sorted(VAGUE_RECORD_TYPE_TOKENS)[:3])
        err = record_type_query_error(vague_query)
        assert err is not None
        assert err["error"] == "query_too_vague"

    def test_mixed_vague_and_specific_accepted(self):
        """One specific token mixed with vague tokens should be accepted."""
        result = record_type_query_error("gene gametocyte")
        # "gene" is vague, "gametocyte" is specific -> accepted
        assert result is None

    def test_error_includes_examples(self):
        err = record_type_query_error("gene")
        assert err is not None
        assert "examples" in err


# ---------------------------------------------------------------------------
# search_query_error edge cases
# ---------------------------------------------------------------------------


class TestSearchQueryError:
    def test_empty_string_returns_error(self):
        err = search_query_error("")
        assert err is not None
        assert err["error"] == "query_required"

    def test_whitespace_only_returns_error(self):
        err = search_query_error("   ")
        assert err is not None
        assert err["error"] == "query_required"

    def test_single_word_rejected(self):
        err = search_query_error("ortholog")
        assert err is not None
        assert err["error"] == "query_too_vague"

    def test_two_words_accepted(self):
        assert search_query_error("vector salivary") is None

    def test_special_chars_only_rejected(self):
        """All special chars -> no valid tokens -> rejected."""
        err = search_query_error("!!@@##")
        assert err is not None

    def test_error_includes_examples(self):
        err = search_query_error("ortholog")
        assert err is not None
        assert "examples" in err

    def test_single_long_token_rejected(self):
        """Even a long single token should be rejected (needs 2+ tokens)."""
        err = search_query_error("gametocyte")
        assert err is not None
        assert err["error"] == "query_too_vague"

    def test_three_words_accepted(self):
        assert search_query_error("malaria liver stage") is None

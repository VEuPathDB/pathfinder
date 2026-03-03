"""Tests for vocab_utils shared vocabulary matching functions."""

from __future__ import annotations

import pytest

from veupath_chatbot.domain.parameters.vocab_utils import (
    match_vocab_value,
    numeric_equivalent,
)
from veupath_chatbot.platform.errors import ValidationError


class TestNumericEquivalent:
    def test_matching_integers(self) -> None:
        assert numeric_equivalent("42", "42") is True

    def test_matching_floats(self) -> None:
        assert numeric_equivalent("3.14", "3.14") is True

    def test_integer_vs_float(self) -> None:
        assert numeric_equivalent("42", "42.0") is True

    def test_non_matching(self) -> None:
        assert numeric_equivalent("1", "2") is False

    def test_none_values(self) -> None:
        assert numeric_equivalent(None, "1") is False
        assert numeric_equivalent("1", None) is False
        assert numeric_equivalent(None, None) is False

    def test_empty_strings(self) -> None:
        assert numeric_equivalent("", "1") is False

    def test_non_numeric(self) -> None:
        assert numeric_equivalent("abc", "1") is False

    def test_whitespace_handling(self) -> None:
        assert numeric_equivalent("  42  ", "42") is True


class TestMatchVocabValue:
    """Tests for the shared match_vocab_value function."""

    def test_no_vocab_returns_value_as_is(self) -> None:
        result = match_vocab_value(vocab=None, param_name="p", value="hello")
        assert result == "hello"

    def test_exact_display_match(self) -> None:
        vocab = [["val1", "Display One"], ["val2", "Display Two"]]
        result = match_vocab_value(vocab=vocab, param_name="p", value="Display One")
        assert result == "val1"

    def test_exact_value_match(self) -> None:
        vocab = [["val1", "Display One"]]
        result = match_vocab_value(vocab=vocab, param_name="p", value="val1")
        assert result == "val1"

    def test_numeric_match(self) -> None:
        vocab = [["42.0", "42"]]
        result = match_vocab_value(vocab=vocab, param_name="p", value="42")
        assert result == "42.0"

    def test_no_match_raises(self) -> None:
        vocab = [["a", "A"], ["b", "B"]]
        with pytest.raises(ValidationError, match="Invalid parameter value"):
            match_vocab_value(vocab=vocab, param_name="test_param", value="nonexistent")

    def test_tree_vocab_match(self) -> None:
        vocab = {
            "data": {"display": "Root", "term": "root_val"},
            "children": [
                {"data": {"display": "Child", "term": "child_val"}, "children": []}
            ],
        }
        result = match_vocab_value(vocab=vocab, param_name="p", value="Child")
        assert result == "child_val"

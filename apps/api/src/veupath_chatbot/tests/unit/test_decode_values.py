"""Tests for domain/parameters/_decode_values.py."""

import pytest

from veupath_chatbot.domain.parameters._decode_values import (
    decode_values,
    parse_json5_value,
)
from veupath_chatbot.platform.errors import ValidationError


class TestParseJson5Value:
    """Tests for the parse_json5_value helper."""

    def test_parses_json_array(self) -> None:
        assert parse_json5_value('["a", "b"]') == ["a", "b"]

    def test_parses_json5_single_quoted_array(self) -> None:
        result = parse_json5_value("['a', 'b']")
        assert result == ["a", "b"]

    def test_parses_json_number(self) -> None:
        assert parse_json5_value("42") == 42

    def test_parses_json_float(self) -> None:
        assert parse_json5_value("3.14") == 3.14

    def test_parses_json_string(self) -> None:
        assert parse_json5_value('"hello"') == "hello"

    def test_parses_json_bool_true(self) -> None:
        assert parse_json5_value("true") is True

    def test_parses_json_bool_false(self) -> None:
        assert parse_json5_value("false") is False

    def test_parses_json_null(self) -> None:
        assert parse_json5_value("null") is None

    def test_parses_json_object(self) -> None:
        result = parse_json5_value('{"min": 1, "max": 10}')
        assert result == {"min": 1, "max": 10}

    def test_returns_none_for_unparseable(self) -> None:
        assert parse_json5_value("not json at all") is None

    def test_returns_none_for_empty_string(self) -> None:
        # Empty string is not valid JSON
        assert parse_json5_value("") is None

    def test_parses_nested_array(self) -> None:
        result = parse_json5_value('["a", ["b", "c"]]')
        assert result == ["a", ["b", "c"]]


class TestDecodeValues:
    """Tests for the decode_values function."""

    # --- None input ---
    def test_none_returns_empty_list(self) -> None:
        assert decode_values(None, "param") == []

    # --- Dict input ---
    def test_dict_raises_validation_error(self) -> None:
        with pytest.raises(
            ValidationError, match="Invalid parameter value"
        ) as exc_info:
            decode_values({"key": "val"}, "my_param")
        assert "does not accept dictionaries" in (exc_info.value.detail or "")

    # --- List/tuple/set input ---
    def test_list_passthrough(self) -> None:
        assert decode_values(["a", "b", "c"], "p") == ["a", "b", "c"]

    def test_list_filters_none(self) -> None:
        assert decode_values(["a", None, "b"], "p") == ["a", "b"]

    def test_empty_list_returns_empty(self) -> None:
        assert decode_values([], "p") == []

    def test_tuple_passthrough(self) -> None:
        assert decode_values(("x", "y"), "p") == ["x", "y"]

    def test_set_passthrough(self) -> None:
        result = decode_values({"a"}, "p")
        assert result == ["a"]

    # --- String input: empty/whitespace ---
    def test_empty_string_returns_empty(self) -> None:
        assert decode_values("", "p") == []

    def test_whitespace_only_returns_empty(self) -> None:
        assert decode_values("   ", "p") == []

    # --- String input: JSON5 array ---
    def test_json_array_string(self) -> None:
        result = decode_values('["a", "b"]', "p")
        assert result == ["a", "b"]

    def test_json5_single_quoted_array(self) -> None:
        result = decode_values("['x', 'y']", "p")
        assert result == ["x", "y"]

    def test_json_array_with_nulls_filtered(self) -> None:
        result = decode_values('["a", null, "b"]', "p")
        assert result == ["a", "b"]

    # --- String input: JSON5 scalar ---
    def test_json_number_string(self) -> None:
        result = decode_values("42", "p")
        assert result == [42]

    def test_json_true_string(self) -> None:
        result = decode_values("true", "p")
        assert result == [True]

    def test_json_false_string(self) -> None:
        result = decode_values("false", "p")
        assert result == [False]

    def test_json_null_string_treated_as_literal(self) -> None:
        # parse_json5_value("null") returns None, which fails the `is not None` check,
        # so "null" falls through to the plain-string branch and is returned as-is.
        assert decode_values("null", "p") == ["null"]

    # --- String input: CSV ---
    def test_csv_string(self) -> None:
        result = decode_values("a, b, c", "p")
        assert result == ["a", "b", "c"]

    def test_csv_with_extra_spaces(self) -> None:
        result = decode_values("Plasmodium,  Toxoplasma", "p")
        assert result == ["Plasmodium", "Toxoplasma"]

    def test_csv_filters_empty_items(self) -> None:
        # "a,,b" -> csv splits to ["a", "", "b"] and empty strings are filtered
        result = decode_values("a,,b", "p")
        assert result == ["a", "b"]

    # --- String input: plain string (no comma, not JSON) ---
    def test_plain_string(self) -> None:
        result = decode_values("Plasmodium falciparum 3D7", "p")
        assert result == ["Plasmodium falciparum 3D7"]

    def test_plain_string_with_whitespace(self) -> None:
        result = decode_values("  hello  ", "p")
        assert result == ["hello"]

    # --- Numeric input ---
    def test_integer_passthrough(self) -> None:
        assert decode_values(42, "p") == [42]

    def test_float_passthrough(self) -> None:
        assert decode_values(3.14, "p") == [3.14]

    # --- Bool input ---
    def test_bool_true_passthrough(self) -> None:
        assert decode_values(True, "p") == [True]

    def test_bool_false_passthrough(self) -> None:
        assert decode_values(False, "p") == [False]

    # --- Edge cases ---
    def test_json_quoted_string(self) -> None:
        # '"hello"' is valid JSON5 -> parses to "hello"
        result = decode_values('"hello"', "p")
        assert result == ["hello"]

    def test_csv_with_quoted_comma(self) -> None:
        # CSV parsing: '"a,b",c' should parse to ["a,b", "c"]
        result = decode_values('"a,b",c', "p")
        assert result == ["a,b", "c"]

    def test_list_of_mixed_types(self) -> None:
        result = decode_values([1, "two", 3.0, None, True], "p")
        assert result == [1, "two", 3.0, True]

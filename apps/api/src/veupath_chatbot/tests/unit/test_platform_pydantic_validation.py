"""Unit tests for platform.pydantic_validation — parsing Pydantic error text."""

from veupath_chatbot.platform.pydantic_validation import (
    parse_pydantic_validation_error_text,
)


class TestParsePydanticValidationErrorText:
    # -- Null/empty/irrelevant input --
    def test_none_returns_none(self):
        assert parse_pydantic_validation_error_text(None) is None

    def test_empty_string_returns_none(self):
        assert parse_pydantic_validation_error_text("") is None

    def test_unrelated_text_returns_none(self):
        assert parse_pydantic_validation_error_text("some random error") is None

    def test_contains_keyword_but_no_header_match(self):
        # Has "validation error for" but no proper header format
        assert (
            parse_pydantic_validation_error_text(
                "there was a validation error for something"
            )
            is None
        )

    # -- Single error --
    def test_single_field_error(self):
        text = (
            "1 validation error for SearchParams\n"
            "text_expression\n"
            "  Field required [type=missing, input_value={}, input_type=dict]"
        )
        result = parse_pydantic_validation_error_text(text)
        assert result is not None
        assert result["model"] == "SearchParams"
        assert result["errorCount"] == 1
        assert len(result["errors"]) == 1

        err = result["errors"][0]
        assert err["loc"] == ["text_expression"]
        assert err["msg"] == "Field required"
        assert err["type"] == "missing"
        assert "meta" in err
        assert result["raw"] == text

    # -- Multiple errors --
    def test_multiple_field_errors(self):
        text = (
            "2 validation error for GeneSearch\n"
            "organism\n"
            "  Field required [type=missing, input_value={}, input_type=dict]\n"
            "text_expression\n"
            "  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]"
        )
        result = parse_pydantic_validation_error_text(text)
        assert result is not None
        assert result["model"] == "GeneSearch"
        assert result["errorCount"] == 2
        assert len(result["errors"]) == 2

        assert result["errors"][0]["loc"] == ["organism"]
        assert result["errors"][1]["loc"] == ["text_expression"]

    # -- Error without meta brackets --
    def test_error_without_meta(self):
        text = "1 validation error for Model\nfield_name\n  Value is not valid"
        result = parse_pydantic_validation_error_text(text)
        assert result is not None
        assert len(result["errors"]) == 1
        err = result["errors"][0]
        assert err["msg"] == "Value is not valid"
        assert "type" not in err
        # meta should be empty dict
        assert err.get("meta") is None or err.get("meta") == {}

    # -- Leading whitespace in text --
    def test_leading_blank_lines_handled(self):
        text = "\n\n1 validation error for Foo\nbar\n  Missing [type=missing]"
        result = parse_pydantic_validation_error_text(text)
        assert result is not None
        assert result["model"] == "Foo"
        assert result["errorCount"] == 1

    # -- Meta parsing details --
    def test_meta_parsing_with_type(self):
        text = (
            "1 validation error for Config\n"
            "timeout\n"
            "  Input should be a valid integer [type=int_parsing, input_value='abc', input_type=str]"
        )
        result = parse_pydantic_validation_error_text(text)
        assert result is not None
        err = result["errors"][0]
        assert err["type"] == "int_parsing"
        assert err["meta"]["input_value"] == "'abc'"
        assert err["meta"]["input_type"] == "str"

    # -- Blank detail lines skipped --
    def test_blank_lines_between_errors_skipped(self):
        text = (
            "2 validation error for Model\n"
            "field_a\n"
            "  Error A [type=err_a]\n"
            "\n"
            "field_b\n"
            "  Error B [type=err_b]"
        )
        result = parse_pydantic_validation_error_text(text)
        assert result is not None
        assert len(result["errors"]) == 2

    # -- Detail line before any loc is skipped --
    def test_detail_before_loc_skipped(self):
        text = (
            "1 validation error for X\n"
            "  orphaned detail line\n"
            "field\n"
            "  Real error [type=real]"
        )
        result = parse_pydantic_validation_error_text(text)
        assert result is not None
        assert len(result["errors"]) == 1
        assert result["errors"][0]["loc"] == ["field"]

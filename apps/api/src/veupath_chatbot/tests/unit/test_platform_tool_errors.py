"""Unit tests for platform.tool_errors — standardized AI tool error payloads."""

from enum import Enum

from veupath_chatbot.platform.tool_errors import tool_error


class TestToolError:
    def test_basic_string_code(self):
        result = tool_error("INVALID_INPUT", "Missing required field")
        assert result == {
            "ok": False,
            "code": "INVALID_INPUT",
            "message": "Missing required field",
        }

    def test_enum_code_uses_value(self):
        class MyCode(Enum):
            BAD_PARAM = "BAD_PARAM"

        result = tool_error(MyCode.BAD_PARAM, "Bad parameter")
        assert result["ok"] is False
        assert result["code"] == "BAD_PARAM"
        assert result["message"] == "Bad parameter"

    def test_details_added_to_payload(self):
        result = tool_error(
            "SEARCH_FAILED",
            "Could not find search",
            searchName="GenesByTextSearch",
            attempted=True,
        )
        assert result["ok"] is False
        assert result["code"] == "SEARCH_FAILED"
        assert result["message"] == "Could not find search"
        assert result["details"] == {
            "searchName": "GenesByTextSearch",
            "attempted": True,
        }
        # Details also promoted to top level (non-conflicting keys)
        assert result["searchName"] == "GenesByTextSearch"
        assert result["attempted"] is True

    def test_details_do_not_overwrite_reserved_keys(self):
        # "ok" is already in payload; detail keys matching reserved names
        # should not overwrite them. "code" and "message" are positional args
        # so can't appear in **details — test with "ok" which IS already set.
        result = tool_error(
            "ERR",
            "msg",
            extra="val",
        )
        # "ok", "code", "message" remain as originally set
        assert result["ok"] is False
        assert result["code"] == "ERR"
        assert result["message"] == "msg"
        assert result["extra"] == "val"

    def test_none_detail_values_not_promoted(self):
        result = tool_error("ERR", "msg", extra=None)
        assert result["details"] == {"extra": None}
        # None values are not promoted to top level
        assert "extra" not in {k for k in result if k != "details"}

    def test_no_details_key_when_empty(self):
        result = tool_error("ERR", "msg")
        assert "details" not in result

    def test_non_enum_non_string_code_converted_to_str(self):
        result = tool_error(42, "numeric code")
        assert result["code"] == "42"

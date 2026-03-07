"""Unit tests for veupath_chatbot.integrations.veupathdb.param_utils.

Tests normalize_param_value which converts Python JSON values to WDK-compatible
string representations (all WDK params are strings on the wire).
"""

import json

from veupath_chatbot.integrations.veupathdb.param_utils import normalize_param_value


class TestNormalizeParamValueStrings:
    """String inputs are returned as-is."""

    def test_plain_string(self) -> None:
        assert normalize_param_value("kinase") == "kinase"

    def test_empty_string(self) -> None:
        assert normalize_param_value("") == ""

    def test_whitespace_string(self) -> None:
        assert normalize_param_value("  ") == "  "


class TestNormalizeParamValueNone:
    """None becomes empty string (WDK convention)."""

    def test_none_returns_empty(self) -> None:
        assert normalize_param_value(None) == ""


class TestNormalizeParamValueBooleans:
    """Booleans are lowercased (WDK expects "true"/"false")."""

    def test_true(self) -> None:
        assert normalize_param_value(True) == "true"

    def test_false(self) -> None:
        assert normalize_param_value(False) == "false"


class TestNormalizeParamValueNumbers:
    """Numbers become their string representation."""

    def test_int(self) -> None:
        assert normalize_param_value(42) == "42"

    def test_zero(self) -> None:
        assert normalize_param_value(0) == "0"

    def test_negative(self) -> None:
        assert normalize_param_value(-1) == "-1"

    def test_float(self) -> None:
        assert normalize_param_value(3.14) == "3.14"

    def test_float_zero(self) -> None:
        assert normalize_param_value(0.0) == "0.0"


class TestNormalizeParamValueCollections:
    """Lists and dicts are JSON-encoded (WDK multi-pick convention).

    WDK's AbstractEnumParam.getExternalStableValue encodes multi-pick values
    as JSON array strings. E.g. ["Plasmodium falciparum 3D7"] becomes
    '["Plasmodium falciparum 3D7"]'.
    """

    def test_list(self) -> None:
        result = normalize_param_value(["a", "b", "c"])
        assert result == '["a", "b", "c"]'
        assert json.loads(result) == ["a", "b", "c"]

    def test_empty_list(self) -> None:
        result = normalize_param_value([])
        assert result == "[]"

    def test_nested_list(self) -> None:
        result = normalize_param_value([["a"], ["b"]])
        parsed = json.loads(result)
        assert parsed == [["a"], ["b"]]

    def test_dict(self) -> None:
        result = normalize_param_value({"key": "value"})
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_empty_dict(self) -> None:
        result = normalize_param_value({})
        assert result == "{}"

    def test_organism_list_matches_wdk_format(self) -> None:
        """Verify organism list encodes like WDK expects for multi-pick-vocabulary."""
        organisms = ["Plasmodium falciparum 3D7", "Plasmodium vivax P01"]
        result = normalize_param_value(organisms)
        parsed = json.loads(result)
        assert parsed == organisms

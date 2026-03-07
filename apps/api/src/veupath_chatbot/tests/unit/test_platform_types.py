"""Unit tests for platform.types — JSON type guards."""

import pytest

from veupath_chatbot.platform.types import as_json_array, as_json_object


class TestAsJsonObject:
    def test_dict_passes_through(self):
        value = {"key": "value", "nested": {"a": 1}}
        result = as_json_object(value)
        assert result is value
        assert result["key"] == "value"

    def test_empty_dict_passes_through(self):
        value: dict[str, object] = {}
        result = as_json_object(value)
        assert result == {}

    def test_raises_on_list(self):
        with pytest.raises(TypeError, match="Expected dict, got <class 'list'>"):
            as_json_object([1, 2, 3])

    def test_raises_on_string(self):
        with pytest.raises(TypeError, match="Expected dict, got <class 'str'>"):
            as_json_object("not a dict")

    def test_raises_on_int(self):
        with pytest.raises(TypeError, match="Expected dict, got <class 'int'>"):
            as_json_object(42)

    def test_raises_on_none(self):
        with pytest.raises(TypeError, match="Expected dict, got <class 'NoneType'>"):
            as_json_object(None)

    def test_raises_on_bool(self):
        with pytest.raises(TypeError, match="Expected dict, got <class 'bool'>"):
            as_json_object(True)

    def test_raises_on_float(self):
        with pytest.raises(TypeError, match="Expected dict, got <class 'float'>"):
            as_json_object(3.14)


class TestAsJsonArray:
    def test_list_passes_through(self):
        value = [1, "two", {"three": 3}]
        result = as_json_array(value)
        assert result is value
        assert len(result) == 3

    def test_empty_list_passes_through(self):
        value: list[object] = []
        result = as_json_array(value)
        assert result == []

    def test_raises_on_dict(self):
        with pytest.raises(TypeError, match="Expected list, got <class 'dict'>"):
            as_json_array({"key": "value"})

    def test_raises_on_string(self):
        with pytest.raises(TypeError, match="Expected list, got <class 'str'>"):
            as_json_array("not a list")

    def test_raises_on_int(self):
        with pytest.raises(TypeError, match="Expected list, got <class 'int'>"):
            as_json_array(42)

    def test_raises_on_none(self):
        with pytest.raises(TypeError, match="Expected list, got <class 'NoneType'>"):
            as_json_array(None)

    def test_raises_on_tuple(self):
        with pytest.raises(TypeError, match="Expected list, got <class 'tuple'>"):
            as_json_array((1, 2, 3))

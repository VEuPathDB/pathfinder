"""Unit tests for platform.parsing — parse_jsonish helper."""

from veupath_chatbot.platform.parsing import parse_jsonish


class TestParseJsonish:
    # -- None input --
    def test_none_returns_none(self):
        assert parse_jsonish(None) is None

    # -- Already structured (dict/list) --
    def test_dict_passthrough(self):
        d = {"key": "value"}
        assert parse_jsonish(d) is d

    def test_list_passthrough(self):
        lst = [1, 2, 3]
        assert parse_jsonish(lst) is lst

    def test_empty_dict_passthrough(self):
        d: dict[str, object] = {}
        assert parse_jsonish(d) == {}

    def test_empty_list_passthrough(self):
        lst: list[object] = []
        assert parse_jsonish(lst) == []

    # -- JSON strings --
    def test_json_object_string(self):
        result = parse_jsonish('{"name": "kinase", "count": 5}')
        assert result == {"name": "kinase", "count": 5}

    def test_json_array_string(self):
        result = parse_jsonish("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_json_nested_object(self):
        result = parse_jsonish('{"a": {"b": [1, 2]}}')
        assert result == {"a": {"b": [1, 2]}}

    def test_json_empty_object_string(self):
        assert parse_jsonish("{}") == {}

    def test_json_empty_array_string(self):
        assert parse_jsonish("[]") == []

    # -- JSON scalar strings return None (not dict/list) --
    def test_json_scalar_string_returns_none(self):
        assert parse_jsonish('"just a string"') is None

    def test_json_scalar_number_returns_none(self):
        assert parse_jsonish("42") is None

    def test_json_scalar_bool_returns_none(self):
        assert parse_jsonish("true") is None

    def test_json_null_returns_none(self):
        assert parse_jsonish("null") is None

    # -- Python literal fallback --
    def test_python_dict_literal(self):
        result = parse_jsonish("{'key': 'value'}")
        assert result == {"key": "value"}

    def test_python_list_literal(self):
        result = parse_jsonish("['a', 'b', 'c']")
        assert result == ["a", "b", "c"]

    def test_python_tuple_literal_returns_none(self):
        # tuple is not a dict or list, so it is rejected
        assert parse_jsonish("(1, 2, 3)") is None

    def test_python_scalar_literal_returns_none(self):
        assert parse_jsonish("42") is None

    # -- Unparseable strings return None --
    def test_garbage_string_returns_none(self):
        assert parse_jsonish("not json at all {{{}}}") is None

    def test_empty_string_returns_none(self):
        assert parse_jsonish("") is None

    def test_whitespace_string_returns_none(self):
        # Whitespace-only input is not valid JSON or Python literal
        assert parse_jsonish("   ") is None

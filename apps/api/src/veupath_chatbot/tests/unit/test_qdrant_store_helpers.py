"""Tests for pure helper functions in qdrant_store.py."""

import json

from veupath_chatbot.integrations.vectorstore.qdrant_store import (
    context_hash,
    point_uuid,
    sha256_hex,
    stable_json_dumps,
)


class TestStableJsonDumps:
    def test_sort_keys(self) -> None:
        result = stable_json_dumps({"b": 2, "a": 1})
        assert result == '{"a":1,"b":2}'

    def test_no_spaces(self) -> None:
        result = stable_json_dumps({"key": "value"})
        assert " " not in result

    def test_ensure_ascii_false(self) -> None:
        result = stable_json_dumps({"name": "cafe\u0301"})
        # Should contain the raw unicode, not \\u escapes
        assert "\\u" not in result

    def test_nested_objects_are_sorted(self) -> None:
        result = stable_json_dumps({"z": {"b": 1, "a": 2}})
        parsed = json.loads(result)
        # Keys should be sorted in the output
        assert list(parsed["z"].keys()) == ["a", "b"]

    def test_empty_dict(self) -> None:
        assert stable_json_dumps({}) == "{}"

    def test_list_values_preserve_order(self) -> None:
        result = stable_json_dumps([3, 1, 2])
        assert result == "[3,1,2]"


class TestSha256Hex:
    def test_returns_hex_string(self) -> None:
        result = sha256_hex("hello")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self) -> None:
        assert sha256_hex("test") == sha256_hex("test")

    def test_different_inputs_different_hashes(self) -> None:
        assert sha256_hex("a") != sha256_hex("b")

    def test_empty_string(self) -> None:
        result = sha256_hex("")
        assert len(result) == 64


class TestContextHash:
    def test_deterministic_for_same_context(self) -> None:
        ctx = {"param1": "val1", "param2": "val2"}
        assert context_hash(ctx) == context_hash(ctx)

    def test_key_order_does_not_matter(self) -> None:
        a = context_hash({"x": "1", "y": "2"})
        b = context_hash({"y": "2", "x": "1"})
        assert a == b

    def test_different_values_different_hash(self) -> None:
        a = context_hash({"x": "1"})
        b = context_hash({"x": "2"})
        assert a != b

    def test_empty_context(self) -> None:
        result = context_hash({})
        assert len(result) == 64


class TestPointUuid:
    def test_deterministic(self) -> None:
        a = point_uuid("some:key")
        b = point_uuid("some:key")
        assert a == b

    def test_different_keys_different_uuids(self) -> None:
        a = point_uuid("key_a")
        b = point_uuid("key_b")
        assert a != b

    def test_returns_valid_uuid_string(self) -> None:
        result = point_uuid("test")
        # UUID format: 8-4-4-4-12 hex chars
        parts = result.split("-")
        assert len(parts) == 5
        assert [len(p) for p in parts] == [8, 4, 4, 4, 12]

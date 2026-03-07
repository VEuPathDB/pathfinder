"""Tests for domain/parameters/_value_helpers.py."""

from __future__ import annotations

import pytest

from veupath_chatbot.domain.parameters._value_helpers import ParameterValueMixin
from veupath_chatbot.platform.errors import ValidationError
from veupath_chatbot.tests.fixtures.builders import make_param_spec


class Mixin(ParameterValueMixin):
    """Concrete subclass so we can instantiate the mixin for testing."""

    pass


class TestStringify:
    def setup_method(self) -> None:
        self.m = Mixin()

    def test_none(self) -> None:
        assert self.m._stringify(None) == ""

    def test_bool_true(self) -> None:
        assert self.m._stringify(True) == "true"

    def test_bool_false(self) -> None:
        assert self.m._stringify(False) == "false"

    def test_string(self) -> None:
        assert self.m._stringify("hello") == "hello"

    def test_integer(self) -> None:
        assert self.m._stringify(42) == "42"

    def test_float(self) -> None:
        assert self.m._stringify(3.14) == "3.14"

    def test_empty_string(self) -> None:
        assert self.m._stringify("") == ""


class TestHandleEmpty:
    def setup_method(self) -> None:
        self.m = Mixin()

    def test_allow_empty_returns_empty_string(self) -> None:
        spec = make_param_spec(allow_empty=True)
        assert self.m._handle_empty(spec, None) == ""

    def test_allow_empty_returns_empty_string_regardless_of_value(self) -> None:
        spec = make_param_spec(allow_empty=True)
        assert self.m._handle_empty(spec, "anything") == ""

    def test_multi_pick_not_allow_empty_raises(self) -> None:
        spec = make_param_spec(param_type="multi-pick-vocabulary", allow_empty=False)
        with pytest.raises(ValidationError) as exc_info:
            self.m._handle_empty(spec, None)
        assert "requires a value" in (exc_info.value.detail or "")

    def test_single_pick_not_allow_empty_raises(self) -> None:
        spec = make_param_spec(param_type="single-pick-vocabulary", allow_empty=False)
        with pytest.raises(ValidationError) as exc_info:
            self.m._handle_empty(spec, None)
        assert "requires a value" in (exc_info.value.detail or "")

    def test_non_vocab_type_returns_value(self) -> None:
        spec = make_param_spec(param_type="string", allow_empty=False)
        assert self.m._handle_empty(spec, "some_val") == "some_val"

    def test_non_vocab_type_returns_none(self) -> None:
        spec = make_param_spec(param_type="number", allow_empty=False)
        assert self.m._handle_empty(spec, None) is None


class TestValidateMultiCount:
    def setup_method(self) -> None:
        self.m = Mixin()

    def test_empty_with_allow_empty_passes(self) -> None:
        spec = make_param_spec(allow_empty=True)
        self.m._validate_multi_count(spec, [])  # should not raise

    def test_below_min_raises(self) -> None:
        spec = make_param_spec(min_selected=2)
        with pytest.raises(ValidationError) as exc_info:
            self.m._validate_multi_count(spec, ["a"])
        assert "at least 2" in (exc_info.value.detail or "")

    def test_above_max_raises(self) -> None:
        spec = make_param_spec(max_selected=2)
        with pytest.raises(ValidationError) as exc_info:
            self.m._validate_multi_count(spec, ["a", "b", "c"])
        assert "at most 2" in (exc_info.value.detail or "")

    def test_at_min_passes(self) -> None:
        spec = make_param_spec(min_selected=2)
        self.m._validate_multi_count(spec, ["a", "b"])

    def test_at_max_passes(self) -> None:
        spec = make_param_spec(max_selected=3)
        self.m._validate_multi_count(spec, ["a", "b", "c"])

    def test_no_constraints_passes(self) -> None:
        spec = make_param_spec()
        self.m._validate_multi_count(spec, ["a", "b", "c", "d"])

    def test_zero_min_passes_with_empty(self) -> None:
        spec = make_param_spec(min_selected=0)
        self.m._validate_multi_count(spec, [])


class TestValidateSingleRequired:
    def setup_method(self) -> None:
        self.m = Mixin()

    def test_allow_empty_passes(self) -> None:
        spec = make_param_spec(allow_empty=True)
        self.m._validate_single_required(spec)  # should not raise

    def test_min_zero_passes(self) -> None:
        spec = make_param_spec(min_selected=0)
        self.m._validate_single_required(spec)

    def test_min_negative_passes(self) -> None:
        spec = make_param_spec(min_selected=-1)
        self.m._validate_single_required(spec)

    def test_no_min_raises(self) -> None:
        spec = make_param_spec()
        with pytest.raises(ValidationError) as exc_info:
            self.m._validate_single_required(spec)
        assert "requires a value" in (exc_info.value.detail or "")

    def test_min_one_raises(self) -> None:
        spec = make_param_spec(min_selected=1)
        with pytest.raises(ValidationError) as exc_info:
            self.m._validate_single_required(spec)
        assert "requires a value" in (exc_info.value.detail or "")


class TestMatchVocabValue:
    def setup_method(self) -> None:
        self.m = Mixin()

    def test_with_list_vocab(self) -> None:
        spec = make_param_spec(
            vocabulary=[["val1", "Display 1"], ["val2", "Display 2"]]
        )
        assert self.m._match_vocab_value(spec, "Display 1") == "val1"

    def test_no_vocab_passthrough(self) -> None:
        spec = make_param_spec(vocabulary=None)
        assert self.m._match_vocab_value(spec, "anything") == "anything"

    def test_invalid_value_raises(self) -> None:
        spec = make_param_spec(vocabulary=[["a", "A"]])
        with pytest.raises(ValidationError) as exc_info:
            self.m._match_vocab_value(spec, "nonexistent")
        assert "does not accept" in (exc_info.value.detail or "")

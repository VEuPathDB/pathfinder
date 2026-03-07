"""Tests for domain/parameters/specs.py."""

from __future__ import annotations

from veupath_chatbot.domain.parameters.specs import (
    ParamSpecNormalized,
    adapt_param_specs,
    extract_param_specs,
    find_input_step_param,
    find_missing_required_params,
)


# ---------------------------------------------------------------------------
# extract_param_specs
# ---------------------------------------------------------------------------
class TestExtractParamSpecs:
    def test_from_parameters_list(self) -> None:
        payload = {
            "parameters": [
                {"name": "p1", "type": "string"},
                {"name": "p2", "type": "number"},
            ]
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 2
        assert specs[0] == {"name": "p1", "type": "string"}

    def test_from_parameters_dict(self) -> None:
        payload = {
            "parameters": {
                "organism": {"type": "multi-pick-vocabulary"},
                "stage": {"type": "single-pick-vocabulary"},
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 2
        names = {s["name"] for s in specs if isinstance(s, dict)}
        assert names == {"organism", "stage"}
        # Verify dict params get name injected
        for s in specs:
            if isinstance(s, dict):
                assert "name" in s

    def test_from_param_map(self) -> None:
        payload = {
            "paramMap": {
                "organism": {"type": "multi-pick-vocabulary"},
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1

    def test_from_search_config_parameters(self) -> None:
        payload = {
            "searchConfig": {
                "parameters": [
                    {"name": "p1", "type": "string"},
                ]
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1

    def test_from_search_config_param_map(self) -> None:
        payload = {
            "searchConfig": {
                "paramMap": {
                    "p1": {"type": "string"},
                }
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1

    def test_from_question_parameters(self) -> None:
        payload = {
            "question": {
                "parameters": [
                    {"name": "p1", "type": "string"},
                ]
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1

    def test_from_parameter_details(self) -> None:
        payload = {
            "parameterDetails": {
                "p1": {"type": "string"},
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1

    def test_from_param_details(self) -> None:
        payload = {
            "paramDetails": {
                "p1": {"type": "string"},
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1

    def test_priority_order(self) -> None:
        """parameters field takes priority over searchConfig.parameters."""
        payload = {
            "parameters": [{"name": "from_params", "type": "string"}],
            "searchConfig": {
                "parameters": [{"name": "from_sc", "type": "string"}],
            },
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1
        assert specs[0]["name"] == "from_params"

    def test_empty_payload(self) -> None:
        assert extract_param_specs({}) == []

    def test_skips_non_dict_items_in_list(self) -> None:
        payload = {"parameters": [{"name": "p1", "type": "string"}, "not_a_dict", 42]}
        specs = extract_param_specs(payload)
        assert len(specs) == 1

    def test_skips_non_dict_values_in_dict(self) -> None:
        payload = {
            "parameters": {
                "p1": {"type": "string"},
                "p2": "not_a_dict",
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1


# ---------------------------------------------------------------------------
# adapt_param_specs
# ---------------------------------------------------------------------------
class TestAdaptParamSpecs:
    def test_basic_adaptation(self) -> None:
        payload = {
            "parameters": [
                {
                    "name": "organism",
                    "type": "multi-pick-vocabulary",
                    "allowEmptyValue": False,
                    "minSelectedCount": 1,
                    "maxSelectedCount": 10,
                    "vocabulary": [["val1", "Display 1"]],
                }
            ]
        }
        specs = adapt_param_specs(payload)
        assert "organism" in specs
        s = specs["organism"]
        assert s.name == "organism"
        assert s.param_type == "multi-pick-vocabulary"
        assert s.allow_empty_value is False
        assert s.min_selected_count == 1
        assert s.max_selected_count == 10
        assert s.vocabulary == [["val1", "Display 1"]]

    def test_negative_max_selected_becomes_none(self) -> None:
        payload = {
            "parameters": [
                {
                    "name": "organism",
                    "type": "multi-pick-vocabulary",
                    "maxSelectedCount": -1,
                }
            ]
        }
        specs = adapt_param_specs(payload)
        assert specs["organism"].max_selected_count is None

    def test_param_type_alias(self) -> None:
        """paramType is also accepted as a type key."""
        payload = {
            "parameters": [
                {"name": "p1", "paramType": "number"},
            ]
        }
        specs = adapt_param_specs(payload)
        assert specs["p1"].param_type == "number"

    def test_allow_empty_alias(self) -> None:
        """allowEmpty is also accepted."""
        payload = {
            "parameters": [
                {"name": "p1", "type": "string", "allowEmpty": True},
            ]
        }
        specs = adapt_param_specs(payload)
        assert specs["p1"].allow_empty_value is True

    def test_dict_vocabulary(self) -> None:
        vocab = {"data": {"term": "root"}, "children": []}
        payload = {
            "parameters": [
                {"name": "p1", "type": "multi-pick-vocabulary", "vocabulary": vocab},
            ]
        }
        specs = adapt_param_specs(payload)
        assert specs["p1"].vocabulary == vocab

    def test_non_dict_non_list_vocabulary_is_none(self) -> None:
        payload = {
            "parameters": [
                {"name": "p1", "type": "string", "vocabulary": "not_a_vocab"},
            ]
        }
        specs = adapt_param_specs(payload)
        assert specs["p1"].vocabulary is None

    def test_count_only_leaves(self) -> None:
        payload = {
            "parameters": [
                {
                    "name": "p1",
                    "type": "multi-pick-vocabulary",
                    "countOnlyLeaves": True,
                },
            ]
        }
        specs = adapt_param_specs(payload)
        assert specs["p1"].count_only_leaves is True

    def test_skips_spec_without_name(self) -> None:
        payload = {"parameters": [{"type": "string"}]}
        specs = adapt_param_specs(payload)
        assert len(specs) == 0

    def test_skips_non_string_name(self) -> None:
        payload = {"parameters": [{"name": 42, "type": "string"}]}
        specs = adapt_param_specs(payload)
        assert len(specs) == 0

    def test_missing_type_becomes_empty_string(self) -> None:
        payload = {"parameters": [{"name": "p1"}]}
        specs = adapt_param_specs(payload)
        assert specs["p1"].param_type == ""

    def test_non_int_min_selected_becomes_none(self) -> None:
        payload = {
            "parameters": [
                {"name": "p1", "type": "string", "minSelectedCount": "abc"},
            ]
        }
        specs = adapt_param_specs(payload)
        assert specs["p1"].min_selected_count is None

    def test_none_payload(self) -> None:
        specs = adapt_param_specs(None)
        assert specs == {}

    def test_empty_payload(self) -> None:
        specs = adapt_param_specs({})
        assert specs == {}


# ---------------------------------------------------------------------------
# find_input_step_param
# ---------------------------------------------------------------------------
class TestFindInputStepParam:
    def test_finds_input_step(self) -> None:
        specs = {
            "organism": ParamSpecNormalized(
                name="organism", param_type="multi-pick-vocabulary"
            ),
            "inputStepId": ParamSpecNormalized(
                name="inputStepId", param_type="input-step"
            ),
        }
        assert find_input_step_param(specs) == "inputStepId"

    def test_no_input_step(self) -> None:
        specs = {
            "organism": ParamSpecNormalized(
                name="organism", param_type="multi-pick-vocabulary"
            ),
        }
        assert find_input_step_param(specs) is None

    def test_empty_specs(self) -> None:
        assert find_input_step_param({}) is None


# ---------------------------------------------------------------------------
# find_missing_required_params
# ---------------------------------------------------------------------------
class TestFindMissingRequiredParams:
    def test_no_required_params(self) -> None:
        specs = [{"name": "p1", "type": "string", "allowEmptyValue": True}]
        missing = find_missing_required_params(specs, {"p1": "val"})
        assert missing == []

    def test_required_param_present(self) -> None:
        specs = [{"name": "p1", "type": "string", "isRequired": True}]
        missing = find_missing_required_params(specs, {"p1": "val"})
        assert missing == []

    def test_required_param_missing(self) -> None:
        specs = [{"name": "p1", "type": "string", "isRequired": True}]
        missing = find_missing_required_params(specs, {})
        assert missing == ["p1"]

    def test_required_param_none_value(self) -> None:
        specs = [{"name": "p1", "type": "string", "isRequired": True}]
        missing = find_missing_required_params(specs, {"p1": None})
        assert missing == ["p1"]

    def test_required_param_empty_string(self) -> None:
        specs = [{"name": "p1", "type": "string", "isRequired": True}]
        missing = find_missing_required_params(specs, {"p1": ""})
        assert missing == ["p1"]

    def test_required_param_empty_list(self) -> None:
        specs = [{"name": "p1", "type": "string", "isRequired": True}]
        missing = find_missing_required_params(specs, {"p1": []})
        assert missing == ["p1"]

    def test_required_param_empty_dict(self) -> None:
        specs = [{"name": "p1", "type": "string", "isRequired": True}]
        missing = find_missing_required_params(specs, {"p1": {}})
        assert missing == ["p1"]

    def test_not_allow_empty_treated_as_required(self) -> None:
        specs = [{"name": "p1", "type": "string", "allowEmptyValue": False}]
        missing = find_missing_required_params(specs, {})
        assert missing == ["p1"]

    def test_allow_empty_not_treated_as_required(self) -> None:
        specs = [{"name": "p1", "type": "string", "allowEmptyValue": True}]
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_multi_pick_empty_json_string(self) -> None:
        specs = [{"name": "p1", "type": "multi-pick-vocabulary", "isRequired": True}]
        missing = find_missing_required_params(specs, {"p1": "[]"})
        assert missing == ["p1"]

    def test_multi_pick_empty_list(self) -> None:
        specs = [{"name": "p1", "type": "multi-pick-vocabulary", "isRequired": True}]
        missing = find_missing_required_params(specs, {"p1": []})
        assert missing == ["p1"]

    def test_multi_pick_with_values(self) -> None:
        specs = [{"name": "p1", "type": "multi-pick-vocabulary", "isRequired": True}]
        missing = find_missing_required_params(specs, {"p1": '["a"]'})
        assert missing == []

    def test_skips_non_dict_specs(self) -> None:
        specs = ["not_a_dict", {"name": "p1", "type": "string", "isRequired": True}]
        missing = find_missing_required_params(specs, {})
        assert missing == ["p1"]

    def test_skips_spec_without_name(self) -> None:
        specs = [{"type": "string", "isRequired": True}]
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_multiple_missing(self) -> None:
        specs = [
            {"name": "p1", "type": "string", "isRequired": True},
            {"name": "p2", "type": "string", "isRequired": True},
            {"name": "p3", "type": "string", "allowEmptyValue": True},
        ]
        missing = find_missing_required_params(specs, {"p3": "val"})
        assert missing == ["p1", "p2"]

    def test_is_required_non_bool_defaults_false(self) -> None:
        specs = [{"name": "p1", "type": "string", "isRequired": "yes"}]
        # "yes" is not a bool, so isRequired defaults to False
        # But allowEmptyValue is also missing, defaults to True, so not required
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_allow_empty_non_bool_defaults_true(self) -> None:
        specs = [{"name": "p1", "type": "string", "allowEmptyValue": "yes"}]
        # "yes" is not bool, defaults to True for allow_empty
        missing = find_missing_required_params(specs, {})
        assert missing == []

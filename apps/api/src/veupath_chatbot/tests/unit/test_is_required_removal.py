"""Tests for isRequired removal — required params use allowEmptyValue / minSelectedCount."""

from veupath_chatbot.domain.parameters.specs import find_missing_required_params


class TestFindMissingRequiredParamsWDKCompliant:
    """Verify required-param detection uses only WDK-native fields."""

    def test_allow_empty_false_means_required(self) -> None:
        specs = [{"name": "p1", "type": "string", "allowEmptyValue": False}]
        missing = find_missing_required_params(specs, {})
        assert missing == ["p1"]

    def test_allow_empty_true_means_not_required(self) -> None:
        specs = [{"name": "p1", "type": "string", "allowEmptyValue": True}]
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_min_selected_count_1_means_required(self) -> None:
        specs = [{"name": "p1", "type": "multi-pick-vocabulary", "minSelectedCount": 1}]
        missing = find_missing_required_params(specs, {})
        assert missing == ["p1"]

    def test_min_selected_count_0_not_required(self) -> None:
        specs = [{"name": "p1", "type": "multi-pick-vocabulary", "minSelectedCount": 0}]
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_no_allow_empty_key_defaults_not_required(self) -> None:
        """When allowEmptyValue is absent, defaults to True (not required)."""
        specs = [{"name": "p1", "type": "string"}]
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_min_selected_count_absent_defaults_not_required(self) -> None:
        """When minSelectedCount is absent, defaults to 0 (not required)."""
        specs = [{"name": "p1", "type": "multi-pick-vocabulary"}]
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_both_allow_empty_false_and_min_selected_1(self) -> None:
        specs = [
            {
                "name": "p1",
                "type": "multi-pick-vocabulary",
                "allowEmptyValue": False,
                "minSelectedCount": 1,
            }
        ]
        missing = find_missing_required_params(specs, {})
        assert missing == ["p1"]

    def test_allow_empty_true_but_min_selected_1_still_required(self) -> None:
        """minSelectedCount >= 1 overrides allowEmptyValue: True."""
        specs = [
            {
                "name": "p1",
                "type": "multi-pick-vocabulary",
                "allowEmptyValue": True,
                "minSelectedCount": 1,
            }
        ]
        missing = find_missing_required_params(specs, {})
        assert missing == ["p1"]

    def test_is_required_field_is_ignored(self) -> None:
        """isRequired is not a WDK field — it should be completely ignored."""
        specs = [{"name": "p1", "type": "string", "isRequired": True}]
        # isRequired alone should NOT make a param required; allowEmptyValue
        # is absent so defaults to True (not required).
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_is_required_true_with_allow_empty_true(self) -> None:
        """isRequired: True + allowEmptyValue: True should NOT be required."""
        specs = [
            {
                "name": "p1",
                "type": "string",
                "isRequired": True,
                "allowEmptyValue": True,
            }
        ]
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_min_selected_count_non_int_ignored(self) -> None:
        """Non-int minSelectedCount defaults to 0."""
        specs = [
            {"name": "p1", "type": "multi-pick-vocabulary", "minSelectedCount": "1"}
        ]
        missing = find_missing_required_params(specs, {})
        assert missing == []

    def test_required_param_present_with_value(self) -> None:
        specs = [{"name": "p1", "type": "string", "allowEmptyValue": False}]
        missing = find_missing_required_params(specs, {"p1": "some_value"})
        assert missing == []

    def test_required_param_present_but_empty(self) -> None:
        specs = [{"name": "p1", "type": "string", "allowEmptyValue": False}]
        missing = find_missing_required_params(specs, {"p1": ""})
        assert missing == ["p1"]

"""Tests for extract_param_specs after YAGNI cleanup.

Verifies that the canonical WDK payload paths are supported and that
speculative paths (parameterDetails, paramDetails, question.parameters)
have been removed.
"""

from veupath_chatbot.domain.parameters.specs import extract_param_specs


class TestCanonicalPaths:
    """The four canonical paths that WDK actually uses."""

    def test_parameters_as_list(self) -> None:
        payload = {
            "parameters": [
                {"name": "organism", "type": "multi-pick-vocabulary"},
                {"name": "stage", "type": "single-pick-vocabulary"},
            ]
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 2
        assert specs[0]["name"] == "organism"
        assert specs[1]["name"] == "stage"

    def test_parameters_as_dict(self) -> None:
        """Dict-shaped parameters (key -> spec) get name injected."""
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

    def test_param_map_at_top_level(self) -> None:
        """paramMap is a valid WDK shape (dict of name -> spec)."""
        payload = {
            "paramMap": {
                "organism": {"type": "multi-pick-vocabulary"},
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1
        assert specs[0]["name"] == "organism"

    def test_search_config_parameters_list(self) -> None:
        payload = {
            "searchConfig": {
                "parameters": [{"name": "text", "type": "string"}],
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1
        assert specs[0]["name"] == "text"

    def test_search_config_param_map(self) -> None:
        payload = {
            "searchConfig": {
                "paramMap": {"text": {"type": "string"}},
            }
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1
        assert specs[0]["name"] == "text"


class TestPriorityOrder:
    """Top-level fields take priority over nested ones."""

    def test_parameters_over_search_config(self) -> None:
        payload = {
            "parameters": [{"name": "from_params", "type": "string"}],
            "searchConfig": {
                "parameters": [{"name": "from_sc", "type": "string"}],
            },
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1
        assert specs[0]["name"] == "from_params"

    def test_param_map_over_search_config(self) -> None:
        payload = {
            "paramMap": {"from_pm": {"type": "string"}},
            "searchConfig": {
                "parameters": [{"name": "from_sc", "type": "string"}],
            },
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1
        assert specs[0]["name"] == "from_pm"


class TestRemovedYAGNIPaths:
    """Speculative paths that were removed should no longer extract specs."""

    def test_parameter_details_not_supported(self) -> None:
        payload = {"parameterDetails": {"p1": {"type": "string"}}}
        specs = extract_param_specs(payload)
        assert specs == []

    def test_param_details_not_supported(self) -> None:
        payload = {"paramDetails": {"p1": {"type": "string"}}}
        specs = extract_param_specs(payload)
        assert specs == []

    def test_question_parameters_not_supported(self) -> None:
        payload = {"question": {"parameters": [{"name": "p1", "type": "string"}]}}
        specs = extract_param_specs(payload)
        assert specs == []


class TestEdgeCases:
    def test_empty_payload(self) -> None:
        assert extract_param_specs({}) == []

    def test_non_dict_search_config_ignored(self) -> None:
        payload = {"searchConfig": "not_a_dict"}
        specs = extract_param_specs(payload)
        assert specs == []

    def test_falsy_top_level_falls_through_to_search_config(self) -> None:
        payload = {
            "parameters": [],
            "paramMap": {},
            "searchConfig": {"parameters": [{"name": "p1", "type": "string"}]},
        }
        specs = extract_param_specs(payload)
        assert len(specs) == 1
        assert specs[0]["name"] == "p1"

    def test_skips_non_dict_items_in_list(self) -> None:
        payload = {"parameters": [{"name": "p1", "type": "string"}, "bad", 42]}
        specs = extract_param_specs(payload)
        assert len(specs) == 1

    def test_skips_non_dict_values_in_dict(self) -> None:
        payload = {"parameters": {"p1": {"type": "string"}, "p2": "not_a_dict"}}
        specs = extract_param_specs(payload)
        assert len(specs) == 1

    def test_all_paths_empty_returns_empty(self) -> None:
        payload = {"parameters": [], "paramMap": {}, "searchConfig": {}}
        specs = extract_param_specs(payload)
        assert specs == []

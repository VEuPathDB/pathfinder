"""Unit tests for catalog search filtering by excluded param prefixes."""

from pathfinder.integrations.veupathdb.discovery import _filter_searches
from pathfinder.integrations.veupathdb.wdk_models import WDKSearch


def _search(url_segment: str, param_names: list[str]) -> WDKSearch:
    return WDKSearch(url_segment=url_segment, param_names=param_names)


def test_no_excluded_prefixes_returns_all_searches() -> None:
    searches = [
        _search("GenesByEda", ["eda_dataset", "eda_output"]),
        _search("GenesByText", ["text_expression"]),
    ]
    assert _filter_searches(searches, []) == searches


def test_excludes_search_whose_param_matches_prefix() -> None:
    searches = [
        _search("GenesByEda", ["eda_dataset", "eda_output"]),
        _search("GenesByText", ["text_expression"]),
    ]
    result = _filter_searches(searches, ["eda_"])
    assert len(result) == 1
    assert result[0].url_segment == "GenesByText"


def test_excludes_search_when_only_one_param_matches() -> None:
    searches = [
        _search("MixedSearch", ["normal_param", "eda_output"]),
        _search("CleanSearch", ["organism"]),
    ]
    result = _filter_searches(searches, ["eda_"])
    assert len(result) == 1
    assert result[0].url_segment == "CleanSearch"


def test_prefix_match_is_start_not_substring() -> None:
    searches = [_search("SafeSearch", ["dataset_eda_suffix"])]
    result = _filter_searches(searches, ["eda_"])
    assert len(result) == 1


def test_multiple_prefixes_exclude_on_any_match() -> None:
    searches = [
        _search("EdaSearch", ["eda_x"]),
        _search("FooSearch", ["foo_bar"]),
        _search("CleanSearch", ["organism"]),
    ]
    result = _filter_searches(searches, ["eda_", "foo_"])
    assert len(result) == 1
    assert result[0].url_segment == "CleanSearch"


def test_search_with_no_params_is_kept() -> None:
    searches = [_search("NoParams", [])]
    result = _filter_searches(searches, ["eda_"])
    assert len(result) == 1

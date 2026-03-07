"""Unit tests for services.strategies.serialization."""

from veupath_chatbot.services.strategies.serialization import (
    _parse_plan,
    build_steps_data_from_plan,
    count_steps_in_plan,
)


def _valid_plan() -> dict:
    return {
        "recordType": "gene",
        "root": {
            "id": "s1",
            "searchName": "GenesByTextSearch",
            "parameters": {"text_expression": "kinase"},
        },
    }


def _combine_plan() -> dict:
    return {
        "recordType": "gene",
        "root": {
            "id": "c1",
            "searchName": "BooleanQuestion",
            "parameters": {},
            "operator": "INTERSECT",
            "primaryInput": {
                "id": "s1",
                "searchName": "GenesByTextSearch",
                "parameters": {"text_expression": "kinase"},
            },
            "secondaryInput": {
                "id": "s2",
                "searchName": "GenesByGoTerm",
                "parameters": {"GoTerm": "GO:0003723"},
            },
        },
    }


# ── _parse_plan ───────────────────────────────────────────────────────


class TestParsePlan:
    def test_valid_plan(self) -> None:
        ast = _parse_plan(_valid_plan())
        assert ast is not None
        assert ast.record_type == "gene"
        assert ast.root.search_name == "GenesByTextSearch"

    def test_invalid_plan_returns_none(self) -> None:
        # Missing recordType
        assert _parse_plan({"root": {"searchName": "S1"}}) is None

    def test_empty_dict_returns_none(self) -> None:
        assert _parse_plan({}) is None

    def test_malformed_root_returns_none(self) -> None:
        assert _parse_plan({"recordType": "gene", "root": "not-a-dict"}) is None


# ── build_steps_data_from_plan ────────────────────────────────────────


class TestBuildStepsDataFromPlan:
    def test_single_step_plan(self) -> None:
        result = build_steps_data_from_plan(_valid_plan())
        assert len(result) == 1
        assert result[0]["id"] == "s1"
        assert result[0]["searchName"] == "GenesByTextSearch"

    def test_combine_plan(self) -> None:
        result = build_steps_data_from_plan(_combine_plan())
        assert len(result) == 3
        ids = [s["id"] for s in result]
        assert "s1" in ids
        assert "s2" in ids
        assert "c1" in ids

    def test_invalid_plan_returns_empty(self) -> None:
        result = build_steps_data_from_plan({})
        assert result == []

    def test_missing_search_name_returns_empty(self) -> None:
        plan = {"recordType": "gene", "root": {"parameters": {}}}
        result = build_steps_data_from_plan(plan)
        assert result == []


# ── count_steps_in_plan ───────────────────────────────────────────────


class TestCountStepsInPlan:
    def test_single_step(self) -> None:
        assert count_steps_in_plan(_valid_plan()) == 1

    def test_combine_plan(self) -> None:
        assert count_steps_in_plan(_combine_plan()) == 3

    def test_invalid_plan(self) -> None:
        assert count_steps_in_plan({}) == 0

    def test_transform_plan(self) -> None:
        plan = {
            "recordType": "gene",
            "root": {
                "id": "t1",
                "searchName": "GenesByOrthologs",
                "parameters": {},
                "primaryInput": {
                    "id": "s1",
                    "searchName": "GenesByTextSearch",
                    "parameters": {},
                },
            },
        }
        assert count_steps_in_plan(plan) == 2

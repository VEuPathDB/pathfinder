"""Unit tests for services.strategies.plan_validation."""

import pytest

from veupath_chatbot.platform.errors import ValidationError
from veupath_chatbot.services.strategies.plan_validation import validate_plan_or_raise


def _valid_plan() -> dict:
    return {
        "recordType": "gene",
        "root": {
            "id": "s1",
            "searchName": "GenesByTextSearch",
            "parameters": {"text_expression": "kinase"},
        },
    }


class TestValidatePlanOrRaise:
    def test_valid_plan_returns_ast(self) -> None:
        ast = validate_plan_or_raise(_valid_plan())
        assert ast.record_type == "gene"
        assert ast.root.search_name == "GenesByTextSearch"
        assert ast.root.id == "s1"

    def test_missing_record_type_raises(self) -> None:
        plan = {"root": {"searchName": "S1", "parameters": {}}}
        with pytest.raises(ValidationError) as exc_info:
            validate_plan_or_raise(plan)
        assert "Invalid plan" in exc_info.value.title

    def test_missing_root_raises(self) -> None:
        plan = {"recordType": "gene"}
        with pytest.raises(ValidationError) as exc_info:
            validate_plan_or_raise(plan)
        assert exc_info.value.errors is not None

    def test_missing_search_name_raises(self) -> None:
        plan = {"recordType": "gene", "root": {"parameters": {}}}
        with pytest.raises(ValidationError):
            validate_plan_or_raise(plan)

    def test_combine_without_operator_raises(self) -> None:
        plan = {
            "recordType": "gene",
            "root": {
                "searchName": "BooleanQuestion",
                "parameters": {},
                "primaryInput": {
                    "searchName": "S1",
                    "parameters": {},
                },
                "secondaryInput": {
                    "searchName": "S2",
                    "parameters": {},
                },
            },
        }
        with pytest.raises(ValidationError):
            validate_plan_or_raise(plan)

    def test_valid_combine_plan(self) -> None:
        plan = {
            "recordType": "gene",
            "root": {
                "searchName": "BooleanQuestion",
                "parameters": {},
                "operator": "INTERSECT",
                "primaryInput": {
                    "searchName": "S1",
                    "parameters": {},
                },
                "secondaryInput": {
                    "searchName": "S2",
                    "parameters": {},
                },
            },
        }
        ast = validate_plan_or_raise(plan)
        assert ast.root.infer_kind() == "combine"
        assert ast.root.operator is not None
        assert ast.root.operator.value == "INTERSECT"

    def test_valid_transform_plan(self) -> None:
        plan = {
            "recordType": "gene",
            "root": {
                "searchName": "GenesByOrthologs",
                "parameters": {},
                "primaryInput": {
                    "searchName": "GenesByTextSearch",
                    "parameters": {},
                },
            },
        }
        ast = validate_plan_or_raise(plan)
        assert ast.root.infer_kind() == "transform"

    def test_secondary_without_primary_raises(self) -> None:
        """secondaryInput requires primaryInput in the AST parser."""
        plan = {
            "recordType": "gene",
            "root": {
                "searchName": "BooleanQuestion",
                "parameters": {},
                "operator": "INTERSECT",
                "secondaryInput": {
                    "searchName": "S2",
                    "parameters": {},
                },
            },
        }
        with pytest.raises(ValidationError):
            validate_plan_or_raise(plan)

    def test_errors_contain_code(self) -> None:
        """Errors should contain code information."""
        plan = {"recordType": "gene", "root": "not-a-dict"}
        with pytest.raises(ValidationError) as exc_info:
            validate_plan_or_raise(plan)
        assert exc_info.value.errors is not None
        assert len(exc_info.value.errors) > 0
        error = exc_info.value.errors[0]
        assert "code" in error

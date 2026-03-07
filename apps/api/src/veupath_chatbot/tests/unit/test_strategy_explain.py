"""Tests for strategy explain helpers."""

from veupath_chatbot.domain.strategy.explain import explain_operation
from veupath_chatbot.domain.strategy.ops import CombineOp


class TestExplainOperation:
    def test_all_ops_have_explanations(self) -> None:
        for op in CombineOp:
            explanation = explain_operation(op)
            assert isinstance(explanation, str)
            assert len(explanation) > 10

    def test_intersect_mentions_both(self) -> None:
        assert "both" in explain_operation(CombineOp.INTERSECT).lower()

    def test_union_mentions_either(self) -> None:
        assert "either" in explain_operation(CombineOp.UNION).lower()

    def test_minus_and_lonly_same(self) -> None:
        assert explain_operation(CombineOp.MINUS) == explain_operation(CombineOp.LONLY)

    def test_rminus_and_ronly_same(self) -> None:
        assert explain_operation(CombineOp.RMINUS) == explain_operation(CombineOp.RONLY)

    def test_colocate_mentions_genomic(self) -> None:
        assert "genomic" in explain_operation(CombineOp.COLOCATE).lower()

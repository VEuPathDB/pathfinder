"""Tests for ai.tools.strategy_tools.step_ops -- WDK boolean coercion and step creation validation."""

from veupath_chatbot.ai.tools.strategy_tools.step_ops import StrategyStepOps
from veupath_chatbot.domain.strategy.ast import PlanStepNode
from veupath_chatbot.domain.strategy.session import StrategySession


def _make_step_ops() -> StrategyStepOps:
    """Create a StrategyStepOps instance with a real session (no external calls needed)."""
    session = StrategySession("plasmodb")
    ops = StrategyStepOps.__new__(StrategyStepOps)
    ops.session = session
    return ops


# -- _coerce_wdk_boolean_question_params --


class TestCoerceWdkBooleanQuestionParams:
    """Test the pure extraction of bq_left_op_, bq_right_op_, bq_operator from parameters."""

    def test_extracts_boolean_question_params(self):
        ops = _make_step_ops()
        params = {
            "bq_left_op_": "step_1",
            "bq_right_op_": "step_2",
            "bq_operator": "INTERSECT",
        }
        left, right, op = ops._coerce_wdk_boolean_question_params(parameters=params)
        assert left == "step_1"
        assert right == "step_2"
        assert op == "INTERSECT"
        # Should remove the bq_ keys from parameters
        assert "bq_left_op_" not in params
        assert "bq_right_op_" not in params
        assert "bq_operator" not in params

    def test_returns_none_when_missing_all(self):
        ops = _make_step_ops()
        params = {"some_param": "value"}
        left, right, op = ops._coerce_wdk_boolean_question_params(parameters=params)
        assert left is None
        assert right is None
        assert op is None

    def test_returns_none_when_only_left_present(self):
        ops = _make_step_ops()
        params = {"bq_left_op_": "step_1"}
        left, right, op = ops._coerce_wdk_boolean_question_params(parameters=params)
        assert left is None
        assert right is None
        assert op is None

    def test_returns_none_when_operator_missing(self):
        ops = _make_step_ops()
        params = {"bq_left_op_": "step_1", "bq_right_op_": "step_2"}
        left, right, op = ops._coerce_wdk_boolean_question_params(parameters=params)
        assert left is None
        assert right is None
        assert op is None

    def test_returns_none_for_empty_params(self):
        ops = _make_step_ops()
        left, right, op = ops._coerce_wdk_boolean_question_params(parameters={})
        assert left is None
        assert right is None
        assert op is None

    def test_handles_suffixed_bq_keys(self):
        """WDK may use bq_left_op_XYZ style keys (anything starting with bq_left_op)."""
        ops = _make_step_ops()
        params = {
            "bq_left_op_some_suffix": "step_a",
            "bq_right_op_another": "step_b",
            "bq_operator": "UNION",
        }
        left, right, op = ops._coerce_wdk_boolean_question_params(parameters=params)
        assert left == "step_a"
        assert right == "step_b"
        assert op == "UNION"


# -- create_step validation (no external calls) --


async def test_create_step_graph_not_found():
    """When session has no graph, create_step returns graph-not-found error."""
    session = StrategySession("plasmodb")
    ops = StrategyStepOps.__new__(StrategyStepOps)
    ops.session = session

    result = await ops.create_step(search_name="GenesByText", graph_id="missing")
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"


async def test_create_step_secondary_without_primary():
    """Secondary input without primary should be rejected."""
    session = StrategySession("plasmodb")
    graph = session.create_graph("test", graph_id="g1")
    step_a = PlanStepNode(search_name="A", parameters={})
    step_b = PlanStepNode(search_name="B", parameters={})
    graph.add_step(step_a)
    graph.add_step(step_b)

    ops = StrategyStepOps.__new__(StrategyStepOps)
    ops.session = session

    result = await ops.create_step(
        secondary_input_step_id=step_b.id,
        operator="UNION",
        graph_id="g1",
    )
    assert result["ok"] is False
    assert "primary_input_step_id" in str(result["message"])


async def test_create_step_secondary_without_operator():
    """Secondary input without operator should be rejected."""
    session = StrategySession("plasmodb")
    graph = session.create_graph("test", graph_id="g1")
    step_a = PlanStepNode(search_name="A", parameters={})
    step_b = PlanStepNode(search_name="B", parameters={})
    graph.add_step(step_a)
    graph.add_step(step_b)

    ops = StrategyStepOps.__new__(StrategyStepOps)
    ops.session = session

    result = await ops.create_step(
        primary_input_step_id=step_a.id,
        secondary_input_step_id=step_b.id,
        graph_id="g1",
    )
    assert result["ok"] is False
    assert "operator is required" in str(result["message"])


async def test_create_step_leaf_requires_search_name():
    """Leaf steps (no inputs) require search_name."""
    session = StrategySession("plasmodb")
    session.create_graph("test", graph_id="g1")

    ops = StrategyStepOps.__new__(StrategyStepOps)
    ops.session = session

    result = await ops.create_step(graph_id="g1")
    assert result["ok"] is False
    assert "search_name is required" in str(result["message"])


async def test_create_step_primary_input_not_found():
    """Referencing a non-existent primary input step should fail."""
    session = StrategySession("plasmodb")
    session.create_graph("test", graph_id="g1")

    ops = StrategyStepOps.__new__(StrategyStepOps)
    ops.session = session

    result = await ops.create_step(
        primary_input_step_id="nonexistent",
        search_name="SomeTransform",
        graph_id="g1",
    )
    assert result["ok"] is False
    assert result["code"] == "STEP_NOT_FOUND"


async def test_create_step_secondary_input_not_found():
    """Referencing a non-existent secondary input step should fail."""
    session = StrategySession("plasmodb")
    graph = session.create_graph("test", graph_id="g1")
    step_a = PlanStepNode(search_name="A", parameters={})
    graph.add_step(step_a)

    ops = StrategyStepOps.__new__(StrategyStepOps)
    ops.session = session

    result = await ops.create_step(
        primary_input_step_id=step_a.id,
        secondary_input_step_id="nonexistent",
        operator="UNION",
        graph_id="g1",
    )
    assert result["ok"] is False
    assert result["code"] == "STEP_NOT_FOUND"


async def test_create_step_rejects_non_root_primary_input():
    """A step already consumed by another step cannot be used as primary input."""
    session = StrategySession("plasmodb")
    graph = session.create_graph("test", graph_id="g1")
    step_a = PlanStepNode(search_name="A", parameters={})
    step_b = PlanStepNode(search_name="B", parameters={})
    graph.add_step(step_a)
    graph.add_step(step_b)

    # Create a combine that consumes both step_a and step_b
    combine = PlanStepNode(
        search_name="__combine__",
        parameters={},
        primary_input=step_a,
        secondary_input=step_b,
    )
    combine.operator = None  # will be set by parse_op
    graph.add_step(combine)

    ops = StrategyStepOps.__new__(StrategyStepOps)
    ops.session = session

    # Try to use step_a again as primary input -- it's not a root anymore
    result = await ops.create_step(
        search_name="SomeSearch",
        primary_input_step_id=step_a.id,
        graph_id="g1",
    )
    assert result["ok"] is False
    assert "not a subtree root" in str(result["message"])

"""Tests for ai.tools.strategy_tools.attachment_ops -- filter/analysis/report attachments."""

from veupath_chatbot.ai.tools.strategy_tools.attachment_ops import StrategyAttachmentOps
from veupath_chatbot.domain.strategy.ast import PlanStepNode
from veupath_chatbot.domain.strategy.session import StrategySession


def _make_attachment_ops() -> tuple[StrategyAttachmentOps, str]:
    session = StrategySession("plasmodb")
    graph = session.create_graph("test", graph_id="g1")
    graph.record_type = "gene"
    step = PlanStepNode(search_name="GenesByText", parameters={"text": "kinase"})
    graph.add_step(step)

    ops = StrategyAttachmentOps.__new__(StrategyAttachmentOps)
    ops.session = session
    return ops, step.id


# -- add_step_filter --


async def test_add_filter_attaches_to_step():
    ops, step_id = _make_attachment_ops()

    result = await ops.add_step_filter(
        step_id=step_id,
        filter_name="organism_filter",
        value="Plasmodium falciparum 3D7",
        graph_id="g1",
    )

    assert result["ok"] is True
    graph = ops.session.get_graph("g1")
    step = graph.get_step(step_id)
    assert len(step.filters) == 1
    assert step.filters[0].name == "organism_filter"
    assert step.filters[0].value == "Plasmodium falciparum 3D7"
    assert step.filters[0].disabled is False


async def test_add_filter_disabled():
    ops, step_id = _make_attachment_ops()

    await ops.add_step_filter(
        step_id=step_id,
        filter_name="f",
        value="v",
        disabled=True,
        graph_id="g1",
    )

    graph = ops.session.get_graph("g1")
    step = graph.get_step(step_id)
    assert step.filters[0].disabled is True


async def test_add_filter_replaces_existing_by_name():
    ops, step_id = _make_attachment_ops()

    await ops.add_step_filter(
        step_id=step_id, filter_name="f", value="old", graph_id="g1"
    )
    await ops.add_step_filter(
        step_id=step_id, filter_name="f", value="new", graph_id="g1"
    )

    graph = ops.session.get_graph("g1")
    step = graph.get_step(step_id)
    # Should only have one filter with the updated value
    matching = [f for f in step.filters if f.name == "f"]
    assert len(matching) == 1
    assert matching[0].value == "new"


async def test_add_filter_step_not_found():
    ops, _ = _make_attachment_ops()

    result = await ops.add_step_filter(
        step_id="missing", filter_name="f", value="v", graph_id="g1"
    )

    assert result["ok"] is False
    assert result["code"] == "STEP_NOT_FOUND"


# -- add_step_analysis --


async def test_add_analysis_attaches_to_step():
    ops, step_id = _make_attachment_ops()

    result = await ops.add_step_analysis(
        step_id=step_id,
        analysis_type="word_enrichment",
        parameters={"threshold": 0.05},
        custom_name="GO enrichment",
        graph_id="g1",
    )

    assert result["ok"] is True
    graph = ops.session.get_graph("g1")
    step = graph.get_step(step_id)
    assert len(step.analyses) == 1
    assert step.analyses[0].analysis_type == "word_enrichment"
    assert step.analyses[0].parameters == {"threshold": 0.05}
    assert step.analyses[0].custom_name == "GO enrichment"


async def test_add_analysis_defaults():
    ops, step_id = _make_attachment_ops()

    await ops.add_step_analysis(
        step_id=step_id, analysis_type="histogram", graph_id="g1"
    )

    graph = ops.session.get_graph("g1")
    step = graph.get_step(step_id)
    assert step.analyses[0].parameters == {}
    assert step.analyses[0].custom_name is None


async def test_add_analysis_step_not_found():
    ops, _ = _make_attachment_ops()

    result = await ops.add_step_analysis(
        step_id="missing", analysis_type="x", graph_id="g1"
    )

    assert result["ok"] is False
    assert result["code"] == "STEP_NOT_FOUND"


async def test_add_multiple_analyses():
    ops, step_id = _make_attachment_ops()

    await ops.add_step_analysis(
        step_id=step_id, analysis_type="enrichment", graph_id="g1"
    )
    await ops.add_step_analysis(
        step_id=step_id, analysis_type="histogram", graph_id="g1"
    )

    graph = ops.session.get_graph("g1")
    step = graph.get_step(step_id)
    assert len(step.analyses) == 2


# -- add_step_report --


async def test_add_report_attaches_to_step():
    ops, step_id = _make_attachment_ops()

    result = await ops.add_step_report(
        step_id=step_id,
        report_name="tabular",
        config={"attributes": ["gene_id", "product"]},
        graph_id="g1",
    )

    assert result["ok"] is True
    graph = ops.session.get_graph("g1")
    step = graph.get_step(step_id)
    assert len(step.reports) == 1
    assert step.reports[0].report_name == "tabular"
    assert step.reports[0].config == {"attributes": ["gene_id", "product"]}


async def test_add_report_default_name():
    ops, step_id = _make_attachment_ops()

    await ops.add_step_report(step_id=step_id, graph_id="g1")

    graph = ops.session.get_graph("g1")
    step = graph.get_step(step_id)
    assert step.reports[0].report_name == "standard"


async def test_add_report_step_not_found():
    ops, _ = _make_attachment_ops()

    result = await ops.add_step_report(step_id="missing", graph_id="g1")

    assert result["ok"] is False
    assert result["code"] == "STEP_NOT_FOUND"

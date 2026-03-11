"""Unit tests for WorkbenchAgent tool composition."""

from unittest.mock import MagicMock
from uuid import uuid4

from veupath_chatbot.ai.agents.workbench import WorkbenchAgent


class TestWorkbenchAgentToolDiscovery:
    def _make_agent(self) -> WorkbenchAgent:
        engine = MagicMock()
        engine.max_context_size = 8192
        return WorkbenchAgent(
            engine=engine,
            site_id="plasmodb",
            experiment_id="exp-1",
            user_id=uuid4(),
        )

    def test_has_research_tools(self) -> None:
        agent = self._make_agent()
        names = set(agent.functions)
        assert "web_search" in names
        assert "literature_search" in names

    def test_has_workbench_read_tools(self) -> None:
        agent = self._make_agent()
        names = set(agent.functions)
        assert "get_evaluation_summary" in names
        assert "get_enrichment_results" in names
        assert "get_confidence_scores" in names
        assert "get_step_contributions" in names
        assert "get_experiment_config" in names
        assert "get_ensemble_analysis" in names
        assert "get_result_gene_lists" in names

    def test_has_analysis_tools(self) -> None:
        agent = self._make_agent()
        names = set(agent.functions)
        assert "fetch_result_records" in names
        assert "lookup_gene_detail" in names
        assert "compare_gene_groups" in names
        assert "get_attribute_distribution" in names
        assert "search_results" in names

    def test_has_refinement_tools(self) -> None:
        agent = self._make_agent()
        names = set(agent.functions)
        assert "refine_with_search" in names
        assert "refine_with_gene_ids" in names
        assert "re_evaluate_controls" in names

    def test_has_gene_lookup_tools(self) -> None:
        agent = self._make_agent()
        names = set(agent.functions)
        assert "lookup_gene_records" in names

    def test_has_workbench_gene_set_tools(self) -> None:
        agent = self._make_agent()
        names = set(agent.functions)
        assert "create_workbench_gene_set" in names
        assert "run_gene_set_enrichment" in names
        assert "list_workbench_gene_sets" in names

    def test_has_catalog_tools(self) -> None:
        agent = self._make_agent()
        names = set(agent.functions)
        assert "search_for_searches" in names
        assert "get_search_parameters" in names
        assert "get_record_types" in names

    def test_stores_experiment_id(self) -> None:
        agent = self._make_agent()
        assert agent.experiment_id == "exp-1"
        assert agent.site_id == "plasmodb"

"""Tests for ExperimentToolsMixin — control test delegation."""

from unittest.mock import AsyncMock, patch

from veupath_chatbot.ai.tools.planner.experiment_tools import ExperimentToolsMixin

_SITE_ID = "plasmodb"


class _TestableTools(ExperimentToolsMixin):
    """Concrete subclass for testing."""

    def __init__(self, site_id: str = _SITE_ID) -> None:
        self.site_id = site_id


class TestRunControlTests:
    async def test_delegates_all_args(self) -> None:
        tools = _TestableTools()
        expected = {"positiveRecall": 0.8, "negativeExclusion": 1.0}

        with patch(
            "veupath_chatbot.ai.tools.planner.experiment_tools.run_positive_negative_controls",
            new_callable=AsyncMock,
            return_value=expected,
        ) as mock_run:
            result = await tools.run_control_tests(
                record_type="gene",
                target_search_name="GenesByTextSearch",
                target_parameters={"text_expression": "kinase"},
                controls_search_name="GeneByLocusTag",
                controls_param_name="ds_gene_ids",
                positive_controls=["PF3D7_0100100"],
                negative_controls=["PF3D7_0200200"],
                controls_value_format="newline",
                controls_extra_parameters={"organism": "P. falciparum 3D7"},
                id_field="gene_source_id",
            )

        assert result == expected
        mock_run.assert_awaited_once_with(
            site_id=_SITE_ID,
            record_type="gene",
            target_search_name="GenesByTextSearch",
            target_parameters={"text_expression": "kinase"},
            controls_search_name="GeneByLocusTag",
            controls_param_name="ds_gene_ids",
            positive_controls=["PF3D7_0100100"],
            negative_controls=["PF3D7_0200200"],
            controls_value_format="newline",
            controls_extra_parameters={"organism": "P. falciparum 3D7"},
            id_field="gene_source_id",
        )

    async def test_defaults_for_optional_args(self) -> None:
        tools = _TestableTools()

        with patch(
            "veupath_chatbot.ai.tools.planner.experiment_tools.run_positive_negative_controls",
            new_callable=AsyncMock,
            return_value={},
        ) as mock_run:
            await tools.run_control_tests(
                record_type="gene",
                target_search_name="GenesByTextSearch",
                target_parameters={"text_expression": "kinase"},
                controls_search_name="GeneByLocusTag",
                controls_param_name="ds_gene_ids",
            )

        mock_run.assert_awaited_once_with(
            site_id=_SITE_ID,
            record_type="gene",
            target_search_name="GenesByTextSearch",
            target_parameters={"text_expression": "kinase"},
            controls_search_name="GeneByLocusTag",
            controls_param_name="ds_gene_ids",
            positive_controls=None,
            negative_controls=None,
            controls_value_format="newline",
            controls_extra_parameters=None,
            id_field=None,
        )

    async def test_none_target_parameters_becomes_empty_dict(self) -> None:
        """target_parameters or {} ensures None is converted to empty dict."""
        tools = _TestableTools()

        with patch(
            "veupath_chatbot.ai.tools.planner.experiment_tools.run_positive_negative_controls",
            new_callable=AsyncMock,
            return_value={},
        ) as mock_run:
            await tools.run_control_tests(
                record_type="gene",
                target_search_name="GenesByTextSearch",
                target_parameters=None,
                controls_search_name="GeneByLocusTag",
                controls_param_name="ds_gene_ids",
            )

        # target_parameters should be {} when None is passed
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["target_parameters"] == {}

    async def test_uses_instance_site_id(self) -> None:
        tools = _TestableTools(site_id="toxodb")

        with patch(
            "veupath_chatbot.ai.tools.planner.experiment_tools.run_positive_negative_controls",
            new_callable=AsyncMock,
            return_value={},
        ) as mock_run:
            await tools.run_control_tests(
                record_type="gene",
                target_search_name="Search",
                target_parameters={},
                controls_search_name="CtrlSearch",
                controls_param_name="ids",
            )

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["site_id"] == "toxodb"

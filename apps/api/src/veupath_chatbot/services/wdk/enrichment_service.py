"""Unified enrichment service.

Single entry point for running enrichment analyses regardless of
whether the caller is an experiment endpoint, gene set endpoint,
or AI tool.
"""

import asyncio

from veupath_chatbot.domain.strategy.ast import StepTreeNode
from veupath_chatbot.integrations.veupathdb.factory import get_strategy_api
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONObject
from veupath_chatbot.services.control_helpers import delete_temp_strategy
from veupath_chatbot.services.experiment.enrichment import (
    _execute_analysis,
    run_enrichment_analysis,
    run_enrichment_on_step,
)
from veupath_chatbot.services.experiment.helpers import coerce_step_id, extract_wdk_id
from veupath_chatbot.services.experiment.types import (
    EnrichmentAnalysisType,
    EnrichmentResult,
)

logger = get_logger(__name__)


class EnrichmentService:
    """Unified enrichment dispatcher."""

    async def run(
        self,
        *,
        site_id: str,
        analysis_type: EnrichmentAnalysisType,
        step_id: int | None = None,
        search_name: str | None = None,
        record_type: str | None = None,
        parameters: JSONObject | None = None,
    ) -> EnrichmentResult:
        """Run a single enrichment analysis.

        If step_id is provided, runs on the existing step.
        Otherwise creates a temporary strategy from search_name/parameters.
        """
        if step_id is not None:
            return await run_enrichment_on_step(
                site_id=site_id,
                step_id=step_id,
                analysis_type=analysis_type,
            )
        if search_name and parameters is not None:
            return await run_enrichment_analysis(
                site_id=site_id,
                record_type=record_type or "gene",
                search_name=search_name,
                parameters=parameters,
                analysis_type=analysis_type,
            )
        raise ValueError("Either step_id or search_name+parameters required")

    async def run_batch(
        self,
        *,
        site_id: str,
        analysis_types: list[EnrichmentAnalysisType],
        step_id: int | None = None,
        search_name: str | None = None,
        record_type: str | None = None,
        parameters: JSONObject | None = None,
    ) -> tuple[list[EnrichmentResult], list[str]]:
        """Run multiple enrichment analyses concurrently on a shared step.

        When no step_id is provided (paste gene sets), creates ONE temporary
        WDK step/strategy and runs all analysis types against it — instead
        of creating N separate temp strategies. This reduces WDK API calls
        from ~5N to ~N+3 and avoids rate-limit 500s.
        """
        errors: list[str] = []

        # If we already have a step, run all analyses on it directly.
        if step_id is not None:
            return await self._run_analyses_on_step(
                site_id,
                step_id,
                analysis_types,
                errors,
            )

        # No step — need search_name + parameters to create one.
        if not search_name or parameters is None:
            raise ValueError("Either step_id or search_name+parameters required")

        # Create ONE temp step/strategy, run all analyses, then clean up.
        api = get_strategy_api(site_id)
        step = await api.create_step(
            record_type=record_type or "gene",
            search_name=search_name,
            parameters=parameters or {},
            custom_name="Enrichment target",
        )
        shared_step_id = coerce_step_id(step)
        root = StepTreeNode(shared_step_id)
        strategy_id: int | None = None

        try:
            created = await api.create_strategy(
                step_tree=root,
                name="Pathfinder enrichment analysis",
                description=None,
                is_internal=True,
            )
            strategy_id = extract_wdk_id(created)

            return await self._run_analyses_on_step(
                site_id,
                shared_step_id,
                analysis_types,
                errors,
            )
        finally:
            await delete_temp_strategy(api, strategy_id)

    async def _run_analyses_on_step(
        self,
        site_id: str,
        step_id: int,
        analysis_types: list[EnrichmentAnalysisType],
        errors: list[str],
    ) -> tuple[list[EnrichmentResult], list[str]]:
        """Run multiple analysis types on a single step concurrently."""
        api = get_strategy_api(site_id)

        async def _run_one(analysis_type: EnrichmentAnalysisType) -> EnrichmentResult:
            try:
                return await _execute_analysis(api, step_id, analysis_type)
            except Exception as exc:
                logger.warning(
                    "Enrichment failed",
                    analysis_type=analysis_type,
                    error=str(exc),
                )
                error_msg = str(exc)
                errors.append(f"{analysis_type}: {error_msg}")
                return EnrichmentResult(
                    analysis_type=analysis_type,
                    terms=[],
                    total_genes_analyzed=0,
                    background_size=0,
                    error=error_msg,
                )

        results = list(await asyncio.gather(*[_run_one(at) for at in analysis_types]))
        return results, errors

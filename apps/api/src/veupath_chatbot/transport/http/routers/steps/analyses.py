"""Step analysis endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from veupath_chatbot.domain.strategy.ast import StepAnalysis
from veupath_chatbot.integrations.veupathdb.factory import get_strategy_api
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONArray, JSONObject
from veupath_chatbot.transport.http.deps import CurrentUser, StreamRepo
from veupath_chatbot.transport.http.routers.steps._shared import (
    get_step_or_404,
    parse_analyses,
    refresh_step_after_update,
    require_wdk_step_id,
    update_plan,
)
from veupath_chatbot.transport.http.schemas import (
    StepAnalysisRequest,
    StepAnalysisResponse,
    StepAnalysisRunResponse,
)

router = APIRouter(prefix="/api/v1/strategies/{strategyId}/steps", tags=["steps"])
logger = get_logger(__name__)


@router.get("/{step_id}/analysis-types", response_model=JSONArray)
async def list_analysis_types(
    strategyId: UUID,
    step_id: str,
    stream_repo: StreamRepo,
    user_id: CurrentUser,
) -> JSONArray:
    """List available analysis types for a step."""
    projection, plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )
    wdk_step_id = require_wdk_step_id(step)
    api = get_strategy_api(projection.site_id)
    return await api.list_analysis_types(wdk_step_id)


@router.get("/{step_id}/analysis-types/{analysis_type}", response_model=JSONObject)
async def get_analysis_type(
    strategyId: UUID,
    step_id: str,
    analysis_type: str,
    stream_repo: StreamRepo,
    user_id: CurrentUser,
) -> JSONObject:
    """Get analysis form metadata for a step."""
    projection, plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )
    wdk_step_id = require_wdk_step_id(step)
    api = get_strategy_api(projection.site_id)
    return await api.get_analysis_type(wdk_step_id, analysis_type)


@router.get("/{step_id}/analyses", response_model=JSONArray)
async def list_step_analyses(
    strategyId: UUID, step_id: str, stream_repo: StreamRepo, user_id: CurrentUser
) -> JSONArray:
    """List analysis instances for a step."""
    projection, plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )
    wdk_step_id = require_wdk_step_id(step)
    api = get_strategy_api(projection.site_id)
    return await api.list_step_analyses(wdk_step_id)


@router.post("/{step_id}/analyses", response_model=StepAnalysisRunResponse)
async def run_step_analysis(
    strategyId: UUID,
    step_id: str,
    request: StepAnalysisRequest,
    stream_repo: StreamRepo,
    user_id: CurrentUser,
) -> StepAnalysisRunResponse:
    """Run a step analysis and attach it locally."""
    projection, plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )

    analyses = list(parse_analyses(step.get("analyses")))
    analyses.append(
        StepAnalysis(
            analysis_type=request.analysis_type,
            parameters=request.parameters,
            custom_name=request.custom_name,
        )
    )

    updated_plan = update_plan(
        plan, step_id, {"analyses": [a.to_dict() for a in analyses]}
    )
    await stream_repo.update_projection(strategyId, plan=updated_plan)

    wdk_result: JSONObject | None = None
    updated_step = refresh_step_after_update(updated_plan, step_id, step)
    wdk_step_id_raw = updated_step.get("wdkStepId")
    if isinstance(wdk_step_id_raw, int) and projection.site_id:
        try:
            api = get_strategy_api(projection.site_id)
            wdk_result_raw = await api.run_step_analysis(
                step_id=wdk_step_id_raw,
                analysis_type=request.analysis_type,
                parameters=request.parameters,
                custom_name=request.custom_name,
            )
            wdk_result = wdk_result_raw if isinstance(wdk_result_raw, dict) else None
        except Exception as e:
            logger.warning("WDK analysis failed", error=str(e))

    return StepAnalysisRunResponse(
        analysis=StepAnalysisResponse.model_validate(analyses[-1].to_dict()),
        wdk=wdk_result,
    )

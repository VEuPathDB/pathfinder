"""Step filter endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from veupath_chatbot.domain.strategy.ast import StepFilter
from veupath_chatbot.integrations.veupathdb.factory import get_strategy_api
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONArray
from veupath_chatbot.transport.http.deps import CurrentUser, StreamRepo
from veupath_chatbot.transport.http.routers.steps._shared import (
    get_step_or_404,
    parse_filters,
    refresh_step_after_update,
    require_wdk_step_id,
    update_plan,
)
from veupath_chatbot.transport.http.schemas import (
    StepFilterRequest,
    StepFilterResponse,
    StepFiltersResponse,
)

router = APIRouter(prefix="/api/v1/strategies/{strategyId}/steps", tags=["steps"])
logger = get_logger(__name__)


@router.get("/{step_id}/filters", response_model=list[StepFilterResponse])
async def list_step_filters(
    strategyId: UUID,
    step_id: str,
    stream_repo: StreamRepo,
    user_id: CurrentUser,
) -> list[StepFilterResponse]:
    """List filters attached to a step."""
    _projection, _plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )
    filters_raw = step.get("filters", [])
    if not isinstance(filters_raw, list):
        return []
    return [
        StepFilterResponse.model_validate(f) for f in filters_raw if isinstance(f, dict)
    ]


@router.get("/{step_id}/filters/available", response_model=JSONArray)
async def list_available_filters(
    strategyId: UUID, step_id: str, stream_repo: StreamRepo, user_id: CurrentUser
) -> JSONArray:
    """List available filters for a step (WDK-backed)."""
    projection, plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )
    wdk_step_id = require_wdk_step_id(step)
    api = get_strategy_api(projection.site_id)
    return await api.list_step_filters(wdk_step_id)


@router.put("/{step_id}/filters/{filter_name}", response_model=StepFiltersResponse)
async def set_step_filter(
    strategyId: UUID,
    step_id: str,
    filter_name: str,
    request: StepFilterRequest,
    stream_repo: StreamRepo,
    user_id: CurrentUser,
) -> StepFiltersResponse:
    """Add or update a filter for a step."""
    projection, plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )

    filters = [f for f in parse_filters(step.get("filters")) if f.name != filter_name]
    filters.append(
        StepFilter(name=filter_name, value=request.value, disabled=request.disabled)
    )

    updated_plan = update_plan(
        plan, step_id, {"filters": [f.to_dict() for f in filters]}
    )
    await stream_repo.update_projection(strategyId, plan=updated_plan)

    updated_step = refresh_step_after_update(updated_plan, step_id, step)
    wdk_step_id_raw = updated_step.get("wdkStepId")
    if isinstance(wdk_step_id_raw, int) and projection.site_id:
        try:
            api = get_strategy_api(projection.site_id)
            await api.set_step_filter(
                step_id=wdk_step_id_raw,
                filter_name=filter_name,
                value=request.value,
                disabled=request.disabled,
            )
        except Exception as e:
            logger.warning("WDK filter update failed", error=str(e))

    return StepFiltersResponse(
        filters=[StepFilterResponse.model_validate(f.to_dict()) for f in filters]
    )


@router.delete("/{step_id}/filters/{filter_name}", response_model=StepFiltersResponse)
async def delete_step_filter(
    strategyId: UUID,
    step_id: str,
    filter_name: str,
    stream_repo: StreamRepo,
    user_id: CurrentUser,
) -> StepFiltersResponse:
    """Remove a filter from a step."""
    projection, plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )

    filters = [f for f in parse_filters(step.get("filters")) if f.name != filter_name]
    updated_plan = update_plan(
        plan, step_id, {"filters": [f.to_dict() for f in filters]}
    )
    await stream_repo.update_projection(strategyId, plan=updated_plan)

    updated_step = refresh_step_after_update(updated_plan, step_id, step)
    wdk_step_id_raw = updated_step.get("wdkStepId")
    if isinstance(wdk_step_id_raw, int) and projection.site_id:
        try:
            api = get_strategy_api(projection.site_id)
            await api.delete_step_filter(
                step_id=wdk_step_id_raw, filter_name=filter_name
            )
        except Exception as e:
            logger.warning("WDK filter delete failed", error=str(e))

    return StepFiltersResponse(
        filters=[StepFilterResponse.model_validate(f.to_dict()) for f in filters]
    )

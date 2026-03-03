"""Step report endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from veupath_chatbot.domain.strategy.ast import StepReport
from veupath_chatbot.integrations.veupathdb.factory import get_strategy_api
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONObject
from veupath_chatbot.transport.http.deps import CurrentUser, StreamRepo
from veupath_chatbot.transport.http.routers.steps._shared import (
    get_step_or_404,
    parse_reports,
    refresh_step_after_update,
    update_plan,
)
from veupath_chatbot.transport.http.schemas import (
    StepReportRequest,
    StepReportResponse,
    StepReportRunResponse,
)

router = APIRouter(prefix="/api/v1/strategies/{strategyId}/steps", tags=["steps"])
logger = get_logger(__name__)


@router.post("/{step_id}/reports", response_model=StepReportRunResponse)
async def run_step_report(
    strategyId: UUID,
    step_id: str,
    request: StepReportRequest,
    stream_repo: StreamRepo,
    user_id: CurrentUser,
) -> StepReportRunResponse:
    """Run a report and attach it locally."""
    projection, plan, step = await get_step_or_404(
        stream_repo, strategyId, user_id, step_id
    )

    reports = list(parse_reports(step.get("reports")))
    reports.append(StepReport(report_name=request.report_name, config=request.config))

    updated_plan = update_plan(
        plan, step_id, {"reports": [r.to_dict() for r in reports]}
    )
    await stream_repo.update_projection(strategyId, plan=updated_plan)

    wdk_result: JSONObject | None = None
    updated_step = refresh_step_after_update(updated_plan, step_id, step)
    wdk_step_id_raw = updated_step.get("wdkStepId")
    if isinstance(wdk_step_id_raw, int) and projection.site_id:
        try:
            api = get_strategy_api(projection.site_id)
            wdk_result_raw = await api.run_step_report(
                step_id=wdk_step_id_raw,
                report_name=request.report_name,
                config=request.config,
            )
            wdk_result = wdk_result_raw if isinstance(wdk_result_raw, dict) else None
        except Exception as e:
            logger.warning("WDK report failed", error=str(e))

    return StepReportRunResponse(
        report=StepReportResponse.model_validate(reports[-1].to_dict()), wdk=wdk_result
    )

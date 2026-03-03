"""Shared helpers for step sub-routers."""

from __future__ import annotations

from uuid import UUID

from veupath_chatbot.domain.strategy.ast import (
    StepAnalysis,
    StepFilter,
    StepReport,
    from_dict,
)
from veupath_chatbot.persistence.models import StreamProjection
from veupath_chatbot.persistence.repositories.stream import StreamRepository
from veupath_chatbot.platform.errors import ErrorCode, NotFoundError, ValidationError
from veupath_chatbot.platform.types import JSONArray, JSONObject, as_json_object
from veupath_chatbot.services.strategies.serialization import build_steps_data_from_plan
from veupath_chatbot.transport.http.routers._authz import get_owned_projection_or_404


def get_steps_as_objects(steps: JSONArray) -> list[JSONObject]:
    """Convert JSONArray to list[JSONObject] with type checking."""
    result: list[JSONObject] = []
    for step in steps:
        if isinstance(step, dict):
            result.append(step)
    return result


def find_step(strategy_steps: list[JSONObject], step_id: str) -> JSONObject | None:
    for step in strategy_steps:
        if step.get("id") == step_id:
            return step
    return None


async def get_step_or_404(
    stream_repo: StreamRepository,
    strategy_id: UUID,
    user_id: UUID,
    step_id: str,
) -> tuple[StreamProjection, JSONObject, JSONObject]:
    """Fetch projection, extract plan, find step by ID or raise 404.

    Returns (projection, plan, step).
    """
    projection = await get_owned_projection_or_404(stream_repo, strategy_id, user_id)
    plan = projection.plan if isinstance(projection.plan, dict) else {}
    steps_raw = build_steps_data_from_plan(plan)
    steps = get_steps_as_objects(steps_raw)
    step = find_step(steps, step_id)
    if not step:
        raise NotFoundError(code=ErrorCode.STEP_NOT_FOUND, title="Step not found")
    return projection, plan, step


def require_wdk_step_id(step: JSONObject) -> int:
    """Extract wdkStepId from step or raise ValidationError."""
    wdk_step_id_raw = step.get("wdkStepId")
    if not isinstance(wdk_step_id_raw, int):
        raise ValidationError(
            detail="WDK step not available",
            errors=[
                {
                    "path": "steps[].wdkStepId",
                    "message": "WDK step not available",
                    "code": "WDK_STEP_NOT_AVAILABLE",
                }
            ],
        )
    return wdk_step_id_raw


def refresh_step_after_update(
    updated_plan: JSONObject, step_id: str, fallback_step: JSONObject
) -> JSONObject:
    """Re-extract a step from an updated plan, falling back to the original."""
    steps_raw = build_steps_data_from_plan(updated_plan)
    steps = get_steps_as_objects(steps_raw)
    return find_step(steps, step_id) or fallback_step


def parse_filters(raw: object) -> list[StepFilter]:
    """Parse a raw JSON list into StepFilter objects."""
    if not isinstance(raw, list):
        return []
    return [
        StepFilter(
            name=str(f.get("name", "")),
            value=f.get("value"),
            disabled=bool(f.get("disabled", False)),
        )
        for f in raw
        if isinstance(f, dict) and f.get("name") is not None
    ]


def parse_analyses(raw: object) -> list[StepAnalysis]:
    """Parse a raw JSON list into StepAnalysis objects."""
    if not isinstance(raw, list):
        return []
    return [
        StepAnalysis(
            analysis_type=str(a.get("analysisType") or a.get("analysis_type", "")),
            parameters=as_json_object(a.get("parameters"))
            if isinstance(a.get("parameters"), dict)
            else {},
            custom_name=str(a.get("customName") or a.get("custom_name"))
            if (a.get("customName") or a.get("custom_name")) is not None
            else None,
        )
        for a in raw
        if isinstance(a, dict) and (a.get("analysisType") or a.get("analysis_type"))
    ]


def parse_reports(raw: object) -> list[StepReport]:
    """Parse a raw JSON list into StepReport objects."""
    if not isinstance(raw, list):
        return []
    return [
        StepReport(
            report_name=str(r.get("reportName") or r.get("report_name") or "standard"),
            config=as_json_object(r.get("config"))
            if isinstance(r.get("config"), dict)
            else {},
        )
        for r in raw
        if isinstance(r, dict)
    ]


def update_plan(plan: JSONObject, step_id: str, updates: JSONObject) -> JSONObject:
    """Update a plan AST with step attachments."""
    try:
        ast = from_dict(plan)
    except Exception as exc:
        raise ValidationError(
            title="Invalid plan",
            errors=[
                {"path": "", "message": str(exc), "code": "INVALID_STRATEGY"},
            ],
        ) from exc

    step = ast.get_step_by_id(step_id)
    if not step:
        return plan

    if "filters" in updates:
        step.filters = parse_filters(updates["filters"])
    if "analyses" in updates:
        step.analyses = parse_analyses(updates["analyses"])
    if "reports" in updates:
        step.reports = parse_reports(updates["reports"])
    return ast.to_dict()

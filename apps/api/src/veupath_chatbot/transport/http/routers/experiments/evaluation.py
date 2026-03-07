"""Evaluation endpoints: re-evaluate, threshold-sweep, step-contributions, report."""

from typing import cast

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from veupath_chatbot.platform.types import JSONObject, JSONValue
from veupath_chatbot.services.experiment.evaluation import (
    compute_step_contributions,
    compute_sweep_values,
    generate_sweep_events,
    re_evaluate,
    validate_sweep_parameter,
)
from veupath_chatbot.transport.http.deps import CurrentUser, ExperimentDep
from veupath_chatbot.transport.http.schemas.experiments import ThresholdSweepRequest


class StepContributionsRequest(BaseModel):
    """Request body for step contributions analysis."""

    step_tree: JSONObject = Field(alias="stepTree")

    model_config = {"populate_by_name": True}


router = APIRouter()


@router.post("/{experiment_id}/re-evaluate")
async def re_evaluate_experiment(
    exp: ExperimentDep, user_id: CurrentUser
) -> JSONObject:
    """Re-run control evaluation against the (possibly modified) strategy."""
    return await re_evaluate(exp)


@router.post("/{experiment_id}/threshold-sweep")
async def threshold_sweep(
    exp: ExperimentDep,
    request: ThresholdSweepRequest,
    user_id: CurrentUser,
) -> StreamingResponse:
    """Sweep a parameter across a range and stream metrics as they complete."""
    validate_sweep_parameter(exp, request.parameter_name)
    sweep_values = compute_sweep_values(
        sweep_type=request.sweep_type,
        values=request.values,
        min_value=request.min_value,
        max_value=request.max_value,
        steps=request.steps,
    )

    return StreamingResponse(
        generate_sweep_events(
            exp=exp,
            param_name=request.parameter_name,
            sweep_type=request.sweep_type,
            sweep_values=sweep_values,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{experiment_id}/step-contributions")
async def step_contributions(
    exp: ExperimentDep,
    body: StepContributionsRequest,
    user_id: CurrentUser,
) -> JSONObject:
    """Analyse per-step contribution to overall result for multi-step experiments."""
    contributions = await compute_step_contributions(exp, body.step_tree)
    return {"contributions": cast(JSONValue, contributions)}


@router.get("/{experiment_id}/report")
async def get_experiment_report(
    exp: ExperimentDep, user_id: CurrentUser
) -> StreamingResponse:
    """Generate and return a self-contained HTML report for an experiment."""
    from veupath_chatbot.services.experiment.report import generate_experiment_report

    html_content = generate_experiment_report(exp)

    return StreamingResponse(
        iter([html_content]),
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="experiment-{exp.id}-report.html"',
        },
    )

"""Evaluation endpoints: re-evaluate, threshold-sweep, step-contributions, report."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from veupath_chatbot.platform.errors import ValidationError
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONObject, JSONValue
from veupath_chatbot.services.control_tests import run_positive_negative_controls
from veupath_chatbot.services.experiment.store import get_experiment_store
from veupath_chatbot.services.experiment.types import ControlValueFormat
from veupath_chatbot.transport.http.deps import CurrentUser, ExperimentDep
from veupath_chatbot.transport.http.schemas.experiments import ThresholdSweepRequest


class StepContributionsRequest(BaseModel):
    """Request body for step contributions analysis."""

    step_tree: JSONObject = Field(alias="stepTree")

    model_config = {"populate_by_name": True}


router = APIRouter()
logger = get_logger(__name__)


@router.post("/{experiment_id}/re-evaluate")
async def re_evaluate_experiment(
    exp: ExperimentDep, user_id: CurrentUser
) -> JSONObject:
    """Re-run control evaluation against the (possibly modified) strategy."""
    from veupath_chatbot.services.experiment.metrics import metrics_from_control_result
    from veupath_chatbot.services.experiment.types import experiment_to_json

    is_tree_mode = exp.config.mode != "single" and isinstance(
        exp.config.step_tree, dict
    )

    if is_tree_mode:
        from veupath_chatbot.services.experiment.step_analysis import (
            run_controls_against_tree,
        )

        result = await run_controls_against_tree(
            site_id=exp.config.site_id,
            record_type=exp.config.record_type,
            tree=exp.config.step_tree,
            controls_search_name=exp.config.controls_search_name,
            controls_param_name=exp.config.controls_param_name,
            controls_value_format=exp.config.controls_value_format,
            positive_controls=exp.config.positive_controls or None,
            negative_controls=exp.config.negative_controls or None,
        )
    else:
        result = await run_positive_negative_controls(
            site_id=exp.config.site_id,
            record_type=exp.config.record_type,
            target_search_name=exp.config.search_name,
            target_parameters=exp.config.parameters,
            controls_search_name=exp.config.controls_search_name,
            controls_param_name=exp.config.controls_param_name,
            positive_controls=exp.config.positive_controls or None,
            negative_controls=exp.config.negative_controls or None,
            controls_value_format=exp.config.controls_value_format,
        )

    from veupath_chatbot.services.experiment.helpers import extract_and_enrich_genes

    metrics = metrics_from_control_result(result)
    exp.metrics = metrics
    (
        exp.true_positive_genes,
        exp.false_negative_genes,
        exp.false_positive_genes,
        exp.true_negative_genes,
    ) = await extract_and_enrich_genes(
        site_id=exp.config.site_id,
        result=result,
        negative_controls=exp.config.negative_controls,
    )
    get_experiment_store().save(exp)

    return experiment_to_json(exp)


_SWEEP_CONCURRENCY = 3  # Max parallel WDK control-test runs per sweep.
_SWEEP_TIMEOUT_S = 4 * 60  # Server-side timeout for the entire sweep.
_SWEEP_POINT_TIMEOUT_S = (
    90  # Per-point timeout; prevents one slow point from blocking all.
)


@router.post("/{experiment_id}/threshold-sweep")
async def threshold_sweep(
    exp: ExperimentDep,
    request: ThresholdSweepRequest,
    user_id: CurrentUser,
) -> StreamingResponse:
    """Sweep a numeric parameter across a range and stream metrics as they complete.

    Returns an SSE stream with ``sweep_point`` events for each completed point
    and a final ``sweep_complete`` event with all results.  This gives the
    frontend live progress instead of a loading spinner for several minutes.
    """
    import asyncio
    import json as json_mod

    from veupath_chatbot.integrations.veupathdb.factory import get_strategy_api
    from veupath_chatbot.services.control_helpers import (
        cleanup_internal_control_test_strategies,
    )
    from veupath_chatbot.services.experiment.metrics import metrics_from_control_result

    param_name = request.parameter_name
    if param_name not in exp.config.parameters:
        raise ValidationError(
            title="Parameter not found",
            detail=f"Parameter '{param_name}' is not in this experiment's config.",
        )

    is_categorical = request.sweep_type == "categorical"

    if is_categorical:
        if not request.values or len(request.values) == 0:
            raise ValidationError(
                title="Missing values",
                detail="Categorical sweep requires a non-empty 'values' list.",
            )
        sweep_values: list[str] = request.values
    else:
        if request.min_value is None or request.max_value is None:
            raise ValidationError(
                title="Missing range",
                detail="Numeric sweep requires 'minValue' and 'maxValue'.",
            )
        step_size = (request.max_value - request.min_value) / max(request.steps - 1, 1)
        sweep_values = [
            str(request.min_value + i * step_size) for i in range(request.steps)
        ]

    total_points = len(sweep_values)

    async def _generate_sweep():  # noqa: C901
        # Best-effort cleanup up-front.
        try:
            api = get_strategy_api(exp.config.site_id)
            strategies = await api.list_strategies()
            await cleanup_internal_control_test_strategies(api, strategies)
        except Exception:
            pass

        semaphore = asyncio.Semaphore(_SWEEP_CONCURRENCY)
        completed_count = 0
        all_points: list[JSONObject] = []

        async def _run_point(val: str) -> JSONObject:
            modified_params = dict(exp.config.parameters)
            modified_params[param_name] = val

            # For response: keep numeric values as floats when possible.
            try:
                response_value: float | str = float(val) if not is_categorical else val
            except ValueError:
                response_value = val

            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        run_positive_negative_controls(
                            site_id=exp.config.site_id,
                            record_type=exp.config.record_type,
                            target_search_name=exp.config.search_name,
                            target_parameters=modified_params,
                            controls_search_name=exp.config.controls_search_name,
                            controls_param_name=exp.config.controls_param_name,
                            positive_controls=exp.config.positive_controls or None,
                            negative_controls=exp.config.negative_controls or None,
                            controls_value_format=exp.config.controls_value_format,
                            skip_cleanup=True,
                        ),
                        timeout=_SWEEP_POINT_TIMEOUT_S,
                    )
                    m = metrics_from_control_result(result)
                    return {
                        "value": response_value,
                        "metrics": {
                            "sensitivity": round(m.sensitivity, 4),
                            "specificity": round(m.specificity, 4),
                            "precision": round(m.precision, 4),
                            "f1Score": round(m.f1_score, 4),
                            "mcc": round(m.mcc, 4),
                            "balancedAccuracy": round(m.balanced_accuracy, 4),
                            "totalResults": m.total_results,
                            "falsePositiveRate": round(m.false_positive_rate, 4),
                        },
                    }
                except Exception as exc:
                    logger.warning(
                        "Threshold sweep point failed",
                        param=param_name,
                        value=val,
                        error=str(exc),
                    )
                    return {"value": response_value, "metrics": None, "error": str(exc)}

        # Launch all points as tasks; yield events as each completes.
        tasks = {asyncio.ensure_future(_run_point(v)): v for v in sweep_values}

        try:
            async with asyncio.timeout(_SWEEP_TIMEOUT_S):
                for coro in asyncio.as_completed(tasks):
                    point = await coro
                    completed_count += 1
                    all_points.append(point)
                    event_data = json_mod.dumps(
                        {
                            "point": point,
                            "completedCount": completed_count,
                            "totalCount": total_points,
                        }
                    )
                    yield f"event: sweep_point\ndata: {event_data}\n\n"

        except TimeoutError:
            logger.warning(
                "Threshold sweep timed out",
                param=param_name,
                completed=completed_count,
                total=total_points,
            )
            # Cancel remaining tasks
            for task in tasks:
                task.cancel()

        # Sort: numeric by value, categorical by original order.
        if is_categorical:
            order = {v: i for i, v in enumerate(sweep_values)}
            all_points.sort(key=lambda p: order.get(str(p.get("value", "")), 0))
        else:
            all_points.sort(key=lambda p: float(p.get("value", 0)))
        final_data = json_mod.dumps(
            {
                "parameter": param_name,
                "sweepType": request.sweep_type,
                "points": all_points,
            }
        )
        yield f"event: sweep_complete\ndata: {final_data}\n\n"

    return StreamingResponse(
        _generate_sweep(),
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
    """Analyse per-step contribution to overall result for multi-step experiments.

    Evaluates controls against each leaf step individually to show how much
    each step contributes to the final strategy result.
    """
    step_tree_raw = body.step_tree

    from veupath_chatbot.services.experiment.step_analysis._tree_utils import (
        _collect_leaves,
    )

    leaves = _collect_leaves(step_tree_raw)
    contributions: list[JSONObject] = []

    _valid_formats: set[ControlValueFormat] = {"newline", "json_list", "comma"}
    cvf = exp.config.controls_value_format
    controls_format: ControlValueFormat = cvf if cvf in _valid_formats else "newline"

    for leaf in leaves:
        search_name = leaf.get("searchName")
        if not isinstance(search_name, str) or not search_name:
            continue
        params = leaf.get("parameters")
        if not isinstance(params, dict):
            params = {}
        display_name = leaf.get("displayName") or search_name

        try:
            result = await run_positive_negative_controls(
                site_id=exp.config.site_id,
                record_type=exp.config.record_type,
                target_search_name=search_name,
                target_parameters=params,
                controls_search_name=exp.config.controls_search_name,
                controls_param_name=exp.config.controls_param_name,
                positive_controls=exp.config.positive_controls or None,
                negative_controls=exp.config.negative_controls or None,
                controls_value_format=controls_format,
            )
            target_data = result.get("target") or {}
            target_dict = target_data if isinstance(target_data, dict) else {}
            raw_count = target_dict.get("resultCount")
            total = int(raw_count) if isinstance(raw_count, (int, float)) else 0

            pos_data = result.get("positive") or {}
            pos_dict = pos_data if isinstance(pos_data, dict) else {}
            raw_pos_hits = pos_dict.get("intersectionCount")
            pos_hits = (
                int(raw_pos_hits) if isinstance(raw_pos_hits, (int, float)) else 0
            )

            neg_data = result.get("negative") or {}
            neg_dict = neg_data if isinstance(neg_data, dict) else {}
            raw_neg_hits = neg_dict.get("intersectionCount")
            neg_hits = (
                int(raw_neg_hits) if isinstance(raw_neg_hits, (int, float)) else 0
            )

            total_pos = (
                len(exp.config.positive_controls) if exp.config.positive_controls else 0
            )
            total_neg = (
                len(exp.config.negative_controls) if exp.config.negative_controls else 0
            )
            contributions.append(
                {
                    "stepName": str(display_name),
                    "stepSearchName": search_name,
                    "totalResults": total,
                    "positiveControlHits": pos_hits,
                    "negativeControlHits": neg_hits,
                    "positiveRecall": round(pos_hits / max(total_pos, 1), 4),
                    "negativeRecall": round(neg_hits / max(total_neg, 1), 4),
                }
            )
        except Exception as exc:
            logger.warning(
                "Step contribution analysis failed",
                step=search_name,
                error=str(exc),
            )
            contributions.append(
                {
                    "stepName": str(display_name),
                    "stepSearchName": search_name,
                    "totalResults": 0,
                    "positiveControlHits": 0,
                    "negativeControlHits": 0,
                    "positiveRecall": 0,
                    "negativeRecall": 0,
                }
            )

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

"""Tools for executing strategies and retrieving results."""

from typing import Annotated, cast

from kani import AIParam, ai_function

from veupath_chatbot.domain.strategy.ast import StrategyAST
from veupath_chatbot.domain.strategy.compile import (
    apply_step_decorations,
    compile_strategy,
)
from veupath_chatbot.domain.strategy.validate import validate_strategy
from veupath_chatbot.integrations.veupathdb.factory import (
    get_site,
    get_strategy_api,
)
from veupath_chatbot.integrations.veupathdb.strategy_api import StrategyAPI
from veupath_chatbot.platform.errors import ErrorCode
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONObject, JSONValue
from veupath_chatbot.services.experiment.helpers import extract_wdk_id
from veupath_chatbot.services.strategies.engine.validation import ValidationMixin

logger = get_logger(__name__)


class ExecutionTools(ValidationMixin):
    """Tools for running strategies and getting results."""

    def _get_api(self) -> StrategyAPI:
        """Get strategy API for current site."""
        return get_strategy_api(self.session.site_id)

    @ai_function()
    async def build_strategy(
        self,
        strategy_name: Annotated[str | None, AIParam(desc="Strategy name")] = None,
        root_step_id: Annotated[
            str | None, AIParam(desc="Root step ID (required if not built)")
        ] = None,
        record_type: Annotated[
            str | None, AIParam(desc="Record type (required if not built)")
        ] = None,
        description: Annotated[str | None, AIParam(desc="Strategy description")] = None,
        graph_id: Annotated[str | None, AIParam(desc="Graph ID to build")] = None,
    ) -> JSONObject:
        """Build or update the current strategy on VEuPathDB.

        If the strategy has already been built (a WDK strategy ID exists),
        this updates it in place.  Otherwise it creates a new WDK strategy.
        Returns per-step result counts, zero-result step detection, and the
        WDK strategy URL.
        """
        graph = self._get_graph(graph_id)
        if not graph:
            return self._graph_not_found(graph_id)

        strategy = graph.current_strategy

        if root_step_id:
            # Explicit override — trust the caller.
            root_step = graph.get_step(root_step_id)
        elif len(graph.roots) == 1:
            root_step = graph.get_step(next(iter(graph.roots)))
        elif len(graph.roots) > 1:
            return self._tool_error(
                ErrorCode.INVALID_STRATEGY,
                f"Graph has {len(graph.roots)} subtree roots — expected exactly 1 to build. "
                "Combine them first, or specify root_step_id.",
                graphId=graph.id,
                roots=cast(JSONValue, sorted(graph.roots)),
            )
        else:
            root_step = None

        needs_rebuild = root_step is not None and (
            not strategy
            or (
                root_step.id is not None
                and strategy.get_step_by_id(root_step.id) is None
            )
        )

        if not strategy or needs_rebuild:
            if not root_step:
                return self._tool_error(
                    ErrorCode.INVALID_STRATEGY,
                    "No steps in graph. Create steps before building.",
                    graphId=graph.id,
                )

            inferred_record_type = record_type or graph.record_type
            if not inferred_record_type:
                return self._tool_error(
                    ErrorCode.VALIDATION_ERROR,
                    "Record type could not be inferred for execution.",
                    graphId=graph.id,
                )

            strategy = StrategyAST(
                record_type=inferred_record_type,
                root=root_step,
                name=strategy_name or graph.name,
                description=description,
            )
            validation_result = validate_strategy(strategy)
            if not validation_result.valid:
                return self._tool_error(
                    ErrorCode.VALIDATION_ERROR,
                    "Strategy validation failed",
                    graphId=graph.id,
                    validationErrors=[
                        {"path": e.path, "message": e.message}
                        for e in validation_result.errors
                    ],
                )

            graph.current_strategy = strategy
            graph.save_history(
                f"Created strategy: {strategy_name or 'Untitled Strategy'}"
            )
        if strategy_name:
            strategy.name = strategy_name
            graph.name = strategy_name

        try:
            api = self._get_api()

            # Compile to WDK
            logger.info("Building strategy", name=strategy.name)
            compilation_result = await compile_strategy(
                strategy, api, site_id=self.session.site_id
            )

            # Create-or-update: if a WDK strategy already exists on the graph,
            # update it rather than creating a duplicate.
            existing_wdk_id = graph.wdk_strategy_id
            wdk_strategy_id: int | None = None

            if existing_wdk_id is not None:
                # Update the existing WDK strategy.
                try:
                    await api.update_strategy(
                        strategy_id=existing_wdk_id,
                        step_tree=compilation_result.step_tree,
                        name=strategy.name or "Untitled Strategy",
                    )
                    wdk_strategy_id = existing_wdk_id
                    logger.info(
                        "Updated existing WDK strategy",
                        wdk_strategy_id=existing_wdk_id,
                    )
                except Exception as update_err:
                    # If the old strategy was deleted (404), fall through to create.
                    logger.warning(
                        "Failed to update WDK strategy, will create new",
                        wdk_strategy_id=existing_wdk_id,
                        error=str(update_err),
                    )
                    wdk_strategy_id = None

            if wdk_strategy_id is None:
                # First build (or update failed) — create a new WDK strategy.
                wdk_result = await api.create_strategy(
                    step_tree=compilation_result.step_tree,
                    name=strategy.name or "Untitled Strategy",
                    description=strategy.description,
                )
                wdk_strategy_id = extract_wdk_id(wdk_result)

            compiled_map = {s.local_id: s.wdk_step_id for s in compilation_result.steps}

            await apply_step_decorations(strategy, compiled_map, api)
            site = get_site(self.session.site_id)
            wdk_url = (
                site.strategy_url(wdk_strategy_id, compilation_result.root_step_id)
                if wdk_strategy_id
                else None
            )

            # Store the local→WDK step ID mapping on the graph so that
            # list_current_steps can surface wdkStepId per step.
            graph.wdk_step_ids = dict(compiled_map)
            graph.wdk_strategy_id = wdk_strategy_id

            # Fetch the strategy once — WDK includes estimatedSize on every
            # step, so one GET replaces N individual report POST calls.
            step_counts: dict[str, int | None] = {}
            root_count: int | None = None
            if wdk_strategy_id is not None:
                try:
                    strategy_info = await api.get_strategy(wdk_strategy_id)
                    if isinstance(strategy_info, dict):
                        root_step_id_raw = strategy_info.get("rootStepId")
                        steps_raw = strategy_info.get("steps")
                        if isinstance(steps_raw, dict):
                            # Build a reverse map: wdk_step_id → local_id
                            wdk_to_local = {v: k for k, v in compiled_map.items()}
                            for wdk_id_str, step_info in steps_raw.items():
                                if not isinstance(step_info, dict):
                                    continue
                                estimated = step_info.get("estimatedSize")
                                count_val = (
                                    estimated if isinstance(estimated, int) else None
                                )
                                # Map back to local step ID
                                try:
                                    wdk_id_int = int(wdk_id_str)
                                except ValueError, TypeError:
                                    continue
                                local_id = wdk_to_local.get(wdk_id_int)
                                if local_id:
                                    step_counts[local_id] = count_val
                            # Extract root count specifically
                            if isinstance(root_step_id_raw, int):
                                root_local = wdk_to_local.get(root_step_id_raw)
                                if root_local:
                                    root_count = step_counts.get(root_local)
                except Exception as e:
                    logger.warning("Strategy count lookup failed", error=str(e))

            # Persist counts on the graph for list_current_steps.
            graph.step_counts = step_counts

            # Build per-step counts response keyed by local step ID.
            counts_response: JSONObject = {str(k): v for k, v in step_counts.items()}
            zeros = sorted([sid for sid, c in step_counts.items() if c == 0])

            wdk_strategy_id_value: JSONValue = wdk_strategy_id
            return {
                "ok": True,
                "graphId": graph.id,
                "graphName": graph.name,
                "name": strategy.name,
                "description": strategy.description,
                "wdkStrategyId": wdk_strategy_id_value,
                "wdkUrl": wdk_url,
                "rootStepId": compilation_result.root_step_id,
                "resultCount": root_count,
                "stepCount": len(compilation_result.steps),
                "counts": counts_response,
                "zeroStepIds": cast(JSONValue, zeros),
                "zeroCount": len(zeros),
            }

        except Exception as e:
            logger.error("Strategy build failed", error=str(e))
            return self._tool_error(
                ErrorCode.WDK_ERROR, f"Build failed: {e}", graphId=graph.id
            )

    @ai_function()
    async def get_result_count(
        self,
        wdk_step_id: Annotated[int, AIParam(desc="WDK step ID")],
        wdk_strategy_id: Annotated[
            int | None, AIParam(desc="WDK strategy ID (for imports)")
        ] = None,
    ) -> JSONObject:
        """Get the result count for a built step.

        Use after build_strategy to check result sizes.
        For imported WDK strategies, provide wdk_strategy_id.
        """
        try:
            api = self._get_api()
            if wdk_strategy_id is not None:
                strategy_raw = await api.get_strategy(wdk_strategy_id)
                if not isinstance(strategy_raw, dict):
                    raise TypeError("Expected dict from get_strategy")
                # WDK: steps is dict[str, stepObj], estimatedSize is on each step.
                steps_raw = strategy_raw.get("steps")
                if isinstance(steps_raw, dict):
                    step_info = steps_raw.get(str(wdk_step_id))
                    if isinstance(step_info, dict):
                        estimated_size = step_info.get("estimatedSize")
                        if isinstance(estimated_size, int):
                            return {"stepId": wdk_step_id, "count": estimated_size}
            count = await api.get_step_count(wdk_step_id)
            return {"stepId": wdk_step_id, "count": count}
        except Exception as e:
            message = str(e)
            if wdk_strategy_id is None:
                message = f"{message} (try providing wdk_strategy_id)"
            return self._tool_error(ErrorCode.WDK_ERROR, message)

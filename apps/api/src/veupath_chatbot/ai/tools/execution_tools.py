"""Tools for executing strategies and retrieving results."""

from typing import Annotated, cast

from kani import AIParam, ai_function

from veupath_chatbot.platform.errors import ErrorCode
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.tool_errors import tool_error
from veupath_chatbot.platform.types import JSONObject, JSONValue
from veupath_chatbot.services.strategies.build import (
    RootResolutionError,
    build_strategy_for_site,
    get_result_count_for_site,
)
from veupath_chatbot.services.strategies.engine.validation import ValidationMixin

logger = get_logger(__name__)


class ExecutionTools(ValidationMixin):
    """Tools for running strategies and getting results."""

    @ai_function()
    async def build_strategy(
        self,
        strategy_name: Annotated[str | None, AIParam(desc="Strategy name")] = None,
        root_step_id: Annotated[
            str | None, AIParam(desc="Root step ID (required if not built)")
        ] = None,
        description: Annotated[str | None, AIParam(desc="Strategy description")] = None,
        graph_id: Annotated[str | None, AIParam(desc="Graph ID to build")] = None,
    ) -> JSONObject:
        """Build or update the current strategy on VEuPathDB.

        Record type is auto-resolved from the searches in the strategy.
        If the strategy has already been built (a WDK strategy ID exists),
        this updates it in place.  Otherwise it creates a new WDK strategy.
        Returns per-step result counts, zero-result step detection, and the
        WDK strategy URL.
        """
        graph = self._get_graph(graph_id)
        if not graph:
            return self._graph_not_found(graph_id)

        try:
            result = await build_strategy_for_site(
                graph=graph,
                site_id=self.session.site_id,
                root_step_id=root_step_id,
                strategy_name=strategy_name,
                description=description,
            )

            strategy = graph.current_strategy
            counts_response: JSONObject = {str(k): v for k, v in result.counts.items()}
            wdk_strategy_id_value: JSONValue = result.wdk_strategy_id

            return {
                "ok": True,
                "graphId": graph.id,
                "graphName": graph.name,
                "name": strategy.name if strategy else None,
                "description": strategy.description if strategy else None,
                "wdkStrategyId": wdk_strategy_id_value,
                "wdkUrl": result.wdk_url,
                "rootStepId": result.root_step_id,
                "resultCount": result.root_count,
                "stepCount": result.step_count,
                "counts": counts_response,
                "zeroStepIds": cast(JSONValue, result.zero_step_ids),
                "zeroCount": len(result.zero_step_ids),
            }

        except RootResolutionError as e:
            if e.root_count > 1:
                return tool_error(
                    ErrorCode.INVALID_STRATEGY,
                    str(e),
                    graphId=graph.id,
                    roots=cast(JSONValue, sorted(graph.roots)),
                )
            return tool_error(
                ErrorCode.INVALID_STRATEGY,
                str(e),
                graphId=graph.id,
            )
        except ValueError as e:
            return tool_error(
                ErrorCode.VALIDATION_ERROR,
                str(e),
                graphId=graph.id,
            )
        except Exception as e:
            logger.error("Strategy build failed", error=str(e))
            return tool_error(
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
            result = await get_result_count_for_site(
                self.session.site_id, wdk_step_id, wdk_strategy_id
            )
            return {"stepId": result.step_id, "count": result.count}
        except Exception as e:
            message = str(e)
            if wdk_strategy_id is None:
                message = f"{message} (try providing wdk_strategy_id)"
            return tool_error(ErrorCode.WDK_ERROR, message)

"""WDK strategy sync logic (service layer).

Handles fetching from WDK, upserting into the CQRS layer, and
error boundary context managers.  No FastAPI dependencies.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from veupath_chatbot.persistence.models import StreamProjection

from veupath_chatbot.integrations.veupathdb.strategy_api import StrategyAPI
from veupath_chatbot.persistence.repositories.stream import StreamRepository
from veupath_chatbot.platform.errors import AppError, WDKError
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONArray, JSONObject
from veupath_chatbot.services.strategies.serialization import count_steps_in_plan
from veupath_chatbot.services.strategies.wdk_snapshot import (
    _build_snapshot_from_wdk,
    _normalize_synced_parameters,
    extract_wdk_is_saved,
)

logger = get_logger(__name__)


@asynccontextmanager
async def wdk_error_boundary(operation: str) -> AsyncIterator[None]:
    """Wrap WDK operations with consistent error handling."""
    try:
        yield
    except AppError:
        raise
    except WDKError as e:
        logger.error(f"{operation} failed", error=str(e))
        raise
    except Exception as e:
        logger.error(f"{operation} failed", error=str(e))
        raise WDKError(f"Failed to {operation}: {e}") from e


async def upsert_wdk_projection(
    *,
    stream_repo: StreamRepository,
    user_id: UUID,
    site_id: str,
    wdk_id: int,
    name: str,
    plan: JSONObject,
    steps_data: JSONArray,
    record_type: str | None,
    root_step_id: str,
    is_saved: bool,
) -> StreamProjection:
    """Upsert a WDK strategy into the CQRS layer (create or update stream projection)."""
    existing = await stream_repo.get_by_wdk_strategy_id(user_id, wdk_id)
    if existing:
        await stream_repo.update_projection(
            existing.stream_id,
            name=name,
            plan=plan,
            steps=list(steps_data),
            record_type=record_type,
            root_step_id=root_step_id,
            root_step_id_set=True,
            wdk_strategy_id=wdk_id,
            wdk_strategy_id_set=True,
            is_saved=is_saved,
            is_saved_set=True,
            step_count=count_steps_in_plan(plan),
        )
        proj = await stream_repo.get_projection(existing.stream_id)
    else:
        stream = await stream_repo.create(
            user_id=user_id,
            site_id=site_id,
            name=name,
        )
        await stream_repo.update_projection(
            stream.id,
            plan=plan,
            steps=list(steps_data),
            record_type=record_type,
            root_step_id=root_step_id,
            root_step_id_set=True,
            wdk_strategy_id=wdk_id,
            wdk_strategy_id_set=True,
            is_saved=is_saved,
            is_saved_set=True,
            step_count=count_steps_in_plan(plan),
        )
        proj = await stream_repo.get_projection(stream.id)

    if proj is None:
        raise RuntimeError(f"Projection disappeared for WDK strategy {wdk_id}")
    return proj


async def sync_single_wdk_strategy(
    *,
    wdk_id: int,
    site_id: str,
    api: StrategyAPI,
    stream_repo: StreamRepository,
    user_id: UUID,
) -> StreamProjection:
    """Fetch a single WDK strategy and upsert into the CQRS layer.

    Shared by ``open_strategy`` and ``sync_all_wdk_strategies``.
    """
    wdk_strategy = await api.get_strategy(wdk_id)

    ast, steps_data = _build_snapshot_from_wdk(wdk_strategy)

    # Normalize parameters so all sync paths produce consistent representations.
    try:
        await _normalize_synced_parameters(ast, steps_data, api)
    except Exception as exc:
        logger.warning(
            "Parameter normalization failed during sync, storing raw values",
            wdk_id=wdk_id,
            error=str(exc),
        )

    is_saved = extract_wdk_is_saved(wdk_strategy)
    plan = ast.to_dict()
    name = ast.name or f"WDK Strategy {wdk_id}"

    return await upsert_wdk_projection(
        stream_repo=stream_repo,
        user_id=user_id,
        site_id=site_id,
        wdk_id=wdk_id,
        name=name,
        plan=plan,
        steps_data=list(steps_data),
        record_type=ast.record_type,
        root_step_id=ast.root.id,
        is_saved=is_saved,
    )


def parse_wdk_strategy_id(item: JSONObject) -> int | None:
    """Extract integer WDK strategy ID from a list-strategies item.

    WDK's ``StrategyFormatter`` emits ``strategyId`` (``JsonKeys.STRATEGY_ID``)
    as a Java long (always an int in JSON).

    :param item: Item dict.

    """
    wdk_id = item.get("strategyId")
    if isinstance(wdk_id, int):
        return wdk_id
    return None

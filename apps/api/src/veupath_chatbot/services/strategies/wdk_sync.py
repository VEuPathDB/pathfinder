"""WDK sync: fetch WDK strategies and sync into CQRS projections.

Handles:
- ``fetch_and_convert`` — fetch WDK strategy, convert to AST, normalize params
- ``sync_to_projection`` — full sync flow: fetch + upsert into CQRS
- ``upsert_projection`` — create-or-update a stream projection from WDK data
- ``upsert_summary_projection`` — create-or-update from list summary data
- ``plan_needs_detail_fetch`` — check if a projection needs WDK detail fetch
"""

from uuid import UUID

from veupath_chatbot.domain.strategy.ast import StrategyAST
from veupath_chatbot.integrations.veupathdb.strategy_api import StrategyAPI
from veupath_chatbot.persistence.models import StreamProjection
from veupath_chatbot.persistence.repositories.stream import StreamRepository
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONObject

from .wdk_conversion import (
    build_snapshot_from_wdk,
    extract_wdk_is_saved,
    normalize_synced_parameters,
    parse_wdk_strategy_id,
)

logger = get_logger(__name__)


def plan_needs_detail_fetch(projection: StreamProjection) -> bool:
    """Check if a WDK-linked projection needs its full detail fetched from WDK.

    Returns True when the projection has a ``wdk_strategy_id`` but no plan data
    (i.e. it was synced with summary data only and the user is now opening it).
    Local strategies (no ``wdk_strategy_id``) never need a WDK fetch.
    """
    if projection.wdk_strategy_id is None:
        return False
    plan = projection.plan
    if not isinstance(plan, dict) or not plan:
        return True
    return "root" not in plan


async def fetch_and_convert(
    api: StrategyAPI,
    wdk_id: int,
) -> tuple[StrategyAST, bool, JSONObject]:
    """Fetch a WDK strategy and convert to internal AST.

    Normalizes parameters best-effort (failures are logged and swallowed).

    :returns: Tuple of (StrategyAST, is_saved, step_counts).
        ``step_counts`` maps step IDs to ``estimatedSize`` values from the
        WDK response, enabling zero-cost count display.
    """
    wdk_strategy = await api.get_strategy(wdk_id)

    ast, steps_data, step_counts = build_snapshot_from_wdk(wdk_strategy)

    try:
        await normalize_synced_parameters(ast, steps_data, api)
    except Exception as exc:
        logger.warning(
            "Parameter normalization failed, storing raw values",
            wdk_id=wdk_id,
            error=str(exc),
        )

    is_saved = extract_wdk_is_saved(wdk_strategy)
    return ast, is_saved, step_counts


async def sync_to_projection(
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
    ast, is_saved, step_counts = await fetch_and_convert(api, wdk_id)
    plan = ast.to_dict()
    if step_counts:
        plan["stepCounts"] = step_counts
    name = ast.name or f"WDK Strategy {wdk_id}"

    return await upsert_projection(
        stream_repo=stream_repo,
        user_id=user_id,
        site_id=site_id,
        wdk_id=wdk_id,
        name=name,
        plan=plan,
        record_type=ast.record_type,
        is_saved=is_saved,
        step_count=len(ast.get_all_steps()),
    )


async def upsert_projection(
    *,
    stream_repo: StreamRepository,
    user_id: UUID,
    site_id: str,
    wdk_id: int,
    name: str,
    plan: JSONObject,
    record_type: str | None,
    is_saved: bool,
    step_count: int = 0,
) -> StreamProjection:
    """Upsert a WDK strategy into the CQRS layer (create or update stream projection)."""
    existing = await stream_repo.get_by_wdk_strategy_id(user_id, wdk_id)
    if existing:
        await stream_repo.update_projection(
            existing.stream_id,
            name=name,
            plan=plan,
            record_type=record_type,
            wdk_strategy_id=wdk_id,
            wdk_strategy_id_set=True,
            is_saved=is_saved,
            is_saved_set=True,
            step_count=step_count,
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
            record_type=record_type,
            wdk_strategy_id=wdk_id,
            wdk_strategy_id_set=True,
            is_saved=is_saved,
            is_saved_set=True,
            step_count=step_count,
        )
        proj = await stream_repo.get_projection(stream.id)

    if proj is None:
        raise RuntimeError(f"Projection disappeared for WDK strategy {wdk_id}")
    return proj


async def upsert_summary_projection(
    wdk_item: JSONObject,
    *,
    stream_repo: StreamRepository,
    user_id: UUID,
    site_id: str,
) -> StreamProjection | None:
    """Create or update a projection from WDK list summary data only.

    Unlike ``sync_to_projection``, this does NOT fetch the full strategy detail
    from WDK. It only stores metadata available from the list endpoint:
    name, recordClassName, estimatedSize, isSaved, leafAndTransformStepCount.

    The ``plan`` field is left untouched (empty for new projections, preserved
    for existing ones). Full plan data is fetched lazily on first GET.

    Returns the projection, or ``None`` if the WDK item has no valid ID.
    """
    wdk_id = parse_wdk_strategy_id(wdk_item)
    if wdk_id is None:
        return None

    name_raw = wdk_item.get("name")
    name = (
        str(name_raw)
        if isinstance(name_raw, str) and name_raw
        else f"WDK Strategy {wdk_id}"
    )

    record_class = wdk_item.get("recordClassName")
    record_type = (
        str(record_class).strip()
        if isinstance(record_class, str) and record_class
        else None
    )

    is_saved = extract_wdk_is_saved(wdk_item)

    estimated_raw = wdk_item.get("estimatedSize")
    estimated_size = estimated_raw if isinstance(estimated_raw, int) else None

    step_count_raw = wdk_item.get("leafAndTransformStepCount")
    step_count = step_count_raw if isinstance(step_count_raw, int) else 0

    existing = await stream_repo.get_by_wdk_strategy_id(user_id, wdk_id)
    if existing and existing.dismissed_at is not None:
        # Strategy was dismissed by user — don't re-import or update it.
        return existing
    if existing:
        await stream_repo.update_projection(
            existing.stream_id,
            name=name,
            record_type=record_type,
            wdk_strategy_id=wdk_id,
            wdk_strategy_id_set=True,
            is_saved=is_saved,
            is_saved_set=True,
            step_count=step_count,
            result_count=estimated_size,
            result_count_set=True,
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
            record_type=record_type,
            wdk_strategy_id=wdk_id,
            wdk_strategy_id_set=True,
            is_saved=is_saved,
            is_saved_set=True,
            step_count=step_count,
            result_count=estimated_size,
            result_count_set=True,
        )
        proj = await stream_repo.get_projection(stream.id)

    return proj

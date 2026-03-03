"""One-time migration: copy strategy identity into streams + projections.

Idempotent — safe to re-run. Skips rows that already exist in streams.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from veupath_chatbot.platform.logging import get_logger

logger = get_logger(__name__)


async def migrate_strategies_to_streams(conn: AsyncConnection) -> int:
    """Migrate existing strategies to the streams + stream_projections tables.

    Returns the number of rows migrated.
    """
    result = await conn.execute(
        text(
            "INSERT INTO streams (id, user_id, site_id, created_at) "
            "SELECT id, user_id, site_id, created_at FROM strategies "
            "WHERE id NOT IN (SELECT id FROM streams) "
            "ON CONFLICT DO NOTHING"
        )
    )
    migrated = result.rowcount or 0

    await conn.execute(
        text(
            "INSERT INTO stream_projections "
            "(stream_id, name, record_type, wdk_strategy_id, is_saved, "
            " model_id, message_count, step_count, plan, steps, root_step_id, "
            " result_count, updated_at) "
            "SELECT s.id, s.name, s.record_type, s.wdk_strategy_id, s.is_saved, "
            "       s.model_id, "
            "       COALESCE(jsonb_array_length(s.messages::jsonb), 0), "
            "       COALESCE(jsonb_array_length(s.steps::jsonb), 0), "
            "       s.plan, s.steps, s.root_step_id, "
            "       s.result_count, s.updated_at "
            "FROM strategies s "
            "WHERE s.id NOT IN (SELECT stream_id FROM stream_projections) "
            "ON CONFLICT DO NOTHING"
        )
    )

    if migrated:
        logger.info("Migrated strategies to streams", count=migrated)

    return migrated

"""Redis connection management for event sourcing."""

from collections.abc import Awaitable

from redis.asyncio import Redis

from veupath_chatbot.platform.config import get_settings
from veupath_chatbot.platform.logging import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None


async def init_redis() -> Redis:
    """Initialize the Redis connection pool."""
    global _redis
    settings = get_settings()
    _redis = Redis.from_url(
        settings.redis_url,
        decode_responses=False,
    )
    result = _redis.ping()
    if isinstance(result, Awaitable):
        await result
    logger.info("Redis connected", url=settings.redis_url)
    return _redis


def get_redis() -> Redis:
    """Get the Redis client. Must call init_redis() first."""
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() during startup.")
    return _redis


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")

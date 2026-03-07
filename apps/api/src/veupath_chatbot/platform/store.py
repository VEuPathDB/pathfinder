"""Generic write-through store: in-memory cache + fire-and-forget DB persistence.

Provides the shared save/get/delete/aget/adelete logic so that concrete
stores only need to supply three async DB functions and their custom
listing methods.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from veupath_chatbot.platform.tasks import spawn


class Identifiable(Protocol):
    """Any entity with a string ``id``."""

    @property
    def id(self) -> str: ...


class WriteThruStore[T: Identifiable]:
    """In-memory cache backed by fire-and-forget DB writes.

    Subclasses must set three class-level functions via ``staticmethod``:

    * ``_persist_fn(entity) -> None``  — upsert to DB
    * ``_load_fn(entity_id) -> T | None``  — load from DB
    * ``_delete_fn(entity_id) -> None``  — delete from DB

    Every entity must satisfy the ``Identifiable`` protocol (have ``id: str``).
    """

    _persist_fn: Callable[..., Awaitable[None]]
    _load_fn: Callable[[str], Awaitable[T | None]]
    _delete_fn: Callable[[str], Awaitable[None]]

    def __init__(self) -> None:
        self._cache: dict[str, T] = {}

    # -- Sync interface ---------------------------------------------------

    def save(self, entity: T) -> None:
        self._cache[entity.id] = entity
        spawn(self._persist_fn(entity), name=f"persist-{entity.id}")

    def get(self, entity_id: str) -> T | None:
        return self._cache.get(entity_id)

    def delete(self, entity_id: str) -> bool:
        removed = self._cache.pop(entity_id, None) is not None
        if removed:
            spawn(self._delete_fn(entity_id), name=f"delete-{entity_id}")
        return removed

    # -- Async interface --------------------------------------------------

    async def aget(self, entity_id: str) -> T | None:
        entity = self._cache.get(entity_id)
        if entity is not None:
            return entity
        entity = await self._load_fn(entity_id)
        if entity is not None:
            self._cache[entity_id] = entity
        return entity

    async def adelete(self, entity_id: str) -> bool:
        removed = entity_id in self._cache
        self._cache.pop(entity_id, None)
        await self._delete_fn(entity_id)
        return removed

"""Unit tests for platform.store — WriteThruStore generic store."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

from veupath_chatbot.platform.store import WriteThruStore


@dataclass
class FakeEntity:
    id: str
    name: str


class SyncFakeStore(WriteThruStore[FakeEntity]):
    """Store variant for sync tests.

    Uses MagicMock (not AsyncMock) for _persist_fn and _delete_fn so that
    calling them does NOT produce an unawaited coroutine. The sync methods
    (save/delete) pass the return value of _persist_fn/_delete_fn to spawn(),
    and since spawn is patched, nothing needs to be awaitable.
    """

    _persist_fn = staticmethod(MagicMock())
    _load_fn = staticmethod(MagicMock(return_value=None))
    _delete_fn = staticmethod(MagicMock())


class AsyncFakeStore(WriteThruStore[FakeEntity]):
    """Store variant for async tests. Uses AsyncMock for proper awaiting."""

    _persist_fn = staticmethod(AsyncMock())
    _load_fn = staticmethod(AsyncMock(return_value=None))
    _delete_fn = staticmethod(AsyncMock())


def _fresh_sync_store() -> SyncFakeStore:
    SyncFakeStore._persist_fn = staticmethod(MagicMock())
    SyncFakeStore._load_fn = staticmethod(MagicMock(return_value=None))
    SyncFakeStore._delete_fn = staticmethod(MagicMock())
    return SyncFakeStore()


def _fresh_async_store() -> AsyncFakeStore:
    AsyncFakeStore._persist_fn = staticmethod(AsyncMock())
    AsyncFakeStore._load_fn = staticmethod(AsyncMock(return_value=None))
    AsyncFakeStore._delete_fn = staticmethod(AsyncMock())
    return AsyncFakeStore()


class TestWriteThruStoreSync:
    """Sync interface: save, get, delete.

    Uses SyncFakeStore with MagicMock DB functions (no coroutines created)
    and patches spawn() to prevent background task creation.
    """

    @patch("veupath_chatbot.platform.store.spawn")
    def test_get_returns_none_when_empty(self, mock_spawn):
        store = _fresh_sync_store()
        assert store.get("nonexistent") is None

    @patch("veupath_chatbot.platform.store.spawn")
    def test_save_stores_in_cache(self, mock_spawn):
        store = _fresh_sync_store()
        entity = FakeEntity(id="abc", name="Test")
        store.save(entity)

        assert store.get("abc") is entity
        mock_spawn.assert_called_once()

    @patch("veupath_chatbot.platform.store.spawn")
    def test_save_overwrites_existing(self, mock_spawn):
        store = _fresh_sync_store()
        e1 = FakeEntity(id="abc", name="V1")
        e2 = FakeEntity(id="abc", name="V2")
        store.save(e1)
        store.save(e2)

        result = store.get("abc")
        assert result is e2
        assert result.name == "V2"

    @patch("veupath_chatbot.platform.store.spawn")
    def test_delete_removes_from_cache(self, mock_spawn):
        store = _fresh_sync_store()
        entity = FakeEntity(id="abc", name="Test")
        store.save(entity)
        assert store.get("abc") is entity

        removed = store.delete("abc")
        assert removed is True
        assert store.get("abc") is None

    @patch("veupath_chatbot.platform.store.spawn")
    def test_delete_nonexistent_returns_false(self, mock_spawn):
        store = _fresh_sync_store()
        removed = store.delete("nonexistent")
        assert removed is False
        mock_spawn.assert_not_called()

    @patch("veupath_chatbot.platform.store.spawn")
    def test_delete_spawns_db_delete(self, mock_spawn):
        store = _fresh_sync_store()
        entity = FakeEntity(id="abc", name="Test")
        store.save(entity)
        mock_spawn.reset_mock()

        store.delete("abc")
        mock_spawn.assert_called_once()

    @patch("veupath_chatbot.platform.store.spawn")
    def test_save_calls_spawn_with_persist_name(self, mock_spawn):
        store = _fresh_sync_store()
        entity = FakeEntity(id="xyz", name="Named")
        store.save(entity)

        call_kwargs = mock_spawn.call_args
        assert call_kwargs[1]["name"] == "persist-xyz"

    @patch("veupath_chatbot.platform.store.spawn")
    def test_delete_calls_spawn_with_delete_name(self, mock_spawn):
        store = _fresh_sync_store()
        store._cache["xyz"] = FakeEntity(id="xyz", name="X")
        store.delete("xyz")

        call_kwargs = mock_spawn.call_args
        assert call_kwargs[1]["name"] == "delete-xyz"


class TestWriteThruStoreAsync:
    """Async interface: aget, adelete.

    Uses AsyncFakeStore with AsyncMock DB functions for proper awaiting.
    """

    async def test_aget_returns_cached_entity(self):
        store = _fresh_async_store()
        entity = FakeEntity(id="abc", name="Cached")
        store._cache["abc"] = entity

        result = await store.aget("abc")
        assert result is entity
        AsyncFakeStore._load_fn.assert_not_called()

    async def test_aget_loads_from_db_on_cache_miss(self):
        store = _fresh_async_store()
        db_entity = FakeEntity(id="abc", name="FromDB")
        AsyncFakeStore._load_fn.return_value = db_entity

        result = await store.aget("abc")
        assert result is db_entity
        assert result.name == "FromDB"
        AsyncFakeStore._load_fn.assert_called_once_with("abc")
        assert store._cache["abc"] is db_entity

    async def test_aget_returns_none_when_not_in_db(self):
        store = _fresh_async_store()
        AsyncFakeStore._load_fn.return_value = None

        result = await store.aget("missing")
        assert result is None
        AsyncFakeStore._load_fn.assert_called_once_with("missing")
        assert "missing" not in store._cache

    async def test_adelete_calls_db_delete(self):
        store = _fresh_async_store()
        store._cache["abc"] = FakeEntity(id="abc", name="Test")

        result = await store.adelete("abc")
        assert result is True
        assert "abc" not in store._cache
        AsyncFakeStore._delete_fn.assert_called_once_with("abc")

    async def test_adelete_returns_false_for_nonexistent(self):
        store = _fresh_async_store()
        result = await store.adelete("nonexistent")
        assert result is False
        AsyncFakeStore._delete_fn.assert_called_once_with("nonexistent")

    async def test_aget_after_cache_set_uses_cache(self):
        store = _fresh_async_store()
        entity = FakeEntity(id="abc", name="Saved")
        store._cache["abc"] = entity

        result = await store.aget("abc")
        assert result is entity
        AsyncFakeStore._load_fn.assert_not_called()

    async def test_aget_caches_loaded_entity_for_subsequent_calls(self):
        store = _fresh_async_store()
        db_entity = FakeEntity(id="abc", name="FromDB")
        AsyncFakeStore._load_fn.return_value = db_entity

        await store.aget("abc")
        assert AsyncFakeStore._load_fn.call_count == 1

        result = await store.aget("abc")
        assert result is db_entity
        assert AsyncFakeStore._load_fn.call_count == 1

    async def test_adelete_removes_from_cache_and_calls_db(self):
        store = _fresh_async_store()
        store._cache["abc"] = FakeEntity(id="abc", name="X")

        await store.adelete("abc")
        assert "abc" not in store._cache
        AsyncFakeStore._delete_fn.assert_called_once_with("abc")

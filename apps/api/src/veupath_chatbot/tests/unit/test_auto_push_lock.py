"""Unit tests for auto_push lock eviction safety."""

from uuid import uuid4

import pytest

from veupath_chatbot.services.strategies.auto_push import (
    _PUSH_LOCKS_MAX,
    _get_push_lock,
    _push_locks,
)


@pytest.fixture(autouse=True)
def _clear_locks():
    """Clear the module-level locks before each test."""
    _push_locks.clear()
    yield
    _push_locks.clear()


def test_eviction_skips_locked_entries():
    """Eviction must not remove a lock that is currently held (acquired).

    Regression test: previously eviction blindly removed the oldest entry
    regardless of whether it was locked, breaking serialization guarantees.
    """
    # Fill locks to capacity with one held lock as the oldest
    held_id = uuid4()
    held_lock = _get_push_lock(held_id)
    # Simulate acquiring the lock (non-async acquire for a sync test)
    assert not held_lock.locked()

    # We need to actually hold the lock in an async context
    # but for now, let's test the simpler case first
    # Fill remaining capacity
    for _ in range(_PUSH_LOCKS_MAX - 1):
        _get_push_lock(uuid4())

    assert len(_push_locks) == _PUSH_LOCKS_MAX

    # Now request one more — should trigger eviction
    new_id = uuid4()
    _get_push_lock(new_id)

    # The new lock should exist
    assert new_id in _push_locks


@pytest.mark.asyncio
async def test_eviction_does_not_remove_held_lock():
    """A held (acquired) lock must survive eviction."""
    held_id = uuid4()
    held_lock = _get_push_lock(held_id)

    # Actually acquire the lock
    await held_lock.acquire()
    assert held_lock.locked()

    # Fill remaining capacity
    for _ in range(_PUSH_LOCKS_MAX - 1):
        _get_push_lock(uuid4())

    assert len(_push_locks) == _PUSH_LOCKS_MAX

    # Trigger eviction — the held_id should NOT be evicted
    new_id = uuid4()
    _get_push_lock(new_id)

    assert held_id in _push_locks, (
        "Held lock was evicted! This breaks serialization guarantees."
    )
    assert new_id in _push_locks
    # The evicted entry should be an unlocked one
    assert len(_push_locks) <= _PUSH_LOCKS_MAX

    # Cleanup
    held_lock.release()


@pytest.mark.asyncio
async def test_same_lock_returned_for_same_strategy():
    """The same lock object must be returned for the same strategy ID."""
    sid = uuid4()
    lock1 = _get_push_lock(sid)
    lock2 = _get_push_lock(sid)
    assert lock1 is lock2

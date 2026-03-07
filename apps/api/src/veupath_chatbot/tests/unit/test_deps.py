"""Tests for HTTP dependency injection layer (deps.py).

Covers:
- get_experiment_owned_by_user: ownership check, not-found, forbidden
- get_experiments_owned_by_user: parallel fetch, ownership, not-found
- Inconsistency between single and multi experiment ownership checks
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from veupath_chatbot.platform.errors import ForbiddenError, NotFoundError
from veupath_chatbot.transport.http.deps import (
    get_experiment_owned_by_user,
    get_experiments_owned_by_user,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeExperiment:
    """Minimal stand-in for Experiment with user_id."""

    id: str = "exp-1"
    user_id: str | None = None


def _make_store(experiments: dict[str, FakeExperiment | None]):
    """Create a mock experiment store that returns from a dict."""
    store = AsyncMock()

    async def fake_aget(eid: str):
        return experiments.get(eid)

    store.aget = fake_aget
    return store


# ---------------------------------------------------------------------------
# get_experiment_owned_by_user
# ---------------------------------------------------------------------------


class TestGetExperimentOwnedByUser:
    async def test_returns_experiment_when_owned(self) -> None:
        user_id = uuid4()
        exp = FakeExperiment(id="exp-1", user_id=str(user_id))
        store = _make_store({"exp-1": exp})

        with patch(
            "veupath_chatbot.transport.http.deps.get_experiment_store",
            return_value=store,
        ):
            result = await get_experiment_owned_by_user("exp-1", user_id)
            assert result.id == "exp-1"

    async def test_raises_not_found_when_missing(self) -> None:
        store = _make_store({})

        with (
            patch(
                "veupath_chatbot.transport.http.deps.get_experiment_store",
                return_value=store,
            ),
            pytest.raises(NotFoundError, match="Experiment not found"),
        ):
            await get_experiment_owned_by_user("nonexistent", uuid4())

    async def test_raises_forbidden_when_not_owned(self) -> None:
        owner_id = uuid4()
        other_id = uuid4()
        exp = FakeExperiment(id="exp-1", user_id=str(owner_id))
        store = _make_store({"exp-1": exp})

        with (
            patch(
                "veupath_chatbot.transport.http.deps.get_experiment_store",
                return_value=store,
            ),
            pytest.raises(ForbiddenError),
        ):
            await get_experiment_owned_by_user("exp-1", other_id)

    async def test_raises_forbidden_when_user_id_is_none(self) -> None:
        """Experiment with user_id=None is not accessible to any user.

        This is because `None != str(uuid)` evaluates to True.
        """
        exp = FakeExperiment(id="exp-1", user_id=None)
        store = _make_store({"exp-1": exp})

        with (
            patch(
                "veupath_chatbot.transport.http.deps.get_experiment_store",
                return_value=store,
            ),
            pytest.raises(ForbiddenError),
        ):
            await get_experiment_owned_by_user("exp-1", uuid4())


# ---------------------------------------------------------------------------
# get_experiments_owned_by_user
# ---------------------------------------------------------------------------


class TestGetExperimentsOwnedByUser:
    async def test_returns_all_owned_experiments(self) -> None:
        user_id = str(uuid4())
        exp1 = FakeExperiment(id="exp-1", user_id=user_id)
        exp2 = FakeExperiment(id="exp-2", user_id=user_id)
        store = _make_store({"exp-1": exp1, "exp-2": exp2})

        with patch(
            "veupath_chatbot.transport.http.deps.get_experiment_store",
            return_value=store,
        ):
            result = await get_experiments_owned_by_user(["exp-1", "exp-2"], user_id)
            assert len(result) == 2

    async def test_raises_not_found_when_any_missing(self) -> None:
        user_id = str(uuid4())
        exp1 = FakeExperiment(id="exp-1", user_id=user_id)
        store = _make_store({"exp-1": exp1})

        with (
            patch(
                "veupath_chatbot.transport.http.deps.get_experiment_store",
                return_value=store,
            ),
            pytest.raises(NotFoundError, match="exp-2"),
        ):
            await get_experiments_owned_by_user(["exp-1", "exp-2"], user_id)

    async def test_raises_forbidden_when_not_owned(self) -> None:
        owner_id = str(uuid4())
        other_id = str(uuid4())
        exp = FakeExperiment(id="exp-1", user_id=owner_id)
        store = _make_store({"exp-1": exp})

        with (
            patch(
                "veupath_chatbot.transport.http.deps.get_experiment_store",
                return_value=store,
            ),
            pytest.raises(ForbiddenError),
        ):
            await get_experiments_owned_by_user(["exp-1"], other_id)

    async def test_null_user_id_experiment_rejected(self) -> None:
        """Experiments with user_id=None are rejected by both fetch paths.

        Both ``get_experiment_owned_by_user`` and ``get_experiments_owned_by_user``
        use a strict ``exp.user_id != user_id`` check, so ``None != str(uuid)``
        is ``True`` and raises ``ForbiddenError``.
        """
        exp = FakeExperiment(id="exp-1", user_id=None)
        store = _make_store({"exp-1": exp})

        with (
            patch(
                "veupath_chatbot.transport.http.deps.get_experiment_store",
                return_value=store,
            ),
            pytest.raises(ForbiddenError),
        ):
            await get_experiments_owned_by_user(["exp-1"], str(uuid4()))

    async def test_empty_experiment_ids_returns_empty(self) -> None:
        store = _make_store({})

        with patch(
            "veupath_chatbot.transport.http.deps.get_experiment_store",
            return_value=store,
        ):
            result = await get_experiments_owned_by_user([], str(uuid4()))
            assert result == []

    async def test_preserves_order(self) -> None:
        user_id = str(uuid4())
        exp1 = FakeExperiment(id="exp-a", user_id=user_id)
        exp2 = FakeExperiment(id="exp-b", user_id=user_id)
        exp3 = FakeExperiment(id="exp-c", user_id=user_id)
        store = _make_store({"exp-a": exp1, "exp-b": exp2, "exp-c": exp3})

        with patch(
            "veupath_chatbot.transport.http.deps.get_experiment_store",
            return_value=store,
        ):
            result = await get_experiments_owned_by_user(
                ["exp-c", "exp-a", "exp-b"], user_id
            )
            assert [r.id for r in result] == ["exp-c", "exp-a", "exp-b"]

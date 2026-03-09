from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from veupath_chatbot.services.gene_sets.operations import GeneSetService


@pytest.fixture
def service():
    store = MagicMock()
    store.save = MagicMock()
    return GeneSetService(store)


@pytest.mark.asyncio
async def test_create_deduplicates_gene_ids(service):
    """Gene IDs with duplicates should be deduplicated at creation time."""
    gs = await service.create(
        user_id=uuid4(),
        name="test",
        site_id="PlasmoDB",
        gene_ids=["g1", "g2", "g1", "g3", "g2"],
        source="paste",
    )
    assert gs.gene_ids == ["g1", "g2", "g3"]


@pytest.mark.asyncio
async def test_create_preserves_order_after_dedup(service):
    """Deduplication should preserve first-occurrence order."""
    gs = await service.create(
        user_id=uuid4(),
        name="test",
        site_id="PlasmoDB",
        gene_ids=["z1", "a1", "z1", "b1", "a1"],
        source="paste",
    )
    assert gs.gene_ids == ["z1", "a1", "b1"]


@pytest.mark.asyncio
async def test_create_no_duplicates_passes_through(service):
    """Gene IDs without duplicates should pass through unchanged."""
    gs = await service.create(
        user_id=uuid4(),
        name="test",
        site_id="PlasmoDB",
        gene_ids=["g1", "g2", "g3"],
        source="paste",
    )
    assert gs.gene_ids == ["g1", "g2", "g3"]

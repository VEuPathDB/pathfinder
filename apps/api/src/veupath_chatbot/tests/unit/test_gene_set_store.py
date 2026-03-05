"""Tests for GeneSetStore."""

from veupath_chatbot.services.gene_sets.store import GeneSetStore
from veupath_chatbot.services.gene_sets.types import GeneSet


def _make_set(
    id: str = "gs-1", site_id: str = "plasmo", gene_ids: list[str] | None = None
) -> GeneSet:
    return GeneSet(
        id=id,
        name=f"Test Set {id}",
        site_id=site_id,
        gene_ids=gene_ids or ["GENE1", "GENE2"],
        source="paste",
    )


def test_save_and_get():
    store = GeneSetStore()
    gs = _make_set()
    store.save(gs)
    assert store.get("gs-1") is gs


def test_get_missing_returns_none():
    store = GeneSetStore()
    assert store.get("nonexistent") is None


def test_list_all():
    store = GeneSetStore()
    store.save(_make_set("a"))
    store.save(_make_set("b"))
    assert len(store.list_all()) == 2


def test_list_all_filters_by_site():
    store = GeneSetStore()
    store.save(_make_set("a", site_id="plasmo"))
    store.save(_make_set("b", site_id="toxo"))
    assert len(store.list_all(site_id="plasmo")) == 1


def test_delete():
    store = GeneSetStore()
    store.save(_make_set("a"))
    assert store.delete("a") is True
    assert store.get("a") is None


def test_delete_missing_returns_false():
    store = GeneSetStore()
    assert store.delete("nope") is False

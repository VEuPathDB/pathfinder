"""In-memory store for gene sets (session-scoped, no DB persistence)."""

from __future__ import annotations

from uuid import UUID

from veupath_chatbot.services.gene_sets.types import GeneSet


class GeneSetStore:
    """In-memory gene set store.

    API contract:
    - save(gene_set) — store or update
    - get(gene_set_id) — retrieve by ID
    - list_all(site_id=None) — list all sets, optionally filtered by site
    - list_for_user(user_id, site_id=None) — list for a specific user
    - delete(gene_set_id) — remove by ID
    """

    def __init__(self) -> None:
        self._sets: dict[str, GeneSet] = {}

    def save(self, gene_set: GeneSet) -> None:
        self._sets[gene_set.id] = gene_set

    def get(self, gene_set_id: str) -> GeneSet | None:
        return self._sets.get(gene_set_id)

    def list_all(self, *, site_id: str | None = None) -> list[GeneSet]:
        results = list(self._sets.values())
        if site_id is not None:
            results = [gs for gs in results if gs.site_id == site_id]
        return sorted(results, key=lambda gs: gs.created_at, reverse=True)

    def list_for_user(
        self,
        user_id: UUID,
        *,
        site_id: str | None = None,
    ) -> list[GeneSet]:
        results = [gs for gs in self._sets.values() if gs.user_id == user_id]
        if site_id is not None:
            results = [gs for gs in results if gs.site_id == site_id]
        return sorted(results, key=lambda gs: gs.created_at, reverse=True)

    def delete(self, gene_set_id: str) -> bool:
        return self._sets.pop(gene_set_id, None) is not None


_store: GeneSetStore | None = None


def get_gene_set_store() -> GeneSetStore:
    global _store
    if _store is None:
        _store = GeneSetStore()
    return _store

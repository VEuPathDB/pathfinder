"""Shared base for literature search API clients."""

from __future__ import annotations

from typing import cast

from veupath_chatbot.domain.research.citations import (
    Citation,
    CitationSource,
    _new_citation_id,
    _now_iso,
    ensure_unique_citation_tags,
)
from veupath_chatbot.platform.types import JSONArray, JSONObject, JSONValue

API_USER_AGENT = "pathfinder-planner/1.0 (+https://pathfinder.veupathdb.org)"


class BaseClient:
    """Common initialisation for all literature API clients."""

    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self._timeout = timeout_seconds


def make_citation(
    *,
    source: CitationSource,
    id_prefix: str,
    title: str,
    url: str | None = None,
    authors: list[str] | None = None,
    year: int | None = None,
    doi: str | None = None,
    pmid: str | None = None,
    snippet: str | None = None,
) -> JSONObject:
    """Build a citation dict from common fields."""
    return Citation(
        id=_new_citation_id(id_prefix),
        source=source,
        title=title,
        url=url,
        authors=authors,
        year=year,
        doi=doi,
        pmid=pmid,
        snippet=snippet,
        accessed_at=_now_iso(),
    ).to_dict()


def build_response(
    *,
    query: str,
    source: str,
    results: JSONArray,
    citations: list[JSONObject],
) -> JSONObject:
    """Build the standard client response dict, deduplicating citation tags."""
    ensure_unique_citation_tags(citations)
    return {
        "query": query,
        "source": source,
        "results": results,
        "citations": cast(JSONValue, citations),
    }

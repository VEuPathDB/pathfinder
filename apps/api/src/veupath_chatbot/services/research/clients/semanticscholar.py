"""Semantic Scholar API client."""

from __future__ import annotations

from typing import cast

import httpx

from veupath_chatbot.platform.types import JSONArray, JSONObject, JSONValue
from veupath_chatbot.services.research.clients._base import (
    API_USER_AGENT,
    BaseClient,
    build_response,
    make_citation,
)
from veupath_chatbot.services.research.utils import truncate_text


class SemanticScholarClient(BaseClient):
    """Client for Semantic Scholar API."""

    async def search(
        self, query: str, *, limit: int, abstract_max_chars: int
    ) -> JSONObject:
        """Search Semantic Scholar."""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": str(limit),
            "fields": "title,year,authors,url,abstract,journal,externalIds",
        }
        async with httpx.AsyncClient(
            timeout=self._timeout, headers={"User-Agent": API_USER_AGENT}
        ) as client:
            resp = await client.get(url, params=params, follow_redirects=True)
            resp.raise_for_status()
            payload = resp.json()

        items = payload.get("data", []) if isinstance(payload, dict) else []
        results: JSONArray = []
        citations: list[JSONObject] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            year = item.get("year") if isinstance(item.get("year"), int) else None
            url_item = item.get("url") if isinstance(item.get("url"), str) else None
            authors = None
            raw_authors = item.get("authors")
            if isinstance(raw_authors, list):
                authors = [
                    str(a.get("name"))
                    for a in raw_authors
                    if isinstance(a, dict) and a.get("name")
                ]
            abstract = (
                item.get("abstract") if isinstance(item.get("abstract"), str) else None
            )
            abstract = truncate_text(abstract, abstract_max_chars)
            journal = None
            j = item.get("journal")
            if isinstance(j, dict) and j.get("name"):
                journal = str(j.get("name"))
            ext = item.get("externalIds")
            doi = None
            pmid = None
            if isinstance(ext, dict):
                if isinstance(ext.get("DOI"), str):
                    doi = ext.get("DOI")
                if isinstance(ext.get("PubMed"), str):
                    pmid = ext.get("PubMed")

            result_url = url_item or (f"https://doi.org/{doi}" if doi else None)
            results.append(
                {
                    "title": title,
                    "year": year,
                    "doi": doi,
                    "pmid": pmid,
                    "url": result_url,
                    "authors": cast(JSONValue, authors),
                    "journalTitle": journal,
                    "abstract": abstract,
                    "snippet": abstract or journal,
                }
            )
            citations.append(
                make_citation(
                    source="semanticscholar",
                    id_prefix="s2",
                    title=title or (url_item or "Semantic Scholar result"),
                    url=result_url,
                    authors=authors,
                    year=year,
                    doi=doi,
                    pmid=pmid,
                    snippet=abstract or journal,
                )
            )
        return build_response(
            query=query,
            source="semanticscholar",
            results=results,
            citations=citations,
        )

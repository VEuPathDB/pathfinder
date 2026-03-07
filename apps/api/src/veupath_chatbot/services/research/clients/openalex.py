"""OpenAlex API client."""

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


class OpenAlexClient(BaseClient):
    """Client for OpenAlex API."""

    async def search(
        self, query: str, *, limit: int, abstract_max_chars: int
    ) -> JSONObject:
        """Search OpenAlex."""
        url = "https://api.openalex.org/works"
        params = {"search": query, "per-page": str(limit)}
        async with httpx.AsyncClient(
            timeout=self._timeout, headers={"User-Agent": API_USER_AGENT}
        ) as client:
            resp = await client.get(url, params=params, follow_redirects=True)
            resp.raise_for_status()
            payload = resp.json()

        items = payload.get("results", []) if isinstance(payload, dict) else []
        results: JSONArray = []
        citations: list[JSONObject] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            year_i = item.get("publication_year")
            year = (
                int(year_i)
                if isinstance(year_i, (int, str)) and str(year_i).isdigit()
                else None
            )
            doi = item.get("doi")
            doi = (
                str(doi).replace("https://doi.org/", "")
                if isinstance(doi, str)
                else None
            )
            url_item = item.get("id") if isinstance(item.get("id"), str) else None
            journal = None
            hv = item.get("host_venue")
            if isinstance(hv, dict):
                journal = hv.get("display_name")
            journal = str(journal).strip() if journal else None
            authors: list[str] | None = None
            auths = item.get("authorships")
            if isinstance(auths, list):
                authors = []
                for a in auths:
                    if not isinstance(a, dict):
                        continue
                    au = a.get("author")
                    if isinstance(au, dict) and au.get("display_name"):
                        authors.append(str(au.get("display_name")))

            abstract = None
            inv = item.get("abstract_inverted_index")
            if isinstance(inv, dict):
                # Best-effort reconstruction.
                pairs: list[tuple[int, str]] = []
                for word, idxs in inv.items():
                    if not isinstance(word, str) or not isinstance(idxs, list):
                        continue
                    for i in idxs:
                        if isinstance(i, int):
                            pairs.append((i, word))
                if pairs:
                    pairs.sort(key=lambda x: x[0])
                    abstract = " ".join(w for _, w in pairs)
            abstract = truncate_text(abstract, abstract_max_chars)

            result_url = f"https://doi.org/{doi}" if doi else url_item
            results.append(
                {
                    "title": title,
                    "year": year,
                    "doi": doi,
                    "url": result_url,
                    "authors": cast(JSONValue, authors),
                    "journalTitle": journal,
                    "abstract": abstract,
                    "snippet": abstract or journal,
                }
            )
            citations.append(
                make_citation(
                    source="openalex",
                    id_prefix="openalex",
                    title=title or (url_item or "OpenAlex result"),
                    url=result_url,
                    authors=authors,
                    year=year,
                    doi=doi,
                    snippet=abstract or journal,
                )
            )
        return build_response(
            query=query, source="openalex", results=results, citations=citations
        )

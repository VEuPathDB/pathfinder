"""Preprint site search client (bioRxiv, medRxiv)."""

from __future__ import annotations

import asyncio
import re
from typing import Literal

import httpx

from veupath_chatbot.platform.types import JSONArray, JSONObject
from veupath_chatbot.services.research.clients._base import (
    BaseClient,
    build_response,
    make_citation,
)
from veupath_chatbot.services.research.utils import (
    BROWSER_USER_AGENT,
    decode_ddg_redirect,
    fetch_page_summary,
    strip_tags,
)


class PreprintClient(BaseClient):
    """Client for preprint site searches via DuckDuckGo."""

    async def search(
        self,
        query: str,
        *,
        site: str,
        source: Literal["biorxiv", "medrxiv"],
        limit: int,
        include_abstract: bool,
        abstract_max_chars: int,
    ) -> JSONObject:
        """Search preprint sites using DuckDuckGo."""
        # Use DDG HTML endpoint (tests mock duckduckgo.com/html/ for preprints).
        ddg_url = "https://duckduckgo.com/html/"
        params = {"q": f"site:{site} {query}"}
        headers = {
            "User-Agent": "pathfinder-planner/1.0 (+https://pathfinder.veupathdb.org)"
        }
        async with httpx.AsyncClient(timeout=self._timeout, headers=headers) as client:
            resp = await client.get(ddg_url, params=params, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text or ""

        # Reuse the simple result parser shape.
        results: JSONArray = []
        citations: list[JSONObject] = []
        for m in re.finditer(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            html,
            flags=re.IGNORECASE,
        ):
            if len(results) >= limit:
                break
            href = m.group(1)
            title = strip_tags(m.group(2))
            url_item = decode_ddg_redirect(href)
            results.append({"title": title, "url": url_item, "snippet": None})
            citations.append(
                make_citation(
                    source=source,
                    id_prefix=source,
                    title=title or (url_item or f"{source} result"),
                    url=url_item,
                )
            )

        # Optional: fetch a summary if requested (best-effort).
        if include_abstract and results:
            dict_results = [r for r in results if isinstance(r, dict)]
            async with httpx.AsyncClient(
                timeout=min(self._timeout, 15.0),
                headers={
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
            ) as client:
                summaries = await asyncio.gather(
                    *[
                        fetch_page_summary(
                            client,
                            r.get("url"),
                            max_chars=abstract_max_chars,
                        )
                        for r in dict_results
                    ],
                    return_exceptions=True,
                )
            for r, s in zip(dict_results, summaries, strict=True):
                if isinstance(s, str) and s.strip():
                    r["abstract"] = s.strip()
                    r["snippet"] = s.strip()

        return build_response(
            query=query, source=source, results=results, citations=citations
        )

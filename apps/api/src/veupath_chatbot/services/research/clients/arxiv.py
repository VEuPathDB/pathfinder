"""arXiv API client."""

from __future__ import annotations

import re

import httpx

from veupath_chatbot.platform.types import JSONArray, JSONObject
from veupath_chatbot.services.research.clients._base import (
    API_USER_AGENT,
    BaseClient,
    build_response,
    make_citation,
)
from veupath_chatbot.services.research.utils import strip_tags, truncate_text


class ArxivClient(BaseClient):
    """Client for arXiv API."""

    async def search(
        self, query: str, *, limit: int, abstract_max_chars: int
    ) -> JSONObject:
        """Search arXiv."""
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": "0",
            "max_results": str(limit),
        }
        async with httpx.AsyncClient(
            timeout=self._timeout, headers={"User-Agent": API_USER_AGENT}
        ) as client:
            resp = await client.get(url, params=params, follow_redirects=True)
            resp.raise_for_status()
            xml = resp.text or ""

        # Minimal parser: handle empty feeds gracefully (unit tests use empty feed).
        entries = re.findall(
            r"<entry>(.*?)</entry>", xml, flags=re.IGNORECASE | re.DOTALL
        )
        results: JSONArray = []
        citations: list[JSONObject] = []
        for e in entries[:limit]:
            title = strip_tags(
                "".join(
                    re.findall(
                        r"<title>(.*?)</title>", e, flags=re.IGNORECASE | re.DOTALL
                    )
                )
            ).strip()
            link_m = re.search(r'<link[^>]+href="([^"]+)"', e, flags=re.IGNORECASE)
            url_item = link_m.group(1) if link_m else None
            abstract = strip_tags(
                "".join(
                    re.findall(
                        r"<summary>(.*?)</summary>",
                        e,
                        flags=re.IGNORECASE | re.DOTALL,
                    )
                )
            ).strip()
            abstract_truncated = truncate_text(abstract, abstract_max_chars)
            results.append(
                {
                    "title": title,
                    "url": url_item,
                    "abstract": abstract_truncated or "",
                    "snippet": abstract,
                }
            )
            citations.append(
                make_citation(
                    source="arxiv",
                    id_prefix="arxiv",
                    title=title or (url_item or "arXiv result"),
                    url=url_item,
                    snippet=abstract,
                )
            )
        return build_response(
            query=query, source="arxiv", results=results, citations=citations
        )

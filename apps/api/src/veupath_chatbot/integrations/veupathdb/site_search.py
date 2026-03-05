"""Integration for VEuPathDB "site search" service.

This is the same backend used by the web UI route `/app/search`.

Important: this service is hosted at the site origin root (e.g. https://plasmodb.org/site-search),
not under the WDK service prefix (e.g. https://plasmodb.org/plasmo/service).
"""

from __future__ import annotations

import re
from typing import cast
from urllib.parse import urlparse

import httpx
from veupath_chatbot.integrations.veupathdb.site_router import get_site_router
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONObject, JSONValue

logger = get_logger(__name__)

# Shared client for site-search requests (avoids connection-per-request overhead).
_site_search_client: httpx.AsyncClient | None = None


def _get_site_search_client() -> httpx.AsyncClient:
    """Get or create the shared site-search HTTP client."""
    global _site_search_client
    if _site_search_client is None or _site_search_client.is_closed:
        _site_search_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
    return _site_search_client


def strip_html_tags(value: str) -> str:
    # site-search highlights matches with <em> tags.
    return re.sub(r"</?[^>]+>", "", value or "").strip()


async def query_site_search(
    site_id: str,
    *,
    search_text: str,
    document_type: str | None = None,
    organisms: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> JSONObject:
    """Query the site's /site-search endpoint and return parsed JSON.

    :param organisms: Optional organism names to restrict results to.
    """
    router = get_site_router()
    site = router.get_site(site_id)

    # site-search is hosted at the site origin, not under the WDK service path.
    parsed = urlparse(site.base_url)
    url = f"{parsed.scheme}://{parsed.netloc}/site-search"

    payload: JSONObject = {
        "searchText": search_text or "",
        "pagination": {"offset": int(offset), "numRecords": int(limit)},
        "restrictToProject": site.project_id,
    }
    if document_type:
        payload["documentTypeFilter"] = {"documentType": document_type}
    if organisms:
        payload["restrictSearchToOrganisms"] = cast(JSONValue, organisms)

    client = _get_site_search_client()
    resp = await client.post(url, json=payload)
    resp.raise_for_status()
    return resp.json() if resp.content else {}

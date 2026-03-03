from __future__ import annotations

from itertools import batched

from qdrant_client import AsyncQdrantClient
from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONObject

logger = get_logger(__name__)


def extract_search_name(obj: JSONObject) -> str:
    """Extract a search/record-type name, preferring urlSegment over name."""
    return str(obj.get("urlSegment") or obj.get("name") or "").strip()


def parse_sites(value: str) -> list[str] | None:
    """Parse a comma-separated list of site IDs or 'all' → None (meaning all)."""
    v = (value or "").strip()
    if not v or v == "all":
        return None
    return [s.strip() for s in v.split(",") if s.strip()]


async def existing_point_ids(
    *,
    qdrant_client: AsyncQdrantClient,
    collection: str,
    ids: list[str],
    chunk_size: int = 256,
) -> set[str]:
    """Return subset of ids that already exist in Qdrant.

    If the collection doesn't exist yet, returns an empty set.
    """
    if not ids:
        return set()

    existing: set[str] = set()

    for chunk in batched(ids, max(1, int(chunk_size)), strict=False):
        try:
            points = await qdrant_client.retrieve(
                collection_name=collection,
                ids=chunk,
                with_payload=False,
                with_vectors=False,
            )
        except Exception as exc:
            # Missing collection is a normal state pre-ingestion.
            msg = str(exc)
            if "doesn't exist" in msg or "Not found: Collection" in msg:
                return set()
            logger.warning(
                "Qdrant retrieve failed during existence check",
                collection=collection,
                error=msg,
                errorType=type(exc).__name__,
            )
            raise

        for p in points or []:
            existing.add(str(p.id))

    return existing

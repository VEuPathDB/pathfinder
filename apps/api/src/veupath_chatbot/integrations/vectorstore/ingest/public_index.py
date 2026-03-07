from __future__ import annotations

from typing import Any, cast

from veupath_chatbot.integrations.embeddings.openai_embeddings import OpenAIEmbeddings
from veupath_chatbot.integrations.vectorstore.collections import EXAMPLE_PLANS_V1
from veupath_chatbot.integrations.vectorstore.ingest.public_strategies_helpers import (
    EMBED_TEXT_MAX_CHARS,
    truncate,
)
from veupath_chatbot.integrations.vectorstore.qdrant_store import QdrantStore
from veupath_chatbot.platform.types import JSONArray, JSONObject, JSONValue


async def _flush_batch(
    *,
    store: QdrantStore,
    embedder: OpenAIEmbeddings,
    points: JSONArray,
    texts: list[str],
) -> None:
    """Embed *texts*, pair with *points* metadata, and upsert to the example plans collection.

    Uses a per-item fallback when the batch embed call fails (e.g. a single
    oversized text causes the whole batch to be rejected by the API).
    """
    if not points:
        return

    safe_texts = [truncate(t, max_chars=EMBED_TEXT_MAX_CHARS) for t in texts]

    try:
        vectors = await embedder.embed_texts(safe_texts)
    except Exception:
        vectors = []
        for t in safe_texts:
            tt = truncate(t, max_chars=10_000)
            vectors.append((await embedder.embed_texts([tt]))[0])

    upsert_points: JSONArray = []
    for p, v in zip(points, vectors, strict=True):
        if not isinstance(p, dict):
            continue
        payload_raw = p.get("payload")
        point_dict: JSONObject = {
            "id": p.get("id"),
            "vector": cast(JSONValue, v),
            "payload": payload_raw if isinstance(payload_raw, dict) else {},
        }
        upsert_points.append(cast(Any, point_dict))

    await store.upsert(collection=EXAMPLE_PLANS_V1, points=upsert_points)
    points.clear()
    texts.clear()

"""Shared helper for building combined RAG + WDK tool outputs."""

from veupath_chatbot.platform.types import JSONObject, JSONValue


def combined_result(
    *,
    rag: JSONValue,
    wdk: JSONValue,
    rag_note: str | None = None,
    wdk_note: str | None = None,
) -> JSONObject:
    """Standardize combined (RAG + WDK) tool outputs.

    Callers always receive both data sources and can decide which to trust
    based on availability/staleness.

    :param rag: RAG context.
    :param wdk: WDK context.
    :param rag_note: RAG note (default: None).
    :param wdk_note: WDK note (default: None).
    """
    return {
        "rag": {"data": rag, "note": rag_note or ""},
        "wdk": {"data": wdk, "note": wdk_note or ""},
    }

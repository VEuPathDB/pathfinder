"""Tests for vectorstore collection name constants."""

from veupath_chatbot.integrations.vectorstore.collections import (
    EXAMPLE_PLANS_V1,
    WDK_DEPENDENT_VOCAB_CACHE_V1,
    WDK_RECORD_TYPES_V1,
    WDK_SEARCHES_V1,
)


def test_collection_names_are_non_empty_strings() -> None:
    for name in (
        WDK_RECORD_TYPES_V1,
        WDK_SEARCHES_V1,
        WDK_DEPENDENT_VOCAB_CACHE_V1,
        EXAMPLE_PLANS_V1,
    ):
        assert isinstance(name, str)
        assert len(name) > 0


def test_collection_names_are_unique() -> None:
    names = [
        WDK_RECORD_TYPES_V1,
        WDK_SEARCHES_V1,
        WDK_DEPENDENT_VOCAB_CACHE_V1,
        EXAMPLE_PLANS_V1,
    ]
    assert len(names) == len(set(names))


def test_collection_names_are_lowercase_and_safe() -> None:
    """Qdrant collection names should be lowercase with underscores."""
    import re

    for name in (
        WDK_RECORD_TYPES_V1,
        WDK_SEARCHES_V1,
        WDK_DEPENDENT_VOCAB_CACHE_V1,
        EXAMPLE_PLANS_V1,
    ):
        assert re.fullmatch(r"[a-z0-9_]+", name), f"Bad collection name: {name!r}"

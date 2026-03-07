"""Tests for pure helpers in vectorstore bootstrap.py."""

from veupath_chatbot.integrations.vectorstore.bootstrap import _known_embedding_dims


class TestKnownEmbeddingDims:
    def test_text_embedding_3_small(self) -> None:
        assert _known_embedding_dims("text-embedding-3-small") == 1536

    def test_text_embedding_3_large(self) -> None:
        assert _known_embedding_dims("text-embedding-3-large") == 3072

    def test_unknown_model_returns_none(self) -> None:
        assert _known_embedding_dims("some-unknown-model") is None

    def test_empty_string_returns_none(self) -> None:
        assert _known_embedding_dims("") is None

    def test_whitespace_stripped(self) -> None:
        assert _known_embedding_dims("  text-embedding-3-small  ") == 1536

    def test_none_like_empty_returns_none(self) -> None:
        # The function does `(model or "").strip()`, so passing something falsy
        # that is not None but string-ish should still work.
        assert _known_embedding_dims("   ") is None

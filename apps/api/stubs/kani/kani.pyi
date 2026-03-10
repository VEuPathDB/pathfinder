"""Type stub for kani.kani — the core Kani agent class."""

from collections.abc import AsyncIterable, Sequence
from typing import Any

from kani.ai_function import AIFunction
from kani.engines.base import BaseEngine
from kani.models import ChatMessage

class Kani:
    """Base class for kani agents."""

    chat_history: list[ChatMessage]
    engine: BaseEngine
    # Subclasses (PathfinderAgent, ExperimentAnalysisAgent) define event_queue.
    # Declared here so services layer can set it without attr-defined errors.
    event_queue: Any

    def __init__(
        self,
        engine: BaseEngine,
        system_prompt: str | None = None,
        always_included_messages: list[ChatMessage] | None = None,
        desired_response_tokens: int | None = None,
        chat_history: list[ChatMessage] | None = None,
        functions: list[AIFunction] | None = None,
        retry_attempts: int = 1,
    ) -> None: ...
    async def chat_round(
        self,
        query: str | Sequence[Any] | None,
        **kwargs: Any,
    ) -> ChatMessage: ...
    async def chat_round_str(
        self,
        query: str | Sequence[Any] | None,
        **kwargs: Any,
    ) -> str: ...
    def full_round(
        self,
        query: str | Sequence[Any] | None,
        *,
        max_function_rounds: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[ChatMessage]: ...
    def full_round_str(
        self,
        query: str | Sequence[Any] | None,
        **kwargs: Any,
    ) -> AsyncIterable[str]: ...
    def full_round_stream(
        self,
        query: str | Sequence[Any] | None,
        *,
        max_function_rounds: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[Any]: ...

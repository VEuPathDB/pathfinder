"""Type stub for kani.engines.anthropic."""

from typing import Any

from kani.engines.base import BaseEngine

class AnthropicEngine(BaseEngine):
    def __init__(self, api_key: str, model: str, **kwargs: Any) -> None: ...

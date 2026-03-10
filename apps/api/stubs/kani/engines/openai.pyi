"""Type stub for kani.engines.openai."""

from typing import Any

from kani.engines.base import BaseEngine

class OpenAIEngine(BaseEngine):
    def __init__(self, api_key: str, model: str, **kwargs: Any) -> None: ...

"""Type stub for kani.engines.google."""

from typing import Any

from kani.engines.base import BaseEngine

class GoogleAIEngine(BaseEngine):
    def __init__(self, api_key: str, model: str, **kwargs: Any) -> None: ...

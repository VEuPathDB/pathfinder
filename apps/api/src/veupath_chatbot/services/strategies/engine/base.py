"""Shared base class for strategy tool implementations (service layer)."""

from veupath_chatbot.domain.strategy.session import StrategySession


class StrategyToolsBase:
    """Base strategy tools class with shared state."""

    def __init__(self, session: StrategySession) -> None:
        self.session = session

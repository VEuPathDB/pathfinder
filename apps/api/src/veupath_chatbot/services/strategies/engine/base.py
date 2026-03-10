"""Shared base class for strategy tool implementations (service layer)."""

from veupath_chatbot.domain.strategy.session import StrategyGraph, StrategySession


class StrategyToolsBase:
    """Base strategy tools class with shared state.

    Declares method stubs for methods defined in ``ValidationMixin`` that are
    used by sibling mixins (``GraphOpsMixin``, ``IdMappingMixin``).  The real
    implementations live in ``ValidationMixin``; these stubs exist solely so
    that mypy can verify attribute access in mixin classes without requiring
    the full MRO to be resolved.
    """

    def __init__(self, session: StrategySession) -> None:
        self.session = session

    # -- Stubs satisfied by ValidationMixin in the final composed class --

    def _get_graph(self, graph_id: str | None) -> StrategyGraph | None:
        raise NotImplementedError

    def _is_placeholder_name(self, name: str | None) -> bool:
        raise NotImplementedError

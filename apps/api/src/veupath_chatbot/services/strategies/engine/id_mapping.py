"""WDK ID <-> local ID mapping and record-type resolution."""

from __future__ import annotations

from typing import cast

from veupath_chatbot.domain.strategy.ast import PlanStepNode
from veupath_chatbot.integrations.veupathdb.discovery import get_discovery_service
from veupath_chatbot.integrations.veupathdb.param_utils import (
    wdk_entity_name,
    wdk_search_matches,
)
from veupath_chatbot.platform.types import JSONObject, JSONValue

from .base import StrategyToolsBase


class IdMappingMixin(StrategyToolsBase):
    def _infer_record_type(self, step: PlanStepNode) -> str | None:
        # Plan steps no longer store record_type; prefer graph-level context when available.
        graph = self._get_graph(None)
        return graph.record_type if graph else None

    async def _resolve_record_type(self, record_type: str | None) -> str | None:
        if not record_type:
            return record_type
        discovery = get_discovery_service()
        record_types = await discovery.get_record_types(self.session.site_id)

        def normalize(value: str) -> str:
            return value.strip().lower()

        normalized = normalize(record_type)
        exact: list[JSONValue] = []
        for rt in record_types:
            if isinstance(rt, (str, dict)):
                if normalize(wdk_entity_name(rt)) == normalized:
                    exact.append(rt)
                elif isinstance(rt, dict):
                    name_raw = rt.get("name")
                    name = name_raw if isinstance(name_raw, str) else ""
                    if normalize(name) == normalized:
                        exact.append(rt)
        if exact:
            if isinstance(exact[0], str):
                return exact[0]
            exact_dict = exact[0] if isinstance(exact[0], dict) else {}
            return cast(
                str,
                exact_dict.get("urlSegment", exact_dict.get("name", record_type)),
            )

        display_matches: list[JSONObject] = []
        for rt in record_types:
            if not isinstance(rt, dict):
                continue
            display_name_raw = rt.get("displayName")
            display_name = display_name_raw if isinstance(display_name_raw, str) else ""
            if normalize(display_name) == normalized:
                display_matches.append(rt)
        if len(display_matches) == 1:
            match_dict = (
                display_matches[0] if isinstance(display_matches[0], dict) else {}
            )
            return cast(
                str,
                match_dict.get("urlSegment", match_dict.get("name", record_type)),
            )

        return record_type

    async def _resolve_record_type_for_search(
        self,
        record_type: str | None,
        search_name: str | None,
        require_match: bool = False,
        allow_fallback: bool = True,
    ) -> str | None:
        resolved = await self._resolve_record_type(record_type)
        if not search_name:
            return resolved
        discovery = get_discovery_service()
        record_types = await discovery.get_record_types(self.session.site_id)

        if resolved:
            try:
                searches = await discovery.get_searches(self.session.site_id, resolved)
                if any(wdk_search_matches(s, search_name) for s in searches):
                    return resolved
            except Exception:
                pass
            if not allow_fallback:
                return None if require_match else resolved

        if not allow_fallback:
            return None if require_match else resolved

        for rt in record_types:
            rt_name = wdk_entity_name(rt)
            if not rt_name:
                continue
            try:
                searches = await discovery.get_searches(self.session.site_id, rt_name)
            except Exception:
                continue
            if any(wdk_search_matches(s, search_name) for s in searches):
                return rt_name

        return None if require_match else resolved

    async def _find_record_type_hint(
        self, search_name: str, exclude: str | None = None
    ) -> str | None:
        discovery = get_discovery_service()
        try:
            record_types = await discovery.get_record_types(self.session.site_id)
        except Exception:
            return None

        for rt in record_types:
            rt_name = wdk_entity_name(rt)
            if not rt_name or (exclude and rt_name == exclude):
                continue
            try:
                searches = await discovery.get_searches(self.session.site_id, rt_name)
            except Exception:
                continue
            if any(wdk_search_matches(s, search_name) for s in searches):
                return rt_name
        return None

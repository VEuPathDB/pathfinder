"""WDK parameter fetching, caching, and expansion."""

from __future__ import annotations

from typing import cast

from veupath_chatbot.domain.parameters.normalize import ParameterNormalizer
from veupath_chatbot.domain.parameters.specs import (
    adapt_param_specs,
    extract_param_specs,
    find_input_step_param,
)
from veupath_chatbot.domain.parameters.vocab_utils import flatten_vocab
from veupath_chatbot.integrations.veupathdb.client import VEuPathDBClient
from veupath_chatbot.integrations.veupathdb.discovery import get_discovery_service
from veupath_chatbot.integrations.veupathdb.factory import get_wdk_client
from veupath_chatbot.integrations.veupathdb.param_utils import (
    normalize_param_value,
    wdk_entity_name,
    wdk_search_matches,
)
from veupath_chatbot.platform.errors import ErrorCode, WDKError
from veupath_chatbot.platform.errors import ValidationError as CoreValidationError
from veupath_chatbot.platform.tool_errors import tool_error
from veupath_chatbot.platform.types import JSONArray, JSONObject, JSONValue

from .searches import _resolve_record_type_for_search


async def get_search_parameters(
    site_id: str,
    record_type: str,
    search_name: str,
) -> JSONObject:
    """Get detailed parameter info for a specific search.

    This is intentionally defensive: WDK responses can vary by site/endpoint.
    """
    discovery = get_discovery_service()
    details: JSONObject | None = None
    resolved_record_type = record_type

    record_types = await discovery.get_record_types(site_id)

    def normalize(value: str) -> str:
        return value.strip().lower()

    if record_type:
        normalized = normalize(record_type)
        exact: list[JSONObject] = []
        for rt in record_types:
            if not isinstance(rt, dict):
                continue
            if normalize(wdk_entity_name(rt)) == normalized:
                exact.append(rt)
        if exact:
            new_rt = wdk_entity_name(exact[0])
            if new_rt:
                resolved_record_type = new_rt
        else:
            display_matches: list[JSONObject] = []
            for rt in record_types:
                if not isinstance(rt, dict):
                    continue
                display_name_raw = rt.get("displayName")
                display_name = (
                    display_name_raw if isinstance(display_name_raw, str) else ""
                )
                if normalize(display_name) == normalized:
                    display_matches.append(rt)
            if len(display_matches) == 1:
                new_rt = wdk_entity_name(display_matches[0])
                if new_rt:
                    resolved_record_type = new_rt

    try:
        details = await discovery.get_search_details(
            site_id, resolved_record_type, search_name, expand_params=True
        )
    except Exception as e:
        for rt in record_types:
            if not isinstance(rt, dict):
                continue
            rt_name = wdk_entity_name(rt)
            if not rt_name:
                continue
            searches = await discovery.get_searches(site_id, rt_name)
            if any(wdk_search_matches(s, search_name) for s in searches):
                resolved_record_type = rt_name
                try:
                    details = await discovery.get_search_details(
                        site_id, rt_name, search_name, expand_params=True
                    )
                except Exception:
                    details = None
                break

        if details is None:
            available = await discovery.get_searches(site_id, resolved_record_type)
            available_searches: list[str] = [
                wdk_entity_name(s)
                for s in available
                if isinstance(s, dict) and wdk_entity_name(s)
            ]

            error_dict: JSONObject = {
                "path": "searchName",
                "message": f"Search not found: {search_name}",
                "code": ErrorCode.SEARCH_NOT_FOUND.value,
                "recordType": resolved_record_type,
                "searchName": search_name,
                "availableSearches": cast(JSONValue, available_searches),
                "details": str(e),
            }
            raise CoreValidationError(
                title="Search not found",
                detail=f"Search not found: {search_name}",
                errors=[error_dict],
            ) from e

    details = _unwrap_search_data(details) or details
    param_specs = extract_param_specs(details if isinstance(details, dict) else {})

    def _allowed_values(vocab: JSONObject | JSONArray | None) -> list[str]:
        """Extract WDK-accepted parameter values from a vocabulary.

        Uses term/value (what WDK actually accepts) rather than display labels,
        so the LLM can pass these values directly to WDK API calls without
        needing vocabulary normalisation.

        :param vocab: Vocabulary tree or flat list from catalog.
        :returns: List of WDK-accepted values.
        """
        if not vocab:
            return []
        values: list[str] = []
        seen: set[str] = set()
        for entry in flatten_vocab(vocab, prefer_term=True):
            # Prefer the WDK-accepted value; fall back to display if missing.
            candidate = entry.get("value") or entry.get("display")
            if not candidate:
                continue
            text = str(candidate)
            if text in seen:
                continue
            seen.add(text)
            values.append(text)
            if len(values) >= 50:
                break
        return values

    param_info: JSONArray = []
    for spec in param_specs:
        if not isinstance(spec, dict):
            continue
        # WDK parameter specs use JsonKeys.NAME = "name".
        name_raw = spec.get("name")
        name = name_raw if isinstance(name_raw, str) else ""
        if not name:
            continue
        is_required_raw = spec.get("isRequired")
        if isinstance(is_required_raw, bool):
            required = is_required_raw
        else:
            allow_empty_raw = spec.get("allowEmptyValue")
            required = not bool(allow_empty_raw)
        display_name_raw = spec.get("displayName")
        display_name = display_name_raw if isinstance(display_name_raw, str) else name
        type_raw = spec.get("type")
        param_type = type_raw if isinstance(type_raw, str) else "string"
        help_raw = spec.get("help")
        help_text = help_raw if isinstance(help_raw, str) else ""
        is_visible_raw = spec.get("isVisible")
        is_visible = is_visible_raw if isinstance(is_visible_raw, bool) else True
        info: JSONObject = {
            "name": name,
            "displayName": display_name,
            "type": param_type,
            "required": required,
            "isVisible": is_visible,
            "help": help_text,
        }

        vocabulary_raw = spec.get("vocabulary")
        vocabulary = (
            vocabulary_raw if isinstance(vocabulary_raw, (dict, list)) else None
        )
        allowed = _allowed_values(vocabulary)
        if allowed:
            info["allowedValues"] = cast(JSONValue, allowed)

        initial_display_raw = spec.get("initialDisplayValue")
        if initial_display_raw is not None:
            info["defaultValue"] = initial_display_raw
        default_value_raw = spec.get("defaultValue")
        if default_value_raw is not None and "defaultValue" not in info:
            info["defaultValue"] = default_value_raw

        param_info.append(info)

    details_display_name = search_name
    details_description = ""
    if isinstance(details, dict):
        display_name_raw = details.get("displayName")
        if isinstance(display_name_raw, str):
            details_display_name = display_name_raw
        description_raw = details.get("description")
        if isinstance(description_raw, str):
            details_description = description_raw

    return {
        "searchName": search_name,
        "displayName": details_display_name,
        "description": details_description,
        "parameters": param_info,
        "resolvedRecordType": resolved_record_type,
    }


async def get_search_parameters_tool(
    site_id: str,
    record_type: str,
    search_name: str,
) -> JSONObject:
    """Tool-friendly wrapper that returns standardized tool_error payloads."""
    try:
        return await get_search_parameters(site_id, record_type, search_name)
    except CoreValidationError as exc:
        code = None
        if exc.errors and isinstance(exc.errors, list) and exc.errors:
            first_error = exc.errors[0]
            if isinstance(first_error, dict):
                code_raw = first_error.get("code")
                if isinstance(code_raw, str):
                    code = code_raw
        return tool_error(
            code or ErrorCode.VALIDATION_ERROR,
            exc.detail or exc.title,
            errors=exc.errors,
        )


async def expand_search_details_with_params(
    site_id: str,
    record_type: str,
    search_name: str,
    context_values: JSONObject | None,
) -> JSONObject:
    """Return WDK search details after applying (WDK-wire) context values.

    NOTE: despite the historical name, this is *not* a pure validation API; it returns
    WDK search details payload. Keep it separate from the public validation endpoint.
    """
    client = get_wdk_client(site_id)
    raw_context = context_values or {}
    normalized_context: JSONObject = {}
    details: JSONObject | None = None
    allowed: set[str] = set()
    details, allowed = await _load_discovery_details_and_allowed(
        site_id=site_id,
        record_type=record_type,
        search_name=search_name,
    )
    filtered_context = _filter_context_values(raw_context, allowed)

    details_unwrapped = _unwrap_search_data(details)
    specs = adapt_param_specs(details_unwrapped) if details_unwrapped else {}

    if specs:
        normalizer = ParameterNormalizer(specs)
        try:
            normalized_context = normalizer.normalize(filtered_context)
        except CoreValidationError:
            try:
                resolved_record_type = await _resolve_record_type_for_search(
                    client, record_type, search_name
                )
                details = await client.get_search_details_with_params(
                    resolved_record_type,
                    search_name,
                    filtered_context,
                    expand_params=True,
                )
            except Exception:
                raise
            details = _unwrap_search_data(details) or details
            specs = adapt_param_specs(details if isinstance(details, dict) else {})
            normalizer = ParameterNormalizer(specs)
            normalized_context = normalizer.normalize(filtered_context)
        input_step_param = find_input_step_param(specs)
        if input_step_param:
            normalized_context[input_step_param] = ""
    else:
        normalized_context = {
            key: normalize_param_value(value) for key, value in filtered_context.items()
        }
    resolved_record_type = await _resolve_record_type_for_search(
        client, record_type, search_name
    )
    return await _get_search_details_with_portal_fallback(
        site_id=site_id,
        client=client,
        record_type=resolved_record_type,
        search_name=search_name,
        context_values=normalized_context,
    )


def _filter_context_values(raw_context: JSONObject, allowed: set[str]) -> JSONObject:
    """Filter context values to keys WDK recognizes for the search (best-effort).

    :param raw_context: Raw context from request.
    :param allowed: Set of allowed parameter names.
    :returns: Filtered context dict.
    """
    return (
        {key: value for key, value in raw_context.items() if key in allowed}
        if allowed
        else dict(raw_context)
    )


def _unwrap_search_data(details: JSONObject | None) -> JSONObject | None:
    """Normalize WDK/discovery payload shape to the dict that contains parameters.

    :param details: Search details from WDK/discovery.
    :returns: Search data dict or None.
    """
    if not isinstance(details, dict):
        return None
    search_data_raw = details.get("searchData")
    if isinstance(search_data_raw, dict):
        return search_data_raw
    return details


async def _load_discovery_details_and_allowed(
    *, site_id: str, record_type: str, search_name: str
) -> tuple[JSONObject | None, set[str]]:
    """Load discovery search details + extract allowed param names (best-effort)."""
    try:
        discovery = get_discovery_service()
        details = await discovery.get_search_details(
            site_id, record_type, search_name, expand_params=True
        )
        return (
            details,
            _extract_param_names(details if isinstance(details, dict) else {}),
        )
    except Exception:
        return None, set()


async def _get_search_details_with_portal_fallback(
    *,
    site_id: str,
    client: VEuPathDBClient,
    record_type: str,
    search_name: str,
    context_values: JSONObject,
) -> JSONObject:
    """Call WDK contextual search details, falling back to portal when appropriate."""
    try:
        return await client.get_search_details_with_params(
            record_type,
            search_name,
            context_values,
        )
    except WDKError:
        if site_id != "veupathdb":
            portal_client = get_wdk_client("veupathdb")
            return await portal_client.get_search_details_with_params(
                record_type,
                search_name,
                context_values,
            )
        raise


def _extract_param_names(details: JSONObject) -> set[str]:
    """Extract parameter names from WDK search details.

    :param details: Search details from WDK.
    :returns: Set of parameter names.
    """
    if not isinstance(details, dict):
        return set()
    search_data = details.get("searchData")
    if isinstance(search_data, dict):
        params = search_data.get("parameters")
        if isinstance(params, list):
            result: set[str] = set()
            for p in params:
                if not isinstance(p, dict):
                    continue
                name_raw = p.get("name")
                if isinstance(name_raw, str):
                    result.add(name_raw)
            return result
    params = details.get("parameters")
    if isinstance(params, dict):
        return {k for k in params if k}
    if isinstance(params, list):
        result2: set[str] = set()
        for p in params:
            if not isinstance(p, dict):
                continue
            name_raw = p.get("name")
            if isinstance(name_raw, str):
                result2.add(name_raw)
        return result2
    return set()

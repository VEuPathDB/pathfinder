import time
from typing import Any, cast

from veupath_chatbot.domain.parameters.specs import (
    extract_param_specs,
    unwrap_search_data,
)
from veupath_chatbot.domain.parameters.vocab_utils import flatten_vocab
from veupath_chatbot.integrations.vectorstore.qdrant_store import (
    point_uuid,
    sha256_hex,
    stable_json_dumps,
)
from veupath_chatbot.integrations.veupathdb.param_utils import wdk_entity_name
from veupath_chatbot.platform.types import JSONArray, JSONObject, JSONValue


def _coerce_str(value: object | None) -> str:
    return str(value) if value is not None else ""


def _preview_vocab(vocab: JSONValue, *, limit: int = 50) -> tuple[list[str], bool]:
    if not vocab:
        return [], False
    values: list[str] = []
    seen: set[str] = set()
    truncated = False
    vocab_input: JSONObject | JSONArray
    if isinstance(vocab, (dict, list)):
        vocab_input = vocab
    else:
        return [], False
    for entry in flatten_vocab(vocab_input, prefer_term=False):
        if len(values) >= limit:
            truncated = True
            break
        candidate = entry.get("display") or entry.get("value")
        if not candidate:
            continue
        s = str(candidate)
        if s in seen:
            continue
        seen.add(s)
        values.append(s)
    return values, truncated


def build_record_type_doc(site_id: str, rt: JSONValue) -> JSONObject | None:
    if isinstance(rt, str):
        rt_name = rt
        rt_display = rt
        rt_desc = ""
    elif isinstance(rt, dict):
        rt_name = wdk_entity_name(rt)
        rt_display = str(rt.get("displayName") or rt_name)
        rt_desc = str(rt.get("description") or "")
    else:
        return None

    if not rt_name:
        return None

    return {
        "id": point_uuid(f"{site_id}:{rt_name}"),
        "text": f"{rt_display}\n{rt_name}\n{rt_desc}".strip(),
        "payload": {
            "siteId": site_id,
            "recordType": rt_name,
            "displayName": rt_display,
            "description": rt_desc,
            "displayNamePlural": rt.get("displayNamePlural")
            if isinstance(rt, dict)
            else None,
            "shortDisplayName": rt.get("shortDisplayName")
            if isinstance(rt, dict)
            else None,
            "shortDisplayNamePlural": rt.get("shortDisplayNamePlural")
            if isinstance(rt, dict)
            else None,
            "fullName": rt.get("fullName") if isinstance(rt, dict) else None,
            "urlSegment": rt.get("urlSegment") if isinstance(rt, dict) else rt_name,
            "name": rt.get("name") if isinstance(rt, dict) else rt_name,
            "iconName": rt.get("iconName") if isinstance(rt, dict) else None,
            "recordIdAttributeName": rt.get("recordIdAttributeName")
            if isinstance(rt, dict)
            else None,
            "primaryKeyColumnRefs": rt.get("primaryKeyColumnRefs")
            if isinstance(rt, dict)
            else None,
            "useBasket": rt.get("useBasket") if isinstance(rt, dict) else None,
            "formats": rt.get("formats") if isinstance(rt, dict) else None,
            "attributes": rt.get("attributes") if isinstance(rt, dict) else None,
            "tables": rt.get("tables") if isinstance(rt, dict) else None,
            "source": "wdk",
        },
    }


def _extract_canonical_params(raw_specs: JSONArray) -> JSONArray:
    """Extract canonical parameter dicts from raw WDK param specs.

    Each output dict contains: name, displayName, type, help, isRequired,
    allowEmptyValue, defaultValue, vocabulary, vocabularyPreview, vocabularyTruncated.
    """
    canonical_params: JSONArray = []
    for spec in raw_specs:
        if not isinstance(spec, dict):
            continue
        name = spec.get("name") or spec.get("paramName") or spec.get("id")
        if not name:
            continue
        vocab = spec.get("vocabulary")
        vocab_preview, vocab_truncated = _preview_vocab(vocab, limit=50)
        canonical_params.append(
            {
                "name": str(name),
                "displayName": spec.get("displayName") or str(name),
                "type": spec.get("type") or "string",
                "help": spec.get("help") or "",
                "isRequired": bool(spec.get("isRequired", False))
                if "isRequired" in spec
                else (not bool(spec.get("allowEmptyValue", False))),
                "allowEmptyValue": bool(spec.get("allowEmptyValue", True))
                if "allowEmptyValue" in spec
                else None,
                "defaultValue": spec.get("defaultValue")
                if spec.get("defaultValue") is not None
                else spec.get("initialDisplayValue"),
                "vocabulary": vocab,
                "vocabularyPreview": cast(Any, vocab_preview),
                "vocabularyTruncated": vocab_truncated,
            }
        )
    return canonical_params


def _resolve_display_fields(
    details_unwrapped: JSONObject,
    summary_unwrapped: JSONObject,
    search_name: str,
) -> tuple[str, str, str, str, str]:
    """Resolve display_name, short, description, summary, help from details/summary.

    Falls back through details -> summary -> search_name for display_name.
    Returns (display_name, short, description, summary, help_text).
    """
    display_name = _coerce_str(
        details_unwrapped.get("displayName")
        or summary_unwrapped.get("displayName")
        or summary_unwrapped.get("shortDisplayName")
        or search_name
    )
    short = _coerce_str(
        details_unwrapped.get("shortDisplayName")
        or summary_unwrapped.get("shortDisplayName")
        or ""
    )
    description = _coerce_str(
        details_unwrapped.get("description")
        or summary_unwrapped.get("description")
        or ""
    )
    summary = _coerce_str(details_unwrapped.get("summary") or "")
    help_text = _coerce_str(details_unwrapped.get("help") or "")
    return display_name, short, description, summary, help_text


def _assemble_search_payload(
    *,
    site_id: str,
    rt_name: str,
    search_name: str,
    display_name: str,
    short: str,
    description: str,
    summary: str,
    help_text: str,
    canonical_params: JSONArray,
    details_unwrapped: JSONObject,
    summary_unwrapped: JSONObject,
    base_url: str,
    is_internal: bool,
    details_error: str | None,
) -> JSONObject:
    """Assemble the search payload dict with source hash."""
    payload: JSONObject = {
        "siteId": site_id,
        "recordType": rt_name,
        "searchName": search_name,
        "displayName": display_name,
        "shortDisplayName": short,
        "description": description,
        "summary": summary,
        "help": help_text,
        "isInternal": is_internal,
        "paramSpecs": canonical_params,
        "fullName": details_unwrapped.get("fullName")
        or summary_unwrapped.get("fullName"),
        "urlSegment": details_unwrapped.get("urlSegment")
        or summary_unwrapped.get("urlSegment")
        or search_name,
        "outputRecordClassName": details_unwrapped.get("outputRecordClassName")
        or rt_name,
        "paramNames": details_unwrapped.get("paramNames")
        or summary_unwrapped.get("paramNames"),
        "groups": details_unwrapped.get("groups") or summary_unwrapped.get("groups"),
        "filters": details_unwrapped.get("filters") or summary_unwrapped.get("filters"),
        "defaultAttributes": details_unwrapped.get("defaultAttributes")
        or summary_unwrapped.get("defaultAttributes"),
        "defaultSorting": details_unwrapped.get("defaultSorting")
        or summary_unwrapped.get("defaultSorting"),
        "dynamicAttributes": details_unwrapped.get("dynamicAttributes")
        or summary_unwrapped.get("dynamicAttributes"),
        "defaultSummaryView": details_unwrapped.get("defaultSummaryView")
        or summary_unwrapped.get("defaultSummaryView"),
        "noSummaryOnSingleRecord": details_unwrapped.get("noSummaryOnSingleRecord")
        or summary_unwrapped.get("noSummaryOnSingleRecord"),
        "summaryViewPlugins": details_unwrapped.get("summaryViewPlugins")
        or summary_unwrapped.get("summaryViewPlugins"),
        "allowedPrimaryInputRecordClassNames": details_unwrapped.get(
            "allowedPrimaryInputRecordClassNames"
        ),
        "allowedSecondaryInputRecordClassNames": details_unwrapped.get(
            "allowedSecondaryInputRecordClassNames"
        ),
        "isAnalyzable": details_unwrapped.get("isAnalyzable")
        or summary_unwrapped.get("isAnalyzable"),
        "isCacheable": details_unwrapped.get("isCacheable")
        or summary_unwrapped.get("isCacheable"),
        "isBeta": details_unwrapped.get("isBeta"),
        "queryName": details_unwrapped.get("queryName")
        or summary_unwrapped.get("queryName"),
        "newBuild": details_unwrapped.get("newBuild"),
        "reviseBuild": details_unwrapped.get("reviseBuild"),
        "searchVisibleHelp": details_unwrapped.get("searchVisibleHelp"),
        "sourceUrl": f"{base_url}/record-types/{rt_name}/searches/{search_name}",
        "ingestedAt": int(time.time()),
    }
    if details_error:
        payload["detailsError"] = details_error
    payload["sourceHash"] = sha256_hex(stable_json_dumps(payload))
    return payload


def _build_search_text(
    display_name: str,
    search_name: str,
    rt_name: str,
    summary: str,
    description: str,
    canonical_params: JSONArray,
) -> str:
    """Build the searchable text blob from display fields and params."""
    return "\n".join(
        [
            display_name,
            search_name,
            rt_name,
            summary,
            description,
            " ".join(
                (
                    f"{p.get('name', '')} {p.get('displayName', '')} "
                    f"{p.get('type', '')} {p.get('help', '')}"
                )
                for p in canonical_params
                if isinstance(p, dict)
            ),
        ]
    ).strip()


def build_search_doc(
    site_id: str,
    rt_name: str,
    s: JSONObject,
    details_unwrapped: JSONObject,
    details_error: str | None,
    base_url: str,
) -> JSONObject | None:
    if not isinstance(s, dict):
        return None
    if s.get("isInternal", False):
        return None
    search_name = wdk_entity_name(s)
    if not search_name:
        return None

    summary_unwrapped = unwrap_search_data(s if isinstance(s, dict) else {}) or {}

    raw_specs = extract_param_specs(details_unwrapped) if details_unwrapped else []
    canonical_params = _extract_canonical_params(raw_specs)

    display_name, short, description, summary, help_text = _resolve_display_fields(
        details_unwrapped, summary_unwrapped, search_name
    )

    payload = _assemble_search_payload(
        site_id=site_id,
        rt_name=rt_name,
        search_name=search_name,
        display_name=display_name,
        short=short,
        description=description,
        summary=summary,
        help_text=help_text,
        canonical_params=canonical_params,
        details_unwrapped=details_unwrapped,
        summary_unwrapped=summary_unwrapped,
        base_url=base_url,
        is_internal=bool(s.get("isInternal", False)),
        details_error=details_error,
    )

    text = _build_search_text(
        display_name, search_name, rt_name, summary, description, canonical_params
    )

    return {
        "id": point_uuid(f"{site_id}:{rt_name}:{search_name}"),
        "text": text,
        "payload": payload,
    }

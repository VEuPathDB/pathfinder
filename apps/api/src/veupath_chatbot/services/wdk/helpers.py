"""Shared WDK helpers for record parsing, attribute inspection, and param merging.

These functions are used by experiment results, gene set, and workbench
endpoints to work with WDK record types, primary keys, and analysis
parameters. Previously duplicated across multiple router modules.
"""

from __future__ import annotations

from veupath_chatbot.platform.types import JSONObject, JSONValue

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SORTABLE_WDK_TYPES = {"number", "float", "integer", "double"}

_SCORE_ATTRIBUTE_KEYWORDS = {
    "score",
    "e_value",
    "evalue",
    "bit_score",
    "bitscore",
    "p_value",
    "pvalue",
    "fold_change",
    "log_fc",
    "confidence",
}


# ---------------------------------------------------------------------------
# Attribute classification
# ---------------------------------------------------------------------------


def is_sortable(attr_type: str | None) -> bool:
    """Return ``True`` if a WDK attribute type supports numeric sorting."""
    if not attr_type:
        return False
    return attr_type.lower() in _SORTABLE_WDK_TYPES


def is_suggested_score(name: str) -> bool:
    """Heuristic: flag well-known score attributes as suggested for ranking."""
    lower = name.lower()
    return any(kw in lower for kw in _SCORE_ATTRIBUTE_KEYWORDS)


# ---------------------------------------------------------------------------
# Primary key extraction
# ---------------------------------------------------------------------------


def extract_pk(record: JSONObject) -> str | None:
    """Extract primary key string from a WDK record.

    WDK records use ``"id": [{name, value}, ...]`` for the composite
    primary key.  Returns the first part's value, stripped.
    """
    pk = record.get("id")
    if isinstance(pk, list) and pk:
        first = pk[0]
        if isinstance(first, dict):
            val = first.get("value")
            if isinstance(val, str):
                return val.strip()
    return None


def extract_record_ids(records: list[object]) -> list[str]:
    """Extract gene/record IDs from WDK standard report records.

    Iterates over records and extracts the first primary key value
    from each.  Skips non-dict entries, missing ``id`` arrays, and
    non-string values.
    """
    ids: list[str] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        pk = rec.get("id")
        if isinstance(pk, list) and pk:
            first = pk[0]
            if isinstance(first, dict):
                val = first.get("value")
                if isinstance(val, str) and val.strip():
                    ids.append(val.strip())
    return ids


# ---------------------------------------------------------------------------
# Attribute name extraction
# ---------------------------------------------------------------------------


def extract_displayable_attr_names(attrs_raw: object) -> list[str]:
    """Extract displayable attribute names from WDK record type info.

    WDK record type info can return attributes in two formats:

    * **dict** (``attributesMap``): ``{name: {isDisplayable, ...}, ...}``
    * **list** (expanded): ``[{name, isDisplayable, ...}, ...]``

    Empty or missing attribute names are filtered out because WDK's
    ``RecordRequest.parseAttributeNames`` rejects names not in the
    record class attribute field map.

    :param attrs_raw: Raw attributes value from the record type info.
    :returns: List of valid displayable attribute names.
    """
    attr_names: list[str] = []
    if isinstance(attrs_raw, dict):
        for name, meta in attrs_raw.items():
            if not name or not isinstance(name, str):
                continue
            if isinstance(meta, dict) and meta.get("isDisplayable", True):
                attr_names.append(str(name))
    elif isinstance(attrs_raw, list):
        for meta in attrs_raw:
            if not isinstance(meta, dict):
                continue
            if not meta.get("isDisplayable", True):
                continue
            raw_name = meta.get("name")
            if raw_name is None:
                continue
            name = str(raw_name).strip()
            if name:
                attr_names.append(name)
    return attr_names


# ---------------------------------------------------------------------------
# Primary key ordering
# ---------------------------------------------------------------------------


def order_primary_key(
    pk_parts: list[JSONObject],
    pk_refs: list[str],
    pk_defaults: dict[str, str],
) -> list[JSONObject]:
    """Reorder and fill primary key parts to match WDK record class definition.

    WDK requires PK columns in the exact order defined by
    ``primaryKeyColumnRefs``.  Step reports may omit columns like
    ``project_id`` and may return them in a different order.

    :param pk_parts: Client-provided PK parts (``[{name, value}, ...]``).
    :param pk_refs: Column names in record-class order.
    :param pk_defaults: Default values for missing columns (e.g. ``project_id``).
    :returns: Ordered PK parts matching ``pk_refs``.
    """
    pk_by_name: dict[str, str] = {
        str(p.get("name", "")): str(p.get("value", ""))
        for p in pk_parts
        if isinstance(p, dict)
    }
    ordered: list[JSONObject] = []
    for col in pk_refs:
        if not isinstance(col, str):
            continue
        value = pk_by_name.get(col) or pk_defaults.get(col) or ""
        ordered.append({"name": col, "value": value})
    return ordered


# ---------------------------------------------------------------------------
# Attribute list building
# ---------------------------------------------------------------------------


def build_attribute_list(attrs_raw: object) -> list[JSONObject]:
    """Build a normalized attribute list from WDK record type info.

    Handles both dict (``attributesMap``) and list (expanded) formats.
    Each entry includes: ``name``, ``displayName``, ``help``, ``type``,
    ``isDisplayable``, ``isSortable``, ``isSuggested``.

    This consolidates the 40+ line if/elif blocks previously copy-pasted
    in both ``get_experiment_attributes`` and ``get_gene_set_attributes``.

    :param attrs_raw: Raw attributes value from the record type info.
    :returns: Normalized attribute list.
    """
    attributes: list[JSONObject] = []

    if isinstance(attrs_raw, dict):
        for name, meta in attrs_raw.items():
            if isinstance(meta, dict):
                attr = _build_single_attribute(str(name), meta, name_fallback=str(name))
                attributes.append(attr)
    elif isinstance(attrs_raw, list):
        for meta in attrs_raw:
            if isinstance(meta, dict):
                attr_name = str(meta.get("name", ""))
                attr = _build_single_attribute(attr_name, meta, name_fallback=attr_name)
                attributes.append(attr)

    return attributes


def _build_single_attribute(
    name: str,
    meta: dict[str, object],
    *,
    name_fallback: str,
) -> JSONObject:
    """Build a single normalized attribute dict from WDK metadata."""
    raw_type = meta.get("type")
    attr_type = str(raw_type) if isinstance(raw_type, str) else None
    sortable = is_sortable(attr_type)
    return {
        "name": name,
        "displayName": meta.get("displayName", name_fallback),
        "help": meta.get("help"),
        "type": attr_type,
        "isDisplayable": meta.get("isDisplayable", True),
        "isSortable": sortable,
        "isSuggested": sortable and is_suggested_score(name),
    }


# ---------------------------------------------------------------------------
# Analysis parameter merging
# ---------------------------------------------------------------------------


def merge_analysis_params(
    form_meta: JSONValue,
    user_params: dict[str, object],
) -> JSONObject:
    """Merge WDK form defaults with user-supplied parameters.

    Always extracts defaults from the WDK form metadata and layers
    user-supplied parameters on top so that required fields are never
    missing (which would cause WDK 422 errors).

    After merging, vocabulary params (``single-pick-vocabulary``,
    ``multi-pick-vocabulary``) are re-encoded as JSON arrays using
    the form metadata.  This ensures that user-supplied plain strings
    don't bypass the encoding required by
    ``AbstractEnumParam.convertToTerms()``.
    """
    from veupath_chatbot.services.experiment.enrichment import (
        _extract_default_params,
        encode_vocab_params,
    )

    defaults = _extract_default_params(form_meta)
    merged: JSONObject = {**defaults, **user_params}
    return encode_vocab_params(merged, form_meta)

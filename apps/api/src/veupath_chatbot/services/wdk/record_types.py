"""Shared record-type resolution utility.

Normalizes a user-supplied record type string and matches it against
the available WDK record type objects.  Three matching strategies are
tried in order:

1. **Exact** (case-insensitive) match on canonical name
   (``urlSegment`` then ``name`` via :func:`wdk_entity_name`).
2. **Exact** (case-insensitive) match on the ``name`` field of dict entries.
3. **Display name** match — only accepted when exactly one record type
   has a matching ``displayName`` to avoid ambiguity.

If none of the strategies succeed the function returns ``None``.
"""

from veupath_chatbot.integrations.veupathdb.param_utils import wdk_entity_name
from veupath_chatbot.platform.types import JSONValue


def resolve_record_type(
    available_types: list[JSONValue],
    user_input: str,
) -> str | None:
    """Match *user_input* against WDK record-type objects.

    :param available_types: Raw record type list from WDK (may contain
        plain strings or dicts with ``urlSegment``/``name``/``displayName``).
    :param user_input: User-supplied record type string.
    :returns: The canonical (``urlSegment`` / ``name``) string for the
        matched record type, or ``None`` if no match is found.
    """
    normalized = user_input.strip().lower()

    # --- Strategy 1: match on canonical name (urlSegment / name) ----------
    for rt in available_types:
        if not isinstance(rt, (str, dict)):
            continue
        if wdk_entity_name(rt).strip().lower() == normalized:
            return wdk_entity_name(rt) or None

    # --- Strategy 2: match on raw "name" field of dict entries ------------
    for rt in available_types:
        if not isinstance(rt, dict):
            continue
        name_raw = rt.get("name")
        name = name_raw if isinstance(name_raw, str) else ""
        if name.strip().lower() == normalized:
            return wdk_entity_name(rt) or None

    # --- Strategy 3: match on displayName (single match only) -------------
    display_matches: list[JSONValue] = []
    for rt in available_types:
        if not isinstance(rt, dict):
            continue
        display_name_raw = rt.get("displayName")
        display_name = display_name_raw if isinstance(display_name_raw, str) else ""
        if display_name.strip().lower() == normalized:
            display_matches.append(rt)

    if len(display_matches) == 1:
        return wdk_entity_name(display_matches[0]) or None

    return None

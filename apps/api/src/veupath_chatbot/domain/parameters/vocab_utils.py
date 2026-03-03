"""Vocabulary utilities."""

from __future__ import annotations

import math
import re

from veupath_chatbot.platform.errors import ValidationError
from veupath_chatbot.platform.types import JSONArray, JSONObject


def numeric_equivalent(a: str | None, b: str | None) -> bool:
    """Check if two string values represent the same number.

    Handles precision differences between WDK vocab values (often floats)
    and imported strategy parameters (often full-precision decimals).
    """
    if not a or not b:
        return False
    try:
        fa = float(str(a).strip())
        fb = float(str(b).strip())
    except Exception:
        return False
    if not (math.isfinite(fa) and math.isfinite(fb)):
        return False
    return math.isclose(fa, fb, rel_tol=1e-9, abs_tol=1e-12)


def match_vocab_value(
    *,
    vocab: JSONObject | JSONArray | None,
    param_name: str,
    value: str,
) -> str:
    """Match a user-supplied value against a vocabulary, returning the canonical form.

    Tries exact display match, exact value match, then numeric equivalence.
    Raises ``ValidationError`` if no match is found.
    """
    if not vocab:
        return value
    value_norm = value.strip() if isinstance(value, str) else str(value)

    entries = flatten_vocab(vocab, prefer_term=True)
    for entry in entries:
        display = entry.get("display")
        raw_value = entry.get("value")
        if value_norm == (display or ""):
            return raw_value or display or value
        if value_norm == (raw_value or ""):
            return raw_value or value
        if numeric_equivalent(value_norm, display):
            return raw_value or display or value
        if numeric_equivalent(value_norm, raw_value):
            return raw_value or value
    raise ValidationError(
        title="Invalid parameter value",
        detail=f"Parameter '{param_name}' does not accept '{value}'.",
        errors=[{"param": param_name, "value": value}],
    )


def normalize_vocab_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def flatten_vocab(
    vocabulary: JSONObject | JSONArray, prefer_term: bool = False
) -> list[dict[str, str | None]]:
    entries: list[dict[str, str | None]] = []

    def choose_value(data: JSONObject) -> str | None:
        term_raw = data.get("term")
        value_raw = data.get("value")
        term = term_raw if isinstance(term_raw, str) else None
        value = value_raw if isinstance(value_raw, str) else None
        if prefer_term:
            return term or value
        return value or term

    def walk(node: JSONObject) -> None:
        data_raw = node.get("data", {})
        data = data_raw if isinstance(data_raw, dict) else {}
        display_raw = data.get("display")
        display = display_raw if isinstance(display_raw, str) else None
        raw_value = choose_value(data)
        entries.append({"display": display, "value": raw_value})
        children_raw = node.get("children", [])
        children = children_raw if isinstance(children_raw, list) else []
        for child in children:
            if isinstance(child, dict):
                walk(child)

    if isinstance(vocabulary, dict) and vocabulary:
        walk(vocabulary)
    elif isinstance(vocabulary, list):
        for item in vocabulary:
            if isinstance(item, list) and item:
                if item[0] is None:
                    continue
                value = str(item[0])
                display_from_list = (
                    str(item[1]) if len(item) > 1 and item[1] is not None else value
                )
                entries.append({"display": display_from_list, "value": value})
            elif isinstance(item, dict):
                display_raw = item.get("display")
                display_from_dict = (
                    display_raw if isinstance(display_raw, str) else None
                )
                raw_value = choose_value(item)
                entries.append({"display": display_from_dict, "value": raw_value})
            else:
                entries.append({"display": str(item), "value": str(item)})
    return entries

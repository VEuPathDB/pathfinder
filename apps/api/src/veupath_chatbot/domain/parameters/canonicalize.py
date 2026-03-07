"""Canonicalize parameter values (API-friendly) using WDK parameter specs.

This module is the counterpart to ``domain/parameters/normalize``:

- ``normalize`` produces WDK wire-safe values (often strings/JSON strings).
- ``canonicalize`` produces API-friendly canonical JSON shapes:
  multi-pick values become ``list[str]``, scalars become strings,
  range values become ``{min, max}``, filter values become dict/list.

Used at API boundaries (plan normalization, validation) so the frontend
can consume stable rules without re-implementing coercion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from veupath_chatbot.domain.parameters._decode_values import decode_values
from veupath_chatbot.domain.parameters._value_helpers import ParameterValueMixin
from veupath_chatbot.domain.parameters.specs import ParamSpecNormalized
from veupath_chatbot.domain.parameters.vocab_utils import (
    collect_leaf_terms,
    find_vocab_node,
    get_node_term,
    get_vocab_children,
)
from veupath_chatbot.platform.errors import ValidationError
from veupath_chatbot.platform.types import (
    JSONArray,
    JSONObject,
    JSONValue,
)

FAKE_ALL_SENTINEL = "@@fake@@"


@dataclass(frozen=True)
class ParameterCanonicalizer(ParameterValueMixin):
    """Canonicalize parameter values using canonical parameter specs."""

    specs: dict[str, ParamSpecNormalized]

    def canonicalize(self, parameters: JSONObject) -> JSONObject:
        canonical: JSONObject = {}
        for name, value in (parameters or {}).items():
            spec = self.specs.get(name)
            if not spec:
                raise ValidationError(
                    title="Unknown parameter",
                    detail=f"Parameter '{name}' does not exist for this search.",
                    errors=[{"param": name, "value": value}],
                )
            if spec.param_type == "input-step":
                continue
            canonical[name] = self._canonicalize_value(spec, value)
        return canonical

    def _canonicalize_value(
        self, spec: ParamSpecNormalized, value: JSONValue
    ) -> JSONValue:
        if value == FAKE_ALL_SENTINEL:
            raise ValidationError(
                title="Invalid parameter value",
                detail=f"Parameter '{spec.name}' does not accept '{FAKE_ALL_SENTINEL}'.",
                errors=[{"param": spec.name, "value": value}],
            )

        param_type = spec.param_type
        if value is None:
            return self._handle_empty(spec, value)

        if param_type == "multi-pick-vocabulary":
            values = [self._stringify(v) for v in decode_values(value, spec.name)]
            if any(v == FAKE_ALL_SENTINEL for v in values):
                raise ValidationError(
                    title="Invalid parameter value",
                    detail=f"Parameter '{spec.name}' does not accept '{FAKE_ALL_SENTINEL}'.",
                    errors=[{"param": spec.name, "value": value}],
                )
            values = [self._match_vocab_value(spec, v) for v in values]
            values = self._enforce_leaf_values(spec, values)
            self._validate_multi_count(spec, values)
            return cast(JSONValue, values)

        if param_type == "single-pick-vocabulary":
            decoded = decode_values(value, spec.name)
            if len(decoded) > 1:
                raise ValidationError(
                    title="Invalid parameter value",
                    detail=f"Parameter '{spec.name}' allows only one value.",
                    errors=[{"param": spec.name, "value": value}],
                )
            selected = self._stringify(decoded[0]) if decoded else ""
            if selected == FAKE_ALL_SENTINEL:
                raise ValidationError(
                    title="Invalid parameter value",
                    detail=f"Parameter '{spec.name}' does not accept '{FAKE_ALL_SENTINEL}'.",
                    errors=[{"param": spec.name, "value": value}],
                )
            if not selected:
                self._validate_single_required(spec)
                return ""
            selected = self._match_vocab_value(spec, selected)
            selected = self._enforce_leaf_value(spec, selected)
            if not selected:
                self._validate_single_required(spec)
            return self._stringify(selected)

        if param_type in {"number", "date", "timestamp", "string"}:
            if isinstance(value, (list, dict, tuple, set)):
                raise ValidationError(
                    title="Invalid parameter value",
                    detail=f"Parameter '{spec.name}' must be a scalar value.",
                    errors=[{"param": spec.name, "value": value}],
                )
            return self._stringify(value)

        if param_type in {"number-range", "date-range"}:
            if isinstance(value, dict):
                return value
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return {"min": value[0], "max": value[1]}
            raise ValidationError(
                title="Invalid parameter value",
                detail=f"Parameter '{spec.name}' must be a range.",
                errors=[{"param": spec.name, "value": value}],
            )

        if param_type == "filter":
            if isinstance(value, (dict, list)):
                return value
            return self._stringify(value)

        if param_type in {"input-dataset"}:
            if isinstance(value, list):
                if len(value) != 1:
                    raise ValidationError(
                        title="Invalid parameter value",
                        detail=f"Parameter '{spec.name}' must be a single value.",
                        errors=[{"param": spec.name, "value": value}],
                    )
                return self._stringify(value[0])
            return self._stringify(value)

        # Unknown param type: preserve value as-is (best-effort).
        return value

    def _enforce_leaf_values(
        self, spec: ParamSpecNormalized, values: list[str]
    ) -> list[str]:
        if not spec.count_only_leaves:
            return values
        enforced: list[str] = []
        seen: set[str] = set()
        for value in values:
            leaves = self._expand_leaf_terms_for_match(spec.vocabulary, value)
            if not leaves:
                raise ValidationError(
                    title="Invalid parameter value",
                    detail=f"Parameter '{spec.name}' requires leaf selections.",
                    errors=[{"param": spec.name, "value": value}],
                )
            for leaf in leaves:
                if leaf in seen:
                    continue
                seen.add(leaf)
                enforced.append(leaf)
        return enforced

    def _enforce_leaf_value(self, spec: ParamSpecNormalized, value: str) -> str:
        if not spec.count_only_leaves or not value:
            return value
        leaf = self._find_leaf_term_for_match(spec.vocabulary, value)
        if not leaf:
            raise ValidationError(
                title="Invalid parameter value",
                detail=f"Parameter '{spec.name}' requires leaf selections.",
                errors=[{"param": spec.name, "value": value}],
            )
        return leaf

    def _expand_leaf_terms_for_match(
        self, vocabulary: JSONObject | JSONArray | None, match: str
    ) -> list[str]:
        if not isinstance(vocabulary, dict) or not match:
            return []
        matched_node = find_vocab_node(vocabulary, match)
        if not matched_node:
            return []
        return collect_leaf_terms(matched_node)

    def _find_leaf_term_for_match(
        self, vocabulary: JSONObject | JSONArray | None, match: str
    ) -> str | None:
        if not isinstance(vocabulary, dict) or not match:
            return None
        matched_node = find_vocab_node(vocabulary, match)
        if not matched_node:
            return None
        if get_vocab_children(matched_node):
            return None
        return get_node_term(matched_node)

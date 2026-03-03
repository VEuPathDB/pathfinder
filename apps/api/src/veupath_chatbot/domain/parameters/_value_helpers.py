"""Shared validation and coercion helpers for parameter processing.

Used by both ``ParameterNormalizer`` (wire-safe WDK values) and
``ParameterCanonicalizer`` (API-friendly canonical shapes).
"""

from __future__ import annotations

from veupath_chatbot.domain.parameters.specs import ParamSpecNormalized
from veupath_chatbot.domain.parameters.vocab_utils import match_vocab_value
from veupath_chatbot.platform.errors import ValidationError
from veupath_chatbot.platform.types import JSONValue


class ParameterValueMixin:
    """Shared helpers for ``ParameterNormalizer`` and ``ParameterCanonicalizer``."""

    def _stringify(self, value: JSONValue) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _handle_empty(self, spec: ParamSpecNormalized, value: JSONValue) -> JSONValue:
        if spec.allow_empty_value:
            return ""
        if spec.param_type in {"multi-pick-vocabulary", "single-pick-vocabulary"}:
            self._validate_single_required(spec)
        return value

    def _validate_multi_count(
        self, spec: ParamSpecNormalized, values: list[str]
    ) -> None:
        if not values and spec.allow_empty_value:
            return
        min_count = spec.min_selected_count or 0
        max_count = spec.max_selected_count
        if len(values) < min_count:
            raise ValidationError(
                title="Invalid parameter value",
                detail=f"Parameter '{spec.name}' requires at least {min_count} value(s).",
                errors=[{"param": spec.name, "value": list(values)}],
            )
        if max_count is not None and len(values) > max_count:
            raise ValidationError(
                title="Invalid parameter value",
                detail=f"Parameter '{spec.name}' allows at most {max_count} value(s).",
                errors=[{"param": spec.name, "value": list(values)}],
            )

    def _validate_single_required(self, spec: ParamSpecNormalized) -> None:
        if spec.allow_empty_value:
            return
        min_count = spec.min_selected_count
        if min_count is not None and min_count <= 0:
            return
        raise ValidationError(
            title="Invalid parameter value",
            detail=f"Parameter '{spec.name}' requires a value.",
            errors=[{"param": spec.name}],
        )

    def _match_vocab_value(self, spec: ParamSpecNormalized, value: str) -> str:
        return match_vocab_value(
            vocab=spec.vocabulary, param_name=spec.name, value=value
        )

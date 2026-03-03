"""Normalize parameter values into WDK wire format."""

from __future__ import annotations

import json
from dataclasses import dataclass

from veupath_chatbot.domain.parameters._decode_values import decode_values
from veupath_chatbot.domain.parameters._value_helpers import ParameterValueMixin
from veupath_chatbot.domain.parameters.specs import ParamSpecNormalized
from veupath_chatbot.platform.errors import ValidationError
from veupath_chatbot.platform.types import (
    JSONObject,
    JSONValue,
)


@dataclass(frozen=True)
class ParameterNormalizer(ParameterValueMixin):
    """Normalize parameter values using canonical parameter specs."""

    specs: dict[str, ParamSpecNormalized]

    def normalize(self, parameters: JSONObject) -> JSONObject:
        normalized: JSONObject = {}
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
            normalized[name] = self._normalize_value(spec, value)
        return normalized

    def _normalize_value(
        self, spec: ParamSpecNormalized, value: JSONValue
    ) -> JSONValue:
        param_type = spec.param_type
        if value is None:
            return self._handle_empty(spec, value)

        if param_type == "multi-pick-vocabulary":
            values = [self._stringify(v) for v in decode_values(value, spec.name)]
            values = [self._match_vocab_value(spec, v) for v in values]
            # Do not expand selections to leaf terms. Even when WDK marks a vocabulary
            # as `countOnlyLeaves`, users may legitimately select higher-level nodes
            # (e.g. a genus) and WDK will interpret it appropriately.
            self._validate_multi_count(spec, values)
            return json.dumps(values)

        if param_type == "single-pick-vocabulary":
            decoded = decode_values(value, spec.name)
            if len(decoded) > 1:
                raise ValidationError(
                    title="Invalid parameter value",
                    detail=f"Parameter '{spec.name}' allows only one value.",
                    errors=[{"param": spec.name, "value": value}],
                )
            selected = self._stringify(decoded[0]) if decoded else ""
            if not selected:
                self._validate_single_required(spec)
                return ""
            selected = self._match_vocab_value(spec, selected)
            # See note above for multi-pick vocabularies: do not coerce selections
            # to leaf terms based on `countOnlyLeaves`.
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
                return json.dumps(value)
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return json.dumps({"min": value[0], "max": value[1]})
            raise ValidationError(
                title="Invalid parameter value",
                detail=f"Parameter '{spec.name}' must be a range.",
                errors=[{"param": spec.name, "value": value}],
            )

        if param_type == "filter":
            if isinstance(value, (dict, list)):
                return json.dumps(value)
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

        return value

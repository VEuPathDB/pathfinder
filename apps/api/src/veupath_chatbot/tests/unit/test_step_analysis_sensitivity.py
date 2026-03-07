"""Unit tests for step_analysis.phase_sensitivity -- pure helper functions."""

from __future__ import annotations

from veupath_chatbot.services.experiment.step_analysis.phase_sensitivity import (
    _constrain_sweep_range,
    _find_bound_partner,
    _generate_sweep_values,
    _is_lower_bound,
    _NumericParamSpec,
    _safe_float,
)

# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------


class TestSafeFloat:
    def test_none_returns_none(self) -> None:
        assert _safe_float(None) is None

    def test_int_converted(self) -> None:
        assert _safe_float(42) == 42.0

    def test_float_passthrough(self) -> None:
        assert _safe_float(3.14) == 3.14

    def test_string_numeric(self) -> None:
        assert _safe_float("1.5") == 1.5

    def test_string_integer(self) -> None:
        assert _safe_float("100") == 100.0

    def test_string_non_numeric(self) -> None:
        assert _safe_float("abc") is None

    def test_empty_string(self) -> None:
        assert _safe_float("") is None

    def test_bool_coerced(self) -> None:
        # In Python, bool is a subclass of int
        # isinstance(True, int) is True, so it hits the int/float branch
        result = _safe_float(True)
        assert result == 1.0

    def test_negative_float(self) -> None:
        assert _safe_float(-5.5) == -5.5

    def test_zero(self) -> None:
        assert _safe_float(0) == 0.0

    def test_string_negative(self) -> None:
        assert _safe_float("-3.14") == -3.14

    def test_list_returns_none(self) -> None:
        assert _safe_float([1, 2]) is None

    def test_dict_returns_none(self) -> None:
        assert _safe_float({"a": 1}) is None


# ---------------------------------------------------------------------------
# _generate_sweep_values
# ---------------------------------------------------------------------------


class TestGenerateSweepValues:
    def test_default_five_points(self) -> None:
        values = _generate_sweep_values(0.0, 1.0, 0.5)
        assert len(values) == 5
        assert values[0] == 0.0
        assert values[-1] == 1.0

    def test_includes_current_value(self) -> None:
        values = _generate_sweep_values(0.0, 1.0, 0.33)
        assert 0.33 in values

    def test_current_already_on_grid(self) -> None:
        """If current is already one of the evenly spaced values, no duplicate."""
        values = _generate_sweep_values(0.0, 1.0, 0.5)
        assert values.count(0.5) == 1

    def test_current_at_endpoints(self) -> None:
        values = _generate_sweep_values(0.0, 1.0, 0.0)
        assert values.count(0.0) == 1
        assert 0.0 in values

        values = _generate_sweep_values(0.0, 1.0, 1.0)
        assert values.count(1.0) == 1

    def test_single_point(self) -> None:
        """n=1 produces just the minimum (step=0)."""
        values = _generate_sweep_values(0.0, 1.0, 0.5, n=1)
        assert 0.0 in values
        assert 0.5 in values
        assert len(values) == 2  # min + current added

    def test_sorted_output(self) -> None:
        values = _generate_sweep_values(0.0, 10.0, 7.3, n=5)
        assert values == sorted(values)

    def test_custom_n(self) -> None:
        values = _generate_sweep_values(0.0, 100.0, 50.0, n=3)
        # Should be [0, 50, 100] -- current is already on grid
        assert 0.0 in values
        assert 50.0 in values
        assert 100.0 in values


# ---------------------------------------------------------------------------
# _is_lower_bound
# ---------------------------------------------------------------------------


class TestIsLowerBound:
    def test_lower_suffix(self) -> None:
        assert _is_lower_bound("evalue_lower") is True

    def test_min_suffix(self) -> None:
        assert _is_lower_bound("score_min") is True

    def test_min_prefix(self) -> None:
        assert _is_lower_bound("minScore") is True
        assert _is_lower_bound("MinScore") is True

    def test_upper_suffix(self) -> None:
        assert _is_lower_bound("evalue_upper") is False

    def test_max_suffix(self) -> None:
        assert _is_lower_bound("score_max") is False

    def test_max_prefix(self) -> None:
        assert _is_lower_bound("MaxScore") is False

    def test_unrelated_name(self) -> None:
        assert _is_lower_bound("evalue_threshold") is False

    def test_case_insensitive(self) -> None:
        assert _is_lower_bound("EVALUE_LOWER") is True
        assert _is_lower_bound("Score_MIN") is True


# ---------------------------------------------------------------------------
# _find_bound_partner
# ---------------------------------------------------------------------------


def _spec(name: str, current: float = 5.0) -> _NumericParamSpec:
    return {"name": name, "min": 0.0, "max": 10.0, "current": current}


class TestFindBoundPartner:
    def test_lower_upper_suffix_pair(self) -> None:
        specs = [_spec("evalue_lower"), _spec("evalue_upper")]
        partner = _find_bound_partner("evalue_lower", specs)
        assert partner is not None
        assert partner["name"] == "evalue_upper"

    def test_upper_lower_suffix_pair(self) -> None:
        specs = [_spec("evalue_lower"), _spec("evalue_upper")]
        partner = _find_bound_partner("evalue_upper", specs)
        assert partner is not None
        assert partner["name"] == "evalue_lower"

    def test_min_max_suffix_pair(self) -> None:
        specs = [_spec("score_min"), _spec("score_max")]
        partner = _find_bound_partner("score_min", specs)
        assert partner is not None
        assert partner["name"] == "score_max"

    def test_min_max_prefix_pair(self) -> None:
        specs = [_spec("MinFoo"), _spec("MaxFoo")]
        partner = _find_bound_partner("MinFoo", specs)
        assert partner is not None
        assert partner["name"] == "MaxFoo"

    def test_max_min_prefix_pair(self) -> None:
        specs = [_spec("MinFoo"), _spec("MaxFoo")]
        partner = _find_bound_partner("MaxFoo", specs)
        assert partner is not None
        assert partner["name"] == "MinFoo"

    def test_no_partner_found(self) -> None:
        specs = [_spec("evalue"), _spec("identity")]
        assert _find_bound_partner("evalue", specs) is None

    def test_case_insensitive_suffix_matching(self) -> None:
        specs = [_spec("score_lower"), _spec("Score_Upper")]
        partner = _find_bound_partner("score_lower", specs)
        assert partner is not None
        assert partner["name"] == "Score_Upper"

    def test_empty_specs(self) -> None:
        assert _find_bound_partner("evalue_lower", []) is None

    def test_prefix_requires_rest(self) -> None:
        """'min' alone (no rest after prefix) should not match."""
        specs = [_spec("min"), _spec("max")]
        partner = _find_bound_partner("min", specs)
        assert partner is None


# ---------------------------------------------------------------------------
# _constrain_sweep_range
# ---------------------------------------------------------------------------


class TestConstrainSweepRange:
    def test_no_partner_returns_original(self) -> None:
        result = _constrain_sweep_range("evalue_lower", 0.0, 10.0, None)
        assert result == (0.0, 10.0)

    def test_lower_bound_constrained_by_partner(self) -> None:
        """Lower bound's max is capped at partner's current value."""
        lo, hi = _constrain_sweep_range("evalue_lower", 0.0, 10.0, 5.0)
        assert lo == 0.0
        assert hi == 5.0

    def test_upper_bound_constrained_by_partner(self) -> None:
        """Upper bound's min is raised to partner's current value."""
        lo, hi = _constrain_sweep_range("evalue_upper", 0.0, 10.0, 3.0)
        assert lo == 3.0
        assert hi == 10.0

    def test_lower_bound_partner_below_min(self) -> None:
        """If partner_current <= min_val, effective_max = partner_current."""
        lo, hi = _constrain_sweep_range("score_lower", 5.0, 10.0, 3.0)
        # effective_max = min(10, 3) = 3, but 3 <= 5, so fallback to partner_current = 3
        assert lo == 5.0
        assert hi == 3.0

    def test_upper_bound_partner_above_max(self) -> None:
        """If partner_current >= max_val, effective_min = partner_current."""
        lo, hi = _constrain_sweep_range("score_upper", 0.0, 5.0, 8.0)
        # effective_min = max(0, 8) = 8, but 8 >= 5, so fallback to partner_current = 8
        assert lo == 8.0
        assert hi == 5.0

    def test_min_prefix_treated_as_lower_bound(self) -> None:
        lo, hi = _constrain_sweep_range("minScore", 0.0, 100.0, 50.0)
        assert lo == 0.0
        assert hi == 50.0

    def test_max_prefix_treated_as_upper_bound(self) -> None:
        lo, hi = _constrain_sweep_range("maxScore", 0.0, 100.0, 30.0)
        assert lo == 30.0
        assert hi == 100.0

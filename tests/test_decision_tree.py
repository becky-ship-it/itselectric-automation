"""Tests for the decision tree evaluator."""

import pytest  # type: ignore

from itselectric.decision_tree import evaluate  # type: ignore


class TestEvaluateLeaf:
    def test_leaf_with_template_returns_name(self):
        node = {"template": "general_car_info"}
        assert evaluate(node, {}) == "general_car_info"

    def test_leaf_with_null_template_returns_none(self):
        node = {"template": None}
        assert evaluate(node, {}) is None


class TestEvaluateConditions:
    def _branch(self, field, op, value, yes_template, no_template):
        return {
            "condition": {"field": field, "op": op, "value": value},
            "then": {"template": yes_template},
            "else": {"template": no_template},
        }

    def test_lt_true(self):
        node = self._branch("distance_miles", "lt", 0.5, "near", "far")
        assert evaluate(node, {"distance_miles": 0.3}) == "near"

    def test_lt_false(self):
        node = self._branch("distance_miles", "lt", 0.5, "near", "far")
        assert evaluate(node, {"distance_miles": 0.5}) == "far"  # equal is not lt

    def test_lte_true_at_boundary(self):
        node = self._branch("distance_miles", "lte", 100, "near", "far")
        assert evaluate(node, {"distance_miles": 100}) == "near"

    def test_gt_true(self):
        node = self._branch("distance_miles", "gt", 10, "far", "near")
        assert evaluate(node, {"distance_miles": 50}) == "far"

    def test_gte_true_at_boundary(self):
        node = self._branch("distance_miles", "gte", 50, "far", "near")
        assert evaluate(node, {"distance_miles": 50}) == "far"

    def test_eq_string(self):
        node = self._branch("driver_state", "eq", "CA", "ca_template", "other")
        assert evaluate(node, {"driver_state": "CA"}) == "ca_template"

    def test_eq_string_mismatch(self):
        node = self._branch("driver_state", "eq", "CA", "ca_template", "other")
        assert evaluate(node, {"driver_state": "TX"}) == "other"

    def test_eq_is_case_insensitive(self):
        node = self._branch("driver_state", "eq", "ca", "ca_template", "other")
        assert evaluate(node, {"driver_state": "CA"}) == "ca_template"

    def test_ne_true(self):
        node = self._branch("driver_state", "ne", "CA", "other", "ca_template")
        assert evaluate(node, {"driver_state": "TX"}) == "other"

    def test_in_true(self):
        node = self._branch("charger_city", "in", ["Los Angeles", "San Francisco"], "ca", "other")
        assert evaluate(node, {"charger_city": "Los Angeles"}) == "ca"

    def test_in_false(self):
        node = self._branch("charger_city", "in", ["Los Angeles", "San Francisco"], "ca", "other")
        assert evaluate(node, {"charger_city": "Sacramento"}) == "other"

    def test_in_is_case_insensitive(self):
        node = self._branch("charger_city", "in", ["los angeles", "san francisco"], "ca", "other")
        assert evaluate(node, {"charger_city": "Los Angeles"}) == "ca"


class TestEvaluateNested:
    """Validates the spec's full example tree."""

    _TREE = {
        "condition": {"field": "distance_miles", "op": "lt", "value": 0.5},
        "then": {"template": "general_car_info"},
        "else": {
            "condition": {"field": "distance_miles", "op": "lt", "value": 100},
            "then": {
                "condition": {"field": "driver_state", "op": "eq", "value": "CA"},
                "then": {
                    "condition": {
                        "field": "charger_city",
                        "op": "in",
                        "value": ["Los Angeles", "San Francisco"],
                    },
                    "then": {"template": "california_car_info"},
                    "else": {"template": "waitlist"},
                },
                "else": {"template": "general_car_info"},
            },
            "else": {"template": "waitlist"},
        },
    }

    def test_utah_driver_150_miles_denver(self):
        """Utah driver 150 mi from Denver → waitlist."""
        ctx = {
            "driver_state": "UT",
            "charger_state": "CO",
            "charger_city": "Denver",
            "distance_miles": 150,
        }
        assert evaluate(self._TREE, ctx) == "waitlist"

    def test_la_driver_15_miles_la_charger(self):
        """LA driver 15 mi from LA charger → california_car_info."""
        ctx = {
            "driver_state": "CA",
            "charger_state": "CA",
            "charger_city": "Los Angeles",
            "distance_miles": 15,
        }
        assert evaluate(self._TREE, ctx) == "california_car_info"

    def test_dallas_driver_99_miles_waco(self):
        """Dallas TX driver 99 mi from Waco → general_car_info."""
        ctx = {
            "driver_state": "TX",
            "charger_state": "TX",
            "charger_city": "Waco",
            "distance_miles": 99,
        }
        assert evaluate(self._TREE, ctx) == "general_car_info"


class TestEvaluateErrors:
    def test_missing_context_field_raises(self):
        """Missing context field raises KeyError — fail loudly rather than silently wrong."""
        node = {
            "condition": {"field": "distance_miles", "op": "lt", "value": 10},
            "then": {"template": "a"},
            "else": {"template": "b"},
        }
        with pytest.raises(KeyError):
            evaluate(node, {})

    def test_unknown_op_raises(self):
        """Unknown operator raises ValueError."""
        node = {
            "condition": {"field": "distance_miles", "op": "contains", "value": 5},
            "then": {"template": "a"},
            "else": {"template": "b"},
        }
        with pytest.raises(ValueError, match="Unknown operator"):
            evaluate(node, {"distance_miles": 3})

"""Tests for the decision tree evaluator."""

import pytest  # type: ignore

from itselectric.decision_tree import evaluate  # type: ignore


class TestEvaluateLeaf:
    def test_leaf_with_email_id_returns_id(self):
        node = {"email_id": 12345}
        assert evaluate(node, {}) == 12345

    def test_leaf_with_null_email_id_returns_none(self):
        node = {"email_id": None}
        assert evaluate(node, {}) is None


class TestEvaluateConditions:
    def _branch(self, field, op, value, yes_id, no_id):
        return {
            "condition": {"field": field, "op": op, "value": value},
            "then": {"email_id": yes_id},
            "else": {"email_id": no_id},
        }

    def test_lt_true(self):
        node = self._branch("distance_miles", "lt", 0.5, 111, 222)
        assert evaluate(node, {"distance_miles": 0.3}) == 111

    def test_lt_false(self):
        node = self._branch("distance_miles", "lt", 0.5, 111, 222)
        assert evaluate(node, {"distance_miles": 0.5}) == 222  # equal is not lt

    def test_lte_true_at_boundary(self):
        node = self._branch("distance_miles", "lte", 100, 111, 222)
        assert evaluate(node, {"distance_miles": 100}) == 111

    def test_gt_true(self):
        node = self._branch("distance_miles", "gt", 10, 111, 222)
        assert evaluate(node, {"distance_miles": 50}) == 111

    def test_gte_true_at_boundary(self):
        node = self._branch("distance_miles", "gte", 50, 111, 222)
        assert evaluate(node, {"distance_miles": 50}) == 111

    def test_eq_string(self):
        node = self._branch("driver_state", "eq", "CA", 111, 222)
        assert evaluate(node, {"driver_state": "CA"}) == 111

    def test_eq_string_mismatch(self):
        node = self._branch("driver_state", "eq", "CA", 111, 222)
        assert evaluate(node, {"driver_state": "TX"}) == 222

    def test_eq_is_case_insensitive(self):
        node = self._branch("driver_state", "eq", "ca", 111, 222)
        assert evaluate(node, {"driver_state": "CA"}) == 111

    def test_ne_true(self):
        node = self._branch("driver_state", "ne", "CA", 111, 222)
        assert evaluate(node, {"driver_state": "TX"}) == 111

    def test_in_true(self):
        node = self._branch("charger_city", "in", ["Los Angeles", "San Francisco"], 111, 222)
        assert evaluate(node, {"charger_city": "Los Angeles"}) == 111

    def test_in_false(self):
        node = self._branch("charger_city", "in", ["Los Angeles", "San Francisco"], 111, 222)
        assert evaluate(node, {"charger_city": "Sacramento"}) == 222

    def test_in_is_case_insensitive(self):
        node = self._branch("charger_city", "in", ["los angeles", "san francisco"], 111, 222)
        assert evaluate(node, {"charger_city": "Los Angeles"}) == 111


class TestEvaluateNested:
    """Validates the spec's full example tree."""

    _TREE = {
        "condition": {"field": "distance_miles", "op": "lt", "value": 0.5},
        "then": {"email_id": 11111},  # Get General Car Info
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
                    "then": {"email_id": 67890},  # Get California Car Info
                    "else": {"email_id": 22222},  # Waitlist
                },
                "else": {"email_id": 11111},  # Get General Car Info
            },
            "else": {"email_id": 22222},  # Waitlist
        },
    }

    def test_utah_driver_150_miles_denver(self):
        """Utah driver 150 mi from Denver → Waitlist."""
        ctx = {
            "driver_state": "UT",
            "charger_state": "CO",
            "charger_city": "Denver",
            "distance_miles": 150,
        }
        assert evaluate(self._TREE, ctx) == 22222

    def test_la_driver_15_miles_la_charger(self):
        """LA driver 15 mi from LA charger → Get California Car Info."""
        ctx = {
            "driver_state": "CA",
            "charger_state": "CA",
            "charger_city": "Los Angeles",
            "distance_miles": 15,
        }
        assert evaluate(self._TREE, ctx) == 67890

    def test_dallas_driver_99_miles_waco(self):
        """Dallas TX driver 99 mi from Waco → Get General Car Info."""
        ctx = {
            "driver_state": "TX",
            "charger_state": "TX",
            "charger_city": "Waco",
            "distance_miles": 99,
        }
        assert evaluate(self._TREE, ctx) == 11111


class TestEvaluateErrors:
    def test_missing_context_field_raises(self):
        """Missing context field raises KeyError — fail loudly rather than silently wrong."""
        node = {
            "condition": {"field": "distance_miles", "op": "lt", "value": 10},
            "then": {"email_id": 1},
            "else": {"email_id": 2},
        }
        with pytest.raises(KeyError):
            evaluate(node, {})

    def test_unknown_op_raises(self):
        """Unknown operator raises ValueError."""
        node = {
            "condition": {"field": "distance_miles", "op": "contains", "value": 5},
            "then": {"email_id": 1},
            "else": {"email_id": 2},
        }
        with pytest.raises(ValueError, match="Unknown operator"):
            evaluate(node, {"distance_miles": 3})

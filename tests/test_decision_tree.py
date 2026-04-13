"""Tests for the decision tree evaluator."""

from pathlib import Path

import pytest  # type: ignore
import yaml  # type: ignore

from itselectric.decision_tree import evaluate  # type: ignore

_TREE_PATH = Path(__file__).parent.parent / "decision_tree.example.yaml"


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


class TestRealDecisionTree:
    """Exercises every distinct terminal path in the real decision_tree.yaml."""

    @pytest.fixture(autouse=True)
    def tree(self):
        with open(_TREE_PATH) as f:
            self._tree = yaml.safe_load(f)

    def _ctx(self, *, driver, charger_state, charger_city, distance):
        return {
            "driver_state": driver,
            "charger_state": charger_state,
            "charger_city": charger_city,
            "distance_miles": distance,
        }

    # ── distance <= 0.5 ───────────────────────────────────────────────────────

    def test_at_charger_gets_general_car_info(self):
        ctx = self._ctx(driver="NY", charger_state="NY", charger_city="Brooklyn", distance=0.1)
        assert evaluate(self._tree, ctx) == "general_car_info"

    # ── distance > 100 ────────────────────────────────────────────────────────

    def test_far_away_gets_waitlist(self):
        ctx = self._ctx(driver="IL", charger_state="MI", charger_city="Detroit", distance=243)
        assert evaluate(self._tree, ctx) == "waitlist"

    # ── non-priority state, in range ─────────────────────────────────────────

    def test_non_priority_state_in_range_gets_waitlist(self):
        ctx = self._ctx(driver="NJ", charger_state="NY", charger_city="Brooklyn", distance=3.5)
        assert evaluate(self._tree, ctx) == "waitlist"

    # ── California ───────────────────────────────────────────────────────────

    def test_ca_driver_near_la_charger_gets_tell_me_more_general(self):
        ctx = self._ctx(driver="CA", charger_state="CA", charger_city="Los Angeles", distance=1.3)
        assert evaluate(self._tree, ctx) == "tell_me_more_general"

    def test_ca_driver_near_alameda_charger_gets_tell_me_more_general(self):
        ctx = self._ctx(driver="CA", charger_state="CA", charger_city="Alemeda", distance=5)
        assert evaluate(self._tree, ctx) == "tell_me_more_general"

    def test_ca_driver_far_from_la_charger_gets_waitlist(self):
        ctx = self._ctx(driver="CA", charger_state="CA", charger_city="Los Angeles", distance=15)
        assert evaluate(self._tree, ctx) == "waitlist"

    def test_ca_driver_near_sf_charger_gets_waitlist(self):
        ctx = self._ctx(driver="CA", charger_state="CA", charger_city="San Francisco", distance=1)
        assert evaluate(self._tree, ctx) == "waitlist"

    def test_priority_driver_ny_charger_non_brooklyn_city_gets_waitlist(self):
        # Tree routes by charger_state, not driver_state, once inside priority branch.
        # CA driver + NY charger in an unlisted city → falls through to waitlist.
        ctx = self._ctx(driver="CA", charger_state="NY", charger_city="New York", distance=5)
        assert evaluate(self._tree, ctx) == "waitlist"

    # ── Massachusetts ─────────────────────────────────────────────────────────

    def test_ma_driver_near_ma_charger_gets_tell_me_more_massachusetts(self):
        ctx = self._ctx(driver="MA", charger_state="MA", charger_city="Boston", distance=2)
        assert evaluate(self._tree, ctx) == "tell_me_more_massachusetts"

    def test_non_ma_driver_near_ma_charger_gets_waitlist(self):
        ctx = self._ctx(driver="CT", charger_state="MA", charger_city="Boston", distance=5)
        assert evaluate(self._tree, ctx) == "waitlist"

    # ── DC ────────────────────────────────────────────────────────────────────

    def test_dc_charger_gets_tell_me_more_dc(self):
        ctx = self._ctx(driver="DC", charger_state="DC", charger_city="Washington", distance=1.5)
        assert evaluate(self._tree, ctx) == "tell_me_more_dc"

    # ── New York / Brooklyn ───────────────────────────────────────────────────

    def test_ny_driver_close_to_brooklyn_charger_gets_tell_me_more_brooklyn(self):
        ctx = self._ctx(driver="NY", charger_state="NY", charger_city="Brooklyn", distance=0.75)
        assert evaluate(self._tree, ctx) == "tell_me_more_brooklyn"

    def test_ny_driver_too_far_from_brooklyn_charger_falls_to_newburgh_check(self):
        # > 5 miles from Brooklyn, and charger is not Newburgh → waitlist
        ctx = self._ctx(driver="NY", charger_state="NY", charger_city="Brooklyn", distance=8)
        assert evaluate(self._tree, ctx) == "waitlist"

    def test_ny_driver_near_newburgh_charger_gets_tell_me_more_general(self):
        ctx = self._ctx(driver="NY", charger_state="NY", charger_city="Newburgh", distance=7)
        assert evaluate(self._tree, ctx) == "tell_me_more_general"

    def test_ny_driver_far_from_newburgh_charger_gets_waitlist(self):
        ctx = self._ctx(driver="NY", charger_state="NY", charger_city="Newburgh", distance=15)
        assert evaluate(self._tree, ctx) == "waitlist"

    # ── Michigan ─────────────────────────────────────────────────────────────

    def test_mi_driver_near_charger_gets_tell_me_more_general(self):
        ctx = self._ctx(driver="MI", charger_state="MI", charger_city="Detroit", distance=2)
        assert evaluate(self._tree, ctx) == "tell_me_more_general"

    def test_mi_driver_far_from_charger_gets_waitlist(self):
        ctx = self._ctx(driver="MI", charger_state="MI", charger_city="Detroit", distance=50)
        assert evaluate(self._tree, ctx) == "waitlist"

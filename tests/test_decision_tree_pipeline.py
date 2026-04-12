"""Tests for decision tree config loading and context building in the pipeline."""

from itselectric.cli import _build_tree_context, _load_decision_tree  # type: ignore


class TestLoadDecisionTree:
    def test_returns_none_for_empty_path(self):
        assert _load_decision_tree("") is None

    def test_returns_none_for_missing_file(self, tmp_path):
        assert _load_decision_tree(str(tmp_path / "nonexistent.yaml")) is None

    def test_loads_yaml_file(self, tmp_path):
        tree_file = tmp_path / "tree.yaml"
        tree_file.write_text("email_id: 42\n")
        result = _load_decision_tree(str(tree_file))
        assert result == {"email_id": 42}

    def test_loads_nested_tree(self, tmp_path):
        tree_file = tmp_path / "tree.yaml"
        tree_file.write_text(
            "condition:\n"
            "  field: distance_miles\n"
            "  op: lt\n"
            "  value: 10\n"
            "then:\n"
            "  email_id: 111\n"
            "else:\n"
            "  email_id: 222\n"
        )
        result = _load_decision_tree(str(tree_file))
        assert result["condition"]["field"] == "distance_miles"
        assert result["then"]["email_id"] == 111


class TestBuildTreeContext:
    _CHARGER = {
        "name": "1 Main St, Boston, MA",
        "city": "Boston",
        "state": "MA",
        "lat": 42.36,
        "lon": -71.06,
    }

    def test_builds_context_with_all_fields(self):
        ctx = _build_tree_context(
            address="123 Elm St, Boston, MA 02101",
            charger_dict=self._CHARGER,
            distance_miles=2.5,
        )
        assert ctx["driver_state"] == "MA"
        assert ctx["charger_state"] == "MA"
        assert ctx["charger_city"] == "Boston"
        assert ctx["distance_miles"] == 2.5

    def test_driver_state_from_full_name(self):
        ctx = _build_tree_context(
            address="123 Elm St, Boston, Massachusetts 02101",
            charger_dict=self._CHARGER,
            distance_miles=1.0,
        )
        assert ctx["driver_state"] == "MA"

    def test_driver_state_none_when_unparseable(self):
        ctx = _build_tree_context(
            address="123 Elm Street",
            charger_dict=self._CHARGER,
            distance_miles=5.0,
        )
        assert ctx["driver_state"] is None

    def test_charger_city_and_state_from_dict(self):
        charger = {
            "name": "5 Oak St, Los Angeles, CA",
            "city": "Los Angeles",
            "state": "CA",
            "lat": 34.05,
            "lon": -118.24,
        }
        ctx = _build_tree_context(
            address="1 Some St, Pasadena, CA 91101",
            charger_dict=charger,
            distance_miles=12.0,
        )
        assert ctx["charger_city"] == "Los Angeles"
        assert ctx["charger_state"] == "CA"

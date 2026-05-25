"""Tests for config_flow/_options_helpers.py.

US-5 testability tests for pure helper functions extracted from
options.py. Each test targets killable mutation patterns in the helpers.
"""

from __future__ import annotations

from custom_components.ev_trip_planner.config_flow._options_helpers import (
    _get_option_float,
    _get_option_int,
    _get_option_str,
    _safe_data_dict,
)


class TestGetOptionFloat:
    """Tests for _get_option_float — kills default_value mutations."""

    def test_present_key_returns_value(self):
        """When key is present, returns the value."""
        data = {"battery_capacity_kwh": 75.0}
        result = _get_option_float(data, "battery_capacity_kwh", 60.0)
        assert result == 75.0

    def test_missing_key_returns_default(self):
        """When key is missing, returns the default — kills default_value mutant (None)."""
        data: dict = {}
        result = _get_option_float(data, "battery_capacity_kwh", 60.0)
        assert result == 60.0

    def test_zero_default(self):
        """Zero default works — kills mutant where default becomes 0 from None."""
        data = {}
        result = _get_option_float(data, "missing", 0.0)
        assert result == 0.0

    def test_negative_default(self):
        """Negative default works — kills mutant where default becomes positive."""
        data = {}
        result = _get_option_float(data, "missing", -1.0)
        assert result == -1.0


class TestGetOptionInt:
    """Tests for _get_option_int — kills default_value mutations."""

    def test_present_key(self):
        """When key present, returns the value."""
        data = {"safety_margin_percent": 30}
        result = _get_option_int(data, "safety_margin_percent", 10)
        assert result == 30

    def test_missing_returns_default(self):
        """Missing key → default — kills default_value mutations."""
        data = {}
        result = _get_option_int(data, "missing", 10)
        assert result == 10

    def test_zero_default(self):
        """Zero default is returned for missing keys."""
        data = {}
        result = _get_option_int(data, "missing", 0)
        assert result == 0


class TestGetOptionStr:
    """Tests for _get_option_str — kills default_value mutations."""

    def test_present_key(self):
        """When key present, returns the value."""
        data = {"soh_sensor": "sensor.battery_soh"}
        result = _get_option_str(data, "soh_sensor", "")
        assert result == "sensor.battery_soh"

    def test_missing_returns_default(self):
        """Missing key → default — kills default_value mutations."""
        data = {}
        result = _get_option_str(data, "missing", "")
        assert result == ""

    def test_non_empty_default(self):
        """Non-empty default is returned for missing keys."""
        data = {}
        result = _get_option_str(data, "missing", "default_value")
        assert result == "default_value"


class TestSafeDataDict:
    """Tests for _safe_data_dict — kills boolean_flip and default_value mutations."""

    def test_none_input(self):
        """None input → empty dict — kills mutant where None stays."""
        result = _safe_data_dict(None)
        assert result == {}

    def test_empty_dict(self):
        """Empty dict → empty dict."""
        result = _safe_data_dict({})
        assert result == {}

    def test_non_none_dict(self):
        """Non-None dict → same dict."""
        data = {"key": "value"}
        result = _safe_data_dict(data)
        assert result == data

    def test_returns_new_dict(self):
        """Returns a new dict (copy), not the original."""
        data = {"key": "value"}
        result = _safe_data_dict(data)
        result["key"] = "changed"
        assert data["key"] == "value"



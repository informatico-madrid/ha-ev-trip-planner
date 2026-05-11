"""Tests for SensorCallbackRegistry in trip._sensor_callbacks module."""

from custom_components.ev_trip_planner.trip._sensor_callbacks import SensorCallbackRegistry


class TestSensorCallbackRegistry:
    """Verify SensorCallbackRegistry class exists and basic functionality works."""

    def test_sensor_callback_registry_import(self):
        """Test that SensorCallbackRegistry can be imported from the correct module."""
        assert SensorCallbackRegistry is not None

    def test_sensor_callback_registry_is_callable(self):
        """Test that SensorCallbackRegistry can be instantiated."""
        registry = SensorCallbackRegistry()
        assert registry is not None

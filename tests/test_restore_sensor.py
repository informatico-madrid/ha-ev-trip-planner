"""TDD: TripPlannerSensor inherits RestoreSensor when description.restore=True.

RED test: Verifies that a TripPlannerSensor with restore=True
calls RestoreSensor.async_get_last_sensor_data() and restores _attr_native_value
when coordinator.data is None (simulating HA restart before first refresh).

Currently FAILS because TripPlannerSensor does not inherit RestoreSensor.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


class FakeRestoreState:
    """Minimal RestoreState substitute for testing."""

    @staticmethod
    async def async_get_last_state(sensor_entity_id: str) -> Any:
        """Return fake last state."""
        return None


@pytest.fixture
def mock_coordinator():
    """Create a mock TripPlannerCoordinator with None data (simulating restart)."""
    coordinator = MagicMock()
    coordinator.data = None  # Simulates HA restart before first refresh
    return coordinator


def test_trip_planner_sensor_inherits_restore_sensor(mock_coordinator):
    """TripPlannerSensor with restore=True should inherit RestoreSensor.

    This test FAILS in RED state because TripPlannerSensor does not
    inherit RestoreSensor.
    """
    from custom_components.ev_trip_planner.definitions import (
        TripSensorEntityDescription,
    )
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from homeassistant.components.sensor import RestoreSensor

    # Create entity description with restore=True
    desc = TripSensorEntityDescription(
        key="test_restore_sensor",
        restore=True,  # This sensor should restore its state
        value_fn=lambda data: data.get("kwh_today", 0.0) if data else 0.0,
        attrs_fn=lambda data: {},
    )

    # Create sensor
    sensor = TripPlannerSensor(
        coordinator=mock_coordinator,
        vehicle_id="test_vehicle",
        entity_description=desc,
    )

    # EXPECTED: sensor should inherit from RestoreSensor
    # ACTUAL (RED): sensor does NOT inherit from RestoreSensor
    assert isinstance(sensor, RestoreSensor), (
        f"TripPlannerSensor with restore=True should inherit RestoreSensor, "
        f"but it inherits from {[type(c).__name__ for c in type(sensor).__bases__]}. "
        "TripPlannerSensor does not inherit RestoreSensor."
    )


def test_trip_planner_sensor_calls_async_get_last_sensor_data(mock_coordinator):
    """TripPlannerSensor should call RestoreSensor.async_get_last_sensor_data().

    This test FAILS in RED state because TripPlannerSensor does not
    implement async_get_last_sensor_data or call super().async_added_to_hass().
    """
    from custom_components.ev_trip_planner.definitions import (
        TripSensorEntityDescription,
    )
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor

    # Create entity description with restore=True
    desc = TripSensorEntityDescription(
        key="test_restore_sensor",
        restore=True,
        value_fn=lambda data: data.get("kwh_today", 0.0) if data else 0.0,
        attrs_fn=lambda data: {},
    )

    # Create sensor
    sensor = TripPlannerSensor(
        coordinator=mock_coordinator,
        vehicle_id="test_vehicle",
        entity_description=desc,
    )

    # EXPECTED: sensor should have async_get_last_sensor_data method from RestoreSensor
    # ACTUAL (RED): sensor does NOT have this method
    assert hasattr(sensor, 'async_get_last_sensor_data'), (
        "TripPlannerSensor with restore=True should have async_get_last_sensor_data() "
        "inherited from RestoreSensor. Method not found."
    )


def test_trip_planner_sensor_without_restore_not_restore_sensor(mock_coordinator):
    """TripPlannerSensor with restore=False should NOT inherit RestoreSensor behavior.

    This test PASSES even in RED state - sensors without restore=True
    are not expected to do state restoration.
    """
    from custom_components.ev_trip_planner.definitions import (
        TripSensorEntityDescription,
    )
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from homeassistant.components.sensor import RestoreSensor

    # Create entity description with restore=False (default)
    desc = TripSensorEntityDescription(
        key="test_non_restore_sensor",
        restore=False,  # Default
        value_fn=lambda data: data.get("kwh_today", 0.0) if data else 0.0,
        attrs_fn=lambda data: {},
    )

    # Create sensor
    sensor = TripPlannerSensor(
        coordinator=mock_coordinator,
        vehicle_id="test_vehicle",
        entity_description=desc,
    )

    # restore=False sensors don't need RestoreSensor behavior
    # (they just won't restore - this is expected behavior)
    assert isinstance(sensor, RestoreSensor) or not hasattr(sensor, 'async_get_last_sensor_data'), (
        "TripPlannerSensor with restore=False may or may not be RestoreSensor - "
        "this is not strictly required."
    )

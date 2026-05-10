"""TDD: TripPlannerSensor checks exists_fn before creating entity.

Test: Verifies that when a sensor's exists_fn returns False,
the sensor is NOT added via async_setup_entry.

Currently FAILS because async_setup_entry creates all sensors from TRIP_SENSORS
without checking exists_fn.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class FakeEntry:
    """Minimal ConfigEntry substitute for testing."""

    def __init__(self, entry_id: str, data: dict[str, Any]) -> None:
        self.entry_id = entry_id
        self.data = data
        self.version = 1
        self.minor_version = 1

        class FakeRuntimeData:
            def __init__(self):
                self.trip_manager = MagicMock()
                self.coordinator = MagicMock()
                self.sensor_async_add_entities = None

        self.runtime_data = FakeRuntimeData()

    @property
    def unique_id(self) -> str:
        return self.entry_id




@pytest.fixture
def mock_coordinator():
    """Create a mock TripPlannerCoordinator with data."""
    coordinator = MagicMock()
    coordinator.data = {
        "recurring_trips": {},
        "punctual_trips": {},
        "kwh_today": 0.0,
        "hours_today": 0,
        "next_trip": None,
        "emhass_power_profile": None,
        "emhass_deferrables_schedule": None,
        "emhass_status": None,
    }
    coordinator.async_config_entry_first_refresh = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_sensor_with_exists_fn_false_not_added_by_setup_entry(
    mock_hass, mock_coordinator
):
    """Sensor with exists_fn returning False should NOT be added via async_setup_entry.

    This test FAILS in RED state because async_setup_entry creates all sensors
    from TRIP_SENSORS without checking exists_fn.

    The fix (G-07.4) will filter sensors based on exists_fn before adding.
    """
    from custom_components.ev_trip_planner import sensor
    from custom_components.ev_trip_planner.definitions import (
        TRIP_SENSORS,
        TripSensorEntityDescription,
    )

    entry = FakeEntry(
        entry_id="test_entry",
        data={"vehicle_name": "TestVehicle"},
    )
    entry.runtime_data.coordinator = mock_coordinator
    entry.runtime_data.trip_manager = MagicMock()
    entry.runtime_data.trip_manager.async_get_all_trips = AsyncMock(return_value=[])

    created_entities = []

    def capture_entities(entities):
        created_entities.extend(entities)

    # Patch TRIP_SENSORS to include a sensor with exists_fn returning False
    custom_sensors = list(TRIP_SENSORS) + [
        TripSensorEntityDescription(
            key="conditional_sensor",
            exists_fn=lambda data: False,  # Should NOT be added
            value_fn=lambda data: "value",
            attrs_fn=lambda data: {},
        ),
    ]

    with patch.object(sensor, "TRIP_SENSORS", custom_sensors):
        with patch.object(
            sensor, "_async_create_trip_sensors", AsyncMock(return_value=[])
        ):
            await sensor.async_setup_entry(mock_hass, entry, capture_entities)

    # EXPECTED: "conditional_sensor" should NOT be in created entities
    # ACTUAL (RED): "conditional_sensor" IS in created entities because exists_fn is not checked
    created_keys = [
        getattr(e, "entity_description", None) and e.entity_description.key
        for e in created_entities
    ]

    assert "conditional_sensor" not in created_keys, (
        f"Expected 'conditional_sensor' (exists_fn=False) to NOT be created, "
        f"but it was created. async_setup_entry does not check exists_fn. "
        f"Created sensors: {created_keys}"
    )


@pytest.mark.asyncio
async def test_sensor_with_exists_fn_true_is_added_by_setup_entry(
    mock_hass, mock_coordinator
):
    """Sensor with exists_fn returning True SHOULD be added via async_setup_entry.

    This test PASSES even in RED state because sensors are added normally.
    """
    from custom_components.ev_trip_planner import sensor
    from custom_components.ev_trip_planner.definitions import (
        TRIP_SENSORS,
        TripSensorEntityDescription,
    )

    entry = FakeEntry(
        entry_id="test_entry",
        data={"vehicle_name": "TestVehicle"},
    )
    entry.runtime_data.coordinator = mock_coordinator
    entry.runtime_data.trip_manager = MagicMock()
    entry.runtime_data.trip_manager.async_get_all_trips = AsyncMock(return_value=[])

    created_entities = []

    def capture_entities(entities):
        created_entities.extend(entities)

    # Patch TRIP_SENSORS to include a sensor with exists_fn returning True
    custom_sensors = list(TRIP_SENSORS) + [
        TripSensorEntityDescription(
            key="unconditional_sensor",
            exists_fn=lambda data: True,  # SHOULD be added
            value_fn=lambda data: "value",
            attrs_fn=lambda data: {},
        ),
    ]

    with patch.object(sensor, "TRIP_SENSORS", custom_sensors):
        with patch.object(
            sensor, "_async_create_trip_sensors", AsyncMock(return_value=[])
        ):
            await sensor.async_setup_entry(mock_hass, entry, capture_entities)

    # EXPECTED: "unconditional_sensor" SHOULD be in created entities
    created_keys = [
        getattr(e, "entity_description", None) and e.entity_description.key
        for e in created_entities
    ]

    assert "unconditional_sensor" in created_keys, (
        f"Expected 'unconditional_sensor' (exists_fn=True) to be created, "
        f"but it was NOT created. Created sensors: {created_keys}"
    )

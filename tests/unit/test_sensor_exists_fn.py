"""TDD: TripPlannerSensor checks exists_fn before creating entity.

Test: Verifies that when a sensor's exists_fn returns False,
the sensor is NOT added via async_setup_entry.
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


def _make_trip_manager():
    """Create a trip_manager mock with all async methods needed by sensor setup."""
    tm = MagicMock()
    tm.async_get_all_trips = AsyncMock(return_value=[])
    tm.async_get_recurring_trips = AsyncMock(return_value={})
    tm.async_get_punctual_trips = AsyncMock(return_value={})
    return tm


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
    """Sensor with exists_fn returning False should NOT be added via async_setup_entry."""
    from custom_components.ev_trip_planner import sensor
    from custom_components.ev_trip_planner.definitions import (
        TRIP_SENSORS,
        TripSensorEntityDescription,
    )

    created_keys: list[str] = []
    entities_added: list = []

    entry = FakeEntry(
        entry_id="test_entry",
        data={"vehicle_name": "TestVehicle"},
    )
    entry.runtime_data.coordinator = mock_coordinator
    entry.runtime_data.trip_manager = _make_trip_manager()

    custom_sensors = list(TRIP_SENSORS) + [
        TripSensorEntityDescription(
            key="conditional_sensor",
            exists_fn=lambda data: False,  # Should NOT be added
            value_fn=lambda data: "value",
            attrs_fn=lambda data: {},
        ),
    ]

    def capture_entities(entities):
        entities_added.extend(entities)
        for e in entities:
            if hasattr(e, "entity_description") and e.entity_description:
                created_keys.append(e.entity_description.key)

    # Patch sensor._async_setup.TRIP_SENSORS (where the code reads from)
    from custom_components.ev_trip_planner.sensor import _async_setup

    with patch.object(_async_setup, "TRIP_SENSORS", custom_sensors):
        await sensor.async_setup_entry(mock_hass, entry, capture_entities)

    # EXPECTED: "conditional_sensor" should NOT be in created keys
    assert "conditional_sensor" not in created_keys, (
        f"Expected 'conditional_sensor' (exists_fn=False) to NOT be created, "
        f"but it was. Created sensors: {created_keys}"
    )


@pytest.mark.asyncio
async def test_sensor_with_exists_fn_true_is_added_by_setup_entry(
    mock_hass, mock_coordinator
):
    """Sensor with exists_fn returning True SHOULD be added via async_setup_entry."""
    from custom_components.ev_trip_planner import sensor
    from custom_components.ev_trip_planner.definitions import (
        TRIP_SENSORS,
        TripSensorEntityDescription,
    )

    created_keys: list[str] = []
    entities_added: list = []

    entry = FakeEntry(
        entry_id="test_entry",
        data={"vehicle_name": "TestVehicle"},
    )
    entry.runtime_data.coordinator = mock_coordinator
    entry.runtime_data.trip_manager = _make_trip_manager()

    custom_sensors = list(TRIP_SENSORS) + [
        TripSensorEntityDescription(
            key="unconditional_sensor",
            exists_fn=lambda data: True,  # SHOULD be added
            value_fn=lambda data: "value",
            attrs_fn=lambda data: {},
        ),
    ]

    def capture_entities(entities):
        entities_added.extend(entities)
        for e in entities:
            if hasattr(e, "entity_description") and e.entity_description:
                created_keys.append(e.entity_description.key)

    # Patch sensor._async_setup.TRIP_SENSORS (where the code reads from)
    from custom_components.ev_trip_planner.sensor import _async_setup

    with patch.object(_async_setup, "TRIP_SENSORS", custom_sensors):
        await sensor.async_setup_entry(mock_hass, entry, capture_entities)

    # EXPECTED: "unconditional_sensor" SHOULD be in created keys
    assert "unconditional_sensor" in created_keys, (
        f"Expected 'unconditional_sensor' (exists_fn=True) to be created, "
        f"but it was NOT created. Created sensors: {created_keys}"
    )

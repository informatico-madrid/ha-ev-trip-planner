"""TDD: setup de sensores vía async_setup_entry."""

from __future__ import annotations

from typing import Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest


class FakeEntry:
    def __init__(self, entry_id: str, data: dict[str, Any]) -> None:
        self.entry_id = entry_id
        self.data = data
        self.runtime_data = None  # Set later in test


@pytest.mark.asyncio
async def test_async_setup_entry_creates_three_sensors():
    from custom_components.ev_trip_planner.sensor import async_setup_entry

    hass = MagicMock()
    # Seed shared TripManager and coordinator in hass.data like real setup_entry does
    tm = MagicMock()
    tm.async_get_all_trips = AsyncMock(return_value=[])
    
    # FIX: Add coordinator to the test data with AsyncMock for awaitable methods
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.async_config_entry_first_refresh = AsyncMock()  # FIX: Hacerlo awaitable
    
    # Add async_get_recurring_trips and async_get_punctual_trips to the mock trip_manager
    tm.async_get_recurring_trips = AsyncMock(return_value=[])
    tm.async_get_punctual_trips = AsyncMock(return_value=[])

    hass.data = {"ev_trip_planner": {"eid123": {"trip_manager": tm, "config": {}, "coordinator": coordinator}}}

    entry = FakeEntry(
        entry_id="eid123",
        data={"vehicle_name": "Chispitas"},
    )

    # Set up runtime_data like __init__.py::async_setup_entry does
    class FakeRuntimeData:
        def __init__(self, tm, coordinator):
            self.trip_manager = tm
            self.coordinator = coordinator
            self.sensor_async_add_entities = None
    entry.runtime_data = FakeRuntimeData(tm, coordinator)

    created: List[Any] = []

    def add_entities(ents):
        created.extend(ents)

    await async_setup_entry(hass, entry, add_entities)

    assert len(created) == 8  # 3 sensores originales + 4 sensores de cálculo + 1 EMHASS sensor

    # Verify EMHASS sensor has correct unique_id
    emhass_sensor = next((e for e in created if hasattr(e, '_attr_unique_id') and e._attr_unique_id and 'emhass' in e._attr_unique_id), None)
    assert emhass_sensor is not None, "EMHASS sensor should be created"
    assert emhass_sensor._attr_unique_id == "emhass_perfil_diferible_eid123"

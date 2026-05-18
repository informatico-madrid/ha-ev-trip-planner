"""Additional focused tests targeting remaining branches in trip_manager.py."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager
from tests import FakeTripStorage, create_mock_ev_config_entry


@pytest.mark.asyncio
async def test_load_trips_from_injected_storage_with_data() -> None:
    # Storage provides a dict with 'data' key (Store API shape)
    stored = {
        "data": {
            "trips": {"legacy": {}},
            "recurring_trips": {
                "r1": {"id": "r1", "hora": "08:00", "dia_semana": "lunes"}
            },
            "punctual_trips": {
                "p1": {
                    "id": "p1",
                    "datetime": "2026-05-01T10:00:00",
                    "estado": "pendiente",
                }
            },
        }
    }
    storage = FakeTripStorage(initial_data=stored)
    hass = MagicMock()
    tm = TripManager(hass, "veh_load", storage=storage)

    await tm._load_trips()

    assert isinstance(tm._recurring_trips, dict)
    assert "r1" in tm._recurring_trips
    assert "p1" in tm._punctual_trips


@pytest.mark.asyncio
async def test_load_trips_from_injected_storage_direct_shape() -> None:
    # Storage provides direct dict (legacy shape without 'data')
    stored = {
        "trips": {},
        "recurring_trips": {
            "r2": {"id": "r2", "hora": "09:00", "dia_semana": "martes"}
        },
        "punctual_trips": {},
    }
    storage = FakeTripStorage(initial_data=stored)
    hass = MagicMock()
    tm = TripManager(hass, "veh_load2", storage=storage)

    await tm._load_trips()

    assert "r2" in tm._recurring_trips


@pytest.mark.asyncio
async def test_async_add_recurring_trip_calls_emhass_when_coordinator_present() -> None:
    hass = MagicMock()
    # Create config entry and ensure lookup returns it
    entry = create_mock_ev_config_entry(
        None, data={"vehicle_name": "veh_emhass"}, entry_id="e_em"
    )
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    # Provide runtime_data.coordinator on entry
    entry.runtime_data = SimpleNamespace(coordinator=MagicMock())

    storage = FakeTripStorage()
    tm = TripManager(hass, "veh_emhass", entry_id="e_em", storage=storage)

    # Patch sensor creation functions to observe calls
    with (
        patch(
            "custom_components.ev_trip_planner.sensor.async_create_trip_sensor",
            new=AsyncMock(),
        ) as mock_create_sensor,
        patch(
            "custom_components.ev_trip_planner.sensor.async_create_trip_emhass_sensor",
            new=AsyncMock(),
        ) as mock_create_emhass,
    ):
        await tm.async_add_recurring_trip(
            dia_semana="lunes", hora="08:00", km=10, kwh=1.0
        )

    mock_create_sensor.assert_awaited()
    mock_create_emhass.assert_awaited()


@pytest.mark.asyncio
async def test_async_update_trip_sensor_with_registry_present() -> None:
    hass = MagicMock()
    tm = TripManager(hass, "veh_reg")
    # Seed a recurring trip so trip_data is found
    tm._recurring_trips = {
        "rX": {"id": "rX", "tipo": "recurrente", "hora": "08:00", "activo": True}
    }

    # Fake registry: async_get(self.hass) -> registry with async_get(entity_id) != None
    class FakeRegistry:
        def async_get(self, entity_id):
            return SimpleNamespace(entity_id=entity_id)

    fake_registry = FakeRegistry()

    # Patch the entity_registry async_get function to return our fake registry
    with patch(
        "homeassistant.helpers.entity_registry.async_get", return_value=fake_registry
    ):
        # Patch hass.states.async_set to capture update
        hass.states = MagicMock()
        hass.states.async_set = MagicMock()

        await tm.async_update_trip_sensor("rX")

        hass.states.async_set.assert_called()

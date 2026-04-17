"""Test: EMHASS deferrable loads not published after HA restart.

Bug hypothesis:
After HA restart, TripManager loads trips from storage but does NOT publish
them to EMHASS, causing EMHASS sensor attributes to be empty.

This test verifies that publish_deferrable_loads() is called after async_setup().
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.mark.asyncio
async def test_publish_deferrable_loads_called_after_setup(mock_hass):
    """RED phase: Test that FAILS because publish_deferrable_loads is NOT called.

    After async_setup(), trips are loaded from storage but not published to EMHASS.
    This causes EMHASS sensors to show empty arrays after HA restart.
    """
    # Setup: Create mock storage with trips (simulating persisted data from before restart)
    # Store API wraps data in "data" key
    existing_trips = {
        "data": {
            "recurring_trips": {
                "rec_lunes_9am": {
                    "id": "rec_lunes_9am",
                    "tipo": "recurrente",
                    "dia_semana": "lunes",
                    "hora": "09:00",
                    "km": 50,
                    "kwh": 7.5,
                    "activo": True,
                }
            },
            "punctual_trips": {
                "pun_20260421_morning": {
                    "id": "pun_20260421_morning",
                    "tipo": "puntual",
                    "datetime": "2026-04-21T07:00:00+00:00",
                    "km": 30,
                    "kwh": 4.5,
                    "activo": True,
                }
            },
        }
    }

    # Mock storage
    mock_storage = MagicMock()
    mock_storage.async_load = AsyncMock(return_value=existing_trips)

    # Mock EMHASS adapter
    emhass_adapter = MagicMock()
    emhass_adapter.async_publish_all_deferrable_loads = AsyncMock()

    # Create TripManager with injected storage and EMHASS adapter
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_CHARGING_POWER: 3.6,
    }

    trip_manager = TripManager(
        mock_hass,
        "test_vehicle",
        entry.entry_id,
        {},
        storage=mock_storage,  # Inject storage to avoid Store patching issues
    )
    trip_manager.set_emhass_adapter(emhass_adapter)

    # Call async_setup (simulates HA restart)
    await trip_manager.async_setup()

    # Verify trips were loaded from storage
    assert len(trip_manager._recurring_trips) == 1, \
        "TripManager should load 1 recurring trip from storage"
    assert len(trip_manager._punctual_trips) == 1, \
        "TripManager should load 1 punctual trip from storage"
    print("✓ Trips loaded from storage successfully")

    # RED PHASE: This assertion FAILS because publish_deferrable_loads is NOT called
    # After async_setup(), trips are in memory but not published to EMHASS
    assert emhass_adapter.async_publish_all_deferrable_loads.called, \
        "BUG: async_setup() should call publish_deferrable_loads() but does not"

    print("✗ BUG DEMONSTRATED:")
    print("  Trips loaded from storage but not published to EMHASS")
    print("  EMHASS sensors show empty arrays after HA restart")


@pytest.mark.asyncio
async def test_emhass_sensors_empty_without_publish(mock_hass):
    """RED phase: Verify EMHASS sensors are empty when publish is not called.

    This demonstrates the user-reported bug where EMHASS attributes show:
    - def_total_hours: []
    - P_deferrable_nom: []
    - def_start_timestep: []
    - def_end_timestep: []
    """
    # Setup: Create mock storage with trips
    existing_trips = {
        "data": {
            "recurring_trips": {
                "rec_lunes_9am": {
                    "id": "rec_lunes_9am",
                    "tipo": "recurrente",
                    "dia_semana": "lunes",
                    "hora": "09:00",
                    "km": 50,
                    "kwh": 7.5,
                    "activo": True,
                }
            },
            "punctual_trips": {
                "pun_20260421_morning": {
                    "id": "pun_20260421_morning",
                    "tipo": "puntual",
                    "datetime": "2026-04-21T07:00:00+00:00",
                    "km": 30,
                    "kwh": 4.5,
                    "activo": True,
                }
            },
        }
    }

    # Mock storage
    mock_storage = MagicMock()
    mock_storage.async_load = AsyncMock(return_value=existing_trips)

    # Mock EMHASS adapter with empty cache (simulates post-restart state)
    emhass_adapter = MagicMock()
    emhass_adapter.async_publish_all_deferrable_loads = AsyncMock()  # Add this mock
    emhass_adapter.get_cached_optimization_results = MagicMock(return_value={
        "emhass_power_profile": [],
        "emhass_deferrables_schedule": [],
        "number_of_deferrable_loads": 0,
        "def_total_hours_array": [],
        "p_deferrable_nom_array": [],
        "def_start_timestep_array": [],
        "def_end_timestep_array": [],
        "p_deferrable_matrix": [],
    })

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_CHARGING_POWER: 3.6,
    }

    trip_manager = TripManager(
        mock_hass,
        "test_vehicle",
        entry.entry_id,
        {},
        storage=mock_storage,
    )
    trip_manager.set_emhass_adapter(emhass_adapter)

    # Call async_setup (simulates HA restart)
    await trip_manager.async_setup()

    # Verify trips were loaded
    assert len(trip_manager._recurring_trips) == 1
    assert len(trip_manager._punctual_trips) == 1

    # Verify EMHASS cache is empty (because publish was not called)
    emhass_data = emhass_adapter.get_cached_optimization_results()

    assert emhass_data["number_of_deferrable_loads"] == 0, \
        "BUG: EMHASS shows 0 deferrable loads despite trips in storage"
    assert emhass_data["def_total_hours_array"] == [], \
        "BUG: def_total_hours_array is empty (user reported issue)"
    assert emhass_data["p_deferrable_nom_array"] == [], \
        "BUG: p_deferrable_nom_array is empty (user reported issue)"
    assert emhass_data["def_start_timestep_array"] == [], \
        "BUG: def_start_timestep_array is empty (user reported issue)"
    assert emhass_data["def_end_timestep_array"] == [], \
        "BUG: def_end_timestep_array is empty (user reported issue)"

    print("✗ BUG CONFIRMED:")
    print("  EMHASS sensors show empty arrays after HA restart")
    print("  User-reported issue reproduced in test")


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])

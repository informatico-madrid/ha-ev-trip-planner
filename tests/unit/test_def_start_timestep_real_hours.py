"""Test that def_start_timestep reflects actual hours until trip departure.

BUG: def_start_timestep is 0 when it should be ~7 hours (from 2:20 to 9:40).
The code falls back to default def_start=0 when charging_windows is empty,
instead of using the actual trip datetime to calculate hours until departure.

This test should FAIL with current code and PASS after fix.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass.adapter import (
    EMHASSAdapter,
    PerTripCacheParams,
)


@pytest.fixture
def mock_store():
    """Create a mock Store instance."""
    store = MagicMock()
    store.data = {"trips": {}, "emhass_indices": {}}
    return store


@pytest.fixture
def mock_hass(tmp_path):
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.config.config_dir = tmp_path
    return hass


@pytest.mark.asyncio
async def test_def_start_matches_actual_hours_until_departure(mock_hass, mock_store):
    """
    Test that def_start_timestep equals actual hours from now to trip departure.
    
    Scenario:
    - Now: 02:20 (2:20 AM)
    - Trip departure: 09:40 (7h20m later)
    - def_start_timestep should be ~7 (hours until departure)
    
    Current bug: def_start_timestep is 0 because charging_windows is empty.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.4,
    }

    # Now = 02:20 UTC
    now = datetime(2026, 5, 15, 2, 20, 0, tzinfo=timezone.utc)

    # Trip departure = 09:40 UTC (7h20m later)
    trip_departure = now + timedelta(hours=7, minutes=20)

    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": trip_departure.isoformat(),
        "km": 30.0,
        "kwh": 5.4,  # 30km * 0.18 kWh/km
    }

    with patch(
        "custom_components.ev_trip_planner.emhass.adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    # Patch now to control the time
    with patch(
        "homeassistant.util.dt.now",
        return_value=now,
    ):
        await adapter._populate_per_trip_cache_entry(
            PerTripCacheParams(
                trip=trip,
                trip_id=trip["id"],
                charging_power_kw=3.4,
                battery_capacity_kwh=28.0,
                safety_margin_percent=10.0,
                soc_current=31.0,
            ),
        )

    params = adapter._cached_per_trip_params.get(trip["id"])
    actual_def_start = params.get("def_start_timestep")
    actual_def_end = params.get("def_end_timestep")
    actual_total_hours = params.get("def_total_hours", 0)

    # Calculate expected values
    hours_until_departure = (trip_departure - now).total_seconds() / 3600
    expected_def_start = round(hours_until_departure)

    print(f"\nDEBUG: Now = {now}")
    print(f"DEBUG: Trip departure = {trip_departure}")
    print(f"DEBUG: Hours until departure = {hours_until_departure}")
    print(f"DEBUG: actual_def_start = {actual_def_start}")
    print(f"DEBUG: actual_def_end = {actual_def_end}")
    print(f"DEBUG: actual_total_hours = {actual_total_hours}")

    # Expected: def_start = 0 (inicio_ventana = now since car is home)
    # def_end = 8 (fin_ventana = trip departure at 09:40 = 7.33 hours from now, ceiling = 8)
    # total_hours = 2 (actual charging time needed)
    expected_def_start = 0
    expected_def_end = 8

    print(f"\nDEBUG: Now = {now}")
    print(f"DEBUG: Trip departure = {trip_departure}")
    print(f"DEBUG: Hours until departure = {hours_until_departure}")
    print(f"DEBUG: actual_def_start = {actual_def_start}")
    print(f"DEBUG: actual_def_end = {actual_def_end}")
    print(f"DEBUG: actual_total_hours = {actual_total_hours}")
    print(f"DEBUG: window_size = {actual_def_end - actual_def_start}")

    # def_start should be 0 since inicio_ventana = now (car is home)
    assert actual_def_start == expected_def_start, (
        f"def_start_timestep ({actual_def_start}) should be {expected_def_start} "
        f"(inicio_ventana = now since car is home with hora_regreso=None)"
    )

    # def_end should be 7 (fin_ventana = trip departure)
    assert actual_def_end == expected_def_end, (
        f"def_end_timestep ({actual_def_end}) should be {expected_def_end} "
        f"(fin_ventana = trip departure at {trip_departure})"
    )


@pytest.mark.asyncio
async def test_def_end_uses_trip_departure_not_hours_available(mock_hass, mock_store):
    """
    Test that def_end_timestep is based on trip departure, not hours_available.
    
    Bug: def_end is calculated as min(hours_available, 168) where
    hours_available = (deadline - now). But this should be the actual
    trip departure time, not "hours until deadline from now".
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.4,
    }

    # Now = 02:20 UTC
    now = datetime(2026, 5, 15, 2, 20, 0, tzinfo=timezone.utc)

    # Trip departure = 09:40 UTC
    trip_departure = now + timedelta(hours=7, minutes=20)

    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": trip_departure.isoformat(),
        "km": 30.0,
        "kwh": 5.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass.adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    with patch(
        "homeassistant.util.dt.now",
        return_value=now,
    ):
        await adapter._populate_per_trip_cache_entry(
            PerTripCacheParams(
                trip=trip,
                trip_id=trip["id"],
                charging_power_kw=3.4,
                battery_capacity_kwh=28.0,
                safety_margin_percent=10.0,
                soc_current=31.0,
            ),
        )

    params = adapter._cached_per_trip_params.get(trip["id"])
    actual_def_start = params.get("def_start_timestep")
    actual_def_end = params.get("def_end_timestep")
    def_total_hours = params.get("def_total_hours")

    # FIX VERIFIED: def_end is based on fin_ventana (trip departure time),
    # NOT def_start + total_hours.
    # The window is 8 hours wide (from 02:20 to 09:40 = 7.33h, ceiling = 8),
    # and charging takes 2 hours (def_total_hours).
    # def_end should be 8 (fin_ventana = trip departure).
    assert actual_def_end == 8, (
        f"def_end ({actual_def_end}) should be 8 (hours until trip departure at {trip_departure})"
    )
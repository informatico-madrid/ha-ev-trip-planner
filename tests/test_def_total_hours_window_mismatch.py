"""RED phase test: Failing test demonstrating def_total_hours > available window bug.

BUG: When a trip has a short charging window (e.g., departure is soon after return),
def_total_hours can exceed the available window (def_end - def_start).

EMHASS warning: "Available timeframe is shorter than the specified number of hours
to operate. Optimization will fail."

FIX: Cap def_total_hours to min(original_hours, available_window_hours) so EMHASS
never receives an impossible optimization request.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import pytest

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
    RETURN_BUFFER_HOURS,
)
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


@pytest.mark.asyncio
async def test_def_total_hours_exceeds_window_due_to_low_soc(mock_hass, mock_store):
    """
    Scenario: Very low SOC (5%) means trip needs ~9 hours of charging,
    but the charging window is only 1 hour. This creates an impossible EMHASS request.
    
    The bug: determine_charging_need calculates total_hours from kwh/power_kw
    WITHOUT considering the window size. When window < hours_needed, EMHASS fails.
    
    Expected fix: def_total_hours should be capped to min(original_hours, window_size).
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)

    # Trip with deadline in 44 hours - BUT window is only 1 hour (trip 1 pattern)
    # This happens when sequential trips are scheduled close together
    hora_regreso = now + timedelta(hours=43)  # Very late return
    deadline = now + timedelta(hours=44)  # Departure 1 hour later = 1h window!
    
    trip = {
        "id": "short_window_low_soc",
        "tipo": "puntual",
        "datetime": deadline.isoformat(),
        "kwh": 30.0,  # Needs ~8 hours at 3.6kW but window is 1h
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    # VERY LOW SOC (5%) so charging is definitely needed
    soc_current = 5.0

    # Call _populate_per_trip_cache_entry with short window scenario
    await adapter._populate_per_trip_cache_entry(
        trip=trip,
        trip_id=trip["id"],
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        safety_margin_percent=10.0,
        soc_current=soc_current,
        hora_regreso=hora_regreso,
    )

    params = adapter._cached_per_trip_params.get(trip["id"])
    assert params is not None, "Parameters should be cached"

    def_start = params.get("def_start_timestep")
    def_end = params.get("def_end_timestep")
    def_total_hours = params.get("def_total_hours")
    window_size = def_end - def_start
    
    print(f"\nDEBUG Short Window + Low SOC:")
    print(f"  hora_regreso = {hora_regreso}")
    print(f"  deadline = {deadline}")
    print(f"  def_start = {def_start}")
    print(f"  def_end = {def_end}")
    print(f"  window_size = {window_size}")
    print(f"  def_total_hours = {def_total_hours}")
    print(f"  soc_current = {soc_current}%")
    
    # Verify charging is needed
    assert def_total_hours > 0, "With 5% SOC, charging should be needed"
    
    # The bug: def_total_hours (8h) > window_size (1h) -> EMHASS fails
    assert def_total_hours <= window_size, \
        f"BUG: def_total_hours ({def_total_hours}h) exceeds window_size ({window_size}h). " \
        f"EMHASS will fail with 'Available timeframe is shorter than the specified number of hours'. " \
        f"Fix: cap def_total_hours to window_size."


@pytest.mark.asyncio  
async def test_def_total_hours_respects_window_size_cap(mock_hass, mock_store):
    """
    This test verifies that def_total_hours is properly capped to window_size
    when the window is smaller than hours needed.
    
    Bug location: _populate_per_trip_cache_entry in emhass_adapter.py
    The code at line 631 sets def_total_hours from decision.def_total_hours
    but never caps it to the available window size.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)

    # Short window scenario
    hora_regreso = now + timedelta(hours=42)
    deadline = now + timedelta(hours=43)  # 1 hour window
    
    trip = {
        "id": "trip_short_window",
        "tipo": "puntual",
        "datetime": deadline.isoformat(),
        "kwh": 7.2,  # 2 hours at 3.6kW
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    # Low SOC to force charging need
    soc_current = 10.0

    await adapter._populate_per_trip_cache_entry(
        trip=trip,
        trip_id=trip["id"],
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        safety_margin_percent=10.0,
        soc_current=soc_current,
        hora_regreso=hora_regreso,
    )

    params = adapter._cached_per_trip_params.get(trip["id"])
    assert params is not None

    def_start = params.get("def_start_timestep")
    def_end = params.get("def_end_timestep")
    def_total_hours = params.get("def_total_hours")
    window_size = def_end - def_start
    
    print(f"\nDEBUG Window Size Cap:")
    print(f"  def_start={def_start}, def_end={def_end}, window_size={window_size}")
    print(f"  def_total_hours={def_total_hours}")
    
    # If charging needed, verify window is large enough OR def_total_hours is capped
    if def_total_hours > 0:
        # This is the assertion that FAILS with current code
        assert def_total_hours <= window_size, \
            f"BUG: def_total_hours ({def_total_hours}h) > window_size ({window_size}h). " \
            f"Fix: cap def_total_hours to window_size in _populate_per_trip_cache_entry."

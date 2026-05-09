"""RED phase test: Failing test against real emhass_adapter.py code.

This test FAILS because the current code has a bug where def_end_timestep
is calculated incorrectly.

After fixing the bug in emhass_adapter.py, this test should PASS.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


@pytest.mark.asyncio
async def test_populate_cache_entry_def_end_should_be_greater_than_def_start(
    mock_hass, mock_store
):
    """
    Bug: When charging window starts near deadline, def_end_timestep equals
    def_start_timestep, creating a zero-duration window.

    This test verifies that after the fix, def_end_timestep > def_start_timestep.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)

    # Trip with deadline far in the future
    deadline = now + timedelta(hours=96)
    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": deadline.isoformat(),
        "kwh": 21.0,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    # Call _populate_per_trip_cache_entry which calculates def_start and def_end
    await adapter._populate_per_trip_cache_entry(
        trip=trip,
        trip_id=trip["id"],
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        safety_margin_percent=10.0,
        soc_current=50.0,
        hora_regreso=None,  # Car not yet returned - triggers the bug scenario
    )

    # Get cached parameters
    params = adapter._cached_per_trip_params.get(trip["id"])
    assert params is not None, "Parameters should be cached"

    def_start = params.get("def_start_timestep")
    def_end = params.get("def_end_timestep")
    def_total_hours = params.get("def_total_hours")

    assert (
        def_end > def_start
    ), f"BUG: def_end ({def_end}) should be > def_start ({def_start}) for {def_total_hours}h charge"

    # Also verify the window is large enough
    window_size = def_end - def_start
    assert (
        window_size >= def_total_hours
    ), f"BUG: Window size ({window_size}h) < charging time ({def_total_hours}h)"


@pytest.mark.asyncio
async def test_populate_cache_entry_def_end_uses_fin_ventana_not_hours_available(
    mock_hass, mock_store
):
    """
    This test will FAIL until the bug is fixed.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=48)  # 2 days from now
    trip = {
        "id": "test_trip_2",
        "tipo": "puntual",
        "datetime": deadline.isoformat(),
        "kwh": 7.0,  # ~2 hours at 3.6 kW
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    # Car already returned
    hora_regreso = now - timedelta(hours=10)

    await adapter._populate_per_trip_cache_entry(
        trip=trip,
        trip_id=trip["id"],
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        safety_margin_percent=10.0,
        soc_current=50.0,
        hora_regreso=hora_regreso,
    )

    params = adapter._cached_per_trip_params.get(trip["id"])
    def_start = params.get("def_start_timestep")
    def_end = params.get("def_end_timestep")

    # With the fix: def_end should be based on fin_ventana (deadline)
    # not just hours_available
    # When car has returned, charging can start immediately (def_start=0)
    # and should continue until deadline (def_end=48)
    assert def_end >= 48, f"def_end ({def_end}) should be >= 48 (hours to deadline)"

    assert (
        def_end > def_start
    ), f"def_end ({def_end}) should be > def_start ({def_start})"


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])

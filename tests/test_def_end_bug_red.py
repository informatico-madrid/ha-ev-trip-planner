"""RED phase test: Test that FAILS demonstrating the def_end_timestep bug.

The bug: def_end_timestep is calculated as min(hours_available, 168) instead
of using fin_ventana from the charging window.

This test will FAIL with current code and PASS after the fix.
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
from custom_components.ev_trip_planner.calculations import (
    calculate_multi_trip_charging_windows,
)


@pytest.mark.asyncio
async def test_def_end_timestep_bug_when_inicio_ventana_equals_hours_available(
    mock_hass, mock_store
):
    """
    When the charging window starts at the same time as the deadline,
    def_start_timestep equals def_end_timestep (both = hours_available).
    This is impossible for charging.

    This test FAILS with current code.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)

    # Scenario: Trip deadline is 96 hours away
    # Charging window starts at hour 90 (6 hours before deadline)
    # But hours_available is 96
    deadline = now + timedelta(hours=96)
    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": deadline.isoformat(),
        "kwh": 21.0,  # 6 hours at 3.6 kW
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    # Car returned recently - charging window starts soon
    hora_regreso = now + timedelta(hours=2)  # Car returns in 2 hours

    # First, let's see what calculate_multi_trip_charging_windows returns
    windows = calculate_multi_trip_charging_windows(
        trips=[(deadline, trip)],
        soc_actual=50.0,
        hora_regreso=hora_regreso,
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        duration_hours=6.0,
        safety_margin_percent=10.0,
    )

    assert len(windows) > 0, "Should have charging windows"
    window = windows[0]

    inicio_ventana = window.get("inicio_ventana")
    fin_ventana = window.get("fin_ventana")

    print(f"\nDEBUG: inicio_ventana = {inicio_ventana}")
    print(f"DEBUG: fin_ventana = {fin_ventana}")
    print(f"DEBUG: fin_ventana type = {type(fin_ventana)}")

    # Calculate what def_start and def_end SHOULD be
    delta_hours_inicio = (inicio_ventana - now).total_seconds() / 3600
    expected_def_start = max(0, min(int(delta_hours_inicio), 168))

    delta_hours_fin = (fin_ventana - now).total_seconds() / 3600
    expected_def_end_raw = delta_hours_fin
    expected_def_end = max(0, min(int(delta_hours_fin), 168))

    print(f"DEBUG: delta_hours_fin (raw) = {expected_def_end_raw}")
    print(f"DEBUG: Expected def_start = {expected_def_start}")
    print(f"DEBUG: Expected def_end = {expected_def_end}")
    print(
        f"DEBUG: Expected window size = {expected_def_end - expected_def_start} hours"
    )

    # Now call the actual code
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
    actual_def_start = params.get("def_start_timestep")
    actual_def_end = params.get("def_end_timestep")

    print(f"DEBUG: Actual def_start = {actual_def_start}")
    print(f"DEBUG: Actual def_end = {actual_def_end}")
    print(f"DEBUG: Actual window size = {actual_def_end - actual_def_start} hours")

    # The bug: def_end is calculated from hours_available, not fin_ventana
    assert actual_def_end == expected_def_end, (
        f"BUG: def_end ({actual_def_end}) should equal {expected_def_end} (calculated from fin_ventana), not hours_available"
    )

    # Also verify window is valid for charging
    def_total_hours = params.get("def_total_hours")
    window_size = actual_def_end - actual_def_start

    assert window_size >= def_total_hours, (
        f"BUG: Window ({window_size}h) too small for {def_total_hours}h charging"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])

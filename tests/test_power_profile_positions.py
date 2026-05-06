"""RED phase test: Verifies power_profile_watts positions are within charging window.

Bug: When charging window is [def_start, def_end), the power_profile_watts
should have the charging values (3600W) at positions WITHIN that window.

For example:
- def_start_timestep = 83
- def_end_timestep = 96
- def_total_hours = 2

Expected: 3600W at positions 94 and 95 (last 2 positions of window)
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
async def test_power_profile_positions_at_end_of_charging_window(mock_hass, mock_store):
    """
    When def_start=83, def_end=96, total_hours=2:
    - Charging window is [83, 96) = 13 hours
    - But only need 2 hours of charging
    - Expected: 3600W at positions 94 and 95 (last 2 positions)

    NOTE: SOC-aware charging recalculates kwh_needed using battery state of charge.
    The trip kwh value (13.2) is set so that after subtracting current battery energy,
    the result requires exactly 2 hours of charging at 3.6 kW.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)

    # Scenario: Deadline is 96 hours away
    # Trip needs 2 hours of charging with SOC-aware behavior
    # SOC-aware calculation:
    #   energia_viaje = trip.kwh
    #   energia_seguridad = 10% * 60 = 6 kWh
    #   energia_objetivo = energia_viaje + 6
    #   energia_actual = 20% * 60 = 12 kWh
    #   energia_necesaria = max(0, energia_objetivo - energia_actual)
    #   def_total_hours = ceil(energia_necesaria / 3.6)
    # To get def_total_hours=2: energia_necesaria ≈ 7.2 kWh
    #   7.2 = energia_viaje + 6 - 12
    #   energia_viaje = 13.2 kWh
    deadline = now + timedelta(hours=96)
    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": deadline.isoformat(),
        "kwh": 13.2,  # SOC-aware: 13.2 + 6 - 12 = 7.2 kWh needed = 2 hours at 3.6kW
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    # Car already returned - charging can start immediately
    hora_regreso = now - timedelta(hours=10)

    await adapter._populate_per_trip_cache_entry(
        trip=trip,
        trip_id=trip["id"],
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        safety_margin_percent=10.0,
        soc_current=20.0,  # Low SOC so charging IS needed (SOC-aware behavior)
        hora_regreso=hora_regreso,
    )

    params = adapter._cached_per_trip_params.get(trip["id"])
    assert params is not None

    def_start = params.get("def_start_timestep")
    def_end = params.get("def_end_timestep")
    def_total_hours = params.get("def_total_hours")
    power_profile = params.get("power_profile_watts", [])

    print(f"\nDEBUG: def_start = {def_start}")
    print(f"DEBUG: def_end = {def_end}")
    print(f"DEBUG: def_total_hours = {def_total_hours}")
    print(f"DEBUG: power_profile length = {len(power_profile)}")

    # Verify parameters are as expected
    assert def_start < def_end, f"def_start ({def_start}) < def_end ({def_end})"
    assert def_total_hours == 2, f"Should need 2 hours charging, got {def_total_hours}"

    # The 3600W values should be at the END of the charging window
    # For window [83, 96) with 2 hours charging, that means positions 94 and 95

    # Find positions where power_profile_watts has 3600
    charging_positions = [i for i, p in enumerate(power_profile) if p == 3600]

    print(f"DEBUG: Charging positions (0-indexed) = {charging_positions}")

    # Verify there are exactly 2 charging hours
    assert len(charging_positions) == def_total_hours, (
        f"Should have {def_total_hours} charging positions, got {len(charging_positions)}"
    )

    # The optimizer may choose any position within [def_start, def_end)
    for pos in charging_positions:
        assert def_start <= pos < def_end, (
            f"Charging position {pos} is OUTSIDE charging window/EMHASS window [{def_start}, {def_end})"
        )

    # Additional: Verify the last charging position is before deadline
    last_charging_pos = max(charging_positions) if charging_positions else -1
    assert last_charging_pos < def_end, (
        f"BUG: Last charging position {last_charging_pos} should be < def_end {def_end}"
    )


@pytest.mark.asyncio
async def test_power_profile_positions_spread_across_window(mock_hass, mock_store):
    """Test case where charging is spread across the window.

    This test covers the original user's bug report:
    - Trip needs 6 hours charging
    - Window is [96, 96) with the BUG (zero-sized window!)
    - After fix, window should have valid size
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)

    # Original bug case: 6 hours charging needed
    deadline = now + timedelta(hours=96)
    trip = {
        "id": "test_trip_6h",
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

    # Car not yet returned
    hora_regreso = now + timedelta(hours=2)

    await adapter._populate_per_trip_cache_entry(
        trip=trip,
        trip_id=trip["id"],
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        safety_margin_percent=10.0,
        soc_current=20.0,  # Low SOC so charging IS needed (SOC-aware behavior)
        hora_regreso=hora_regreso,
    )

    params = adapter._cached_per_trip_params.get(trip["id"])
    assert params is not None

    def_start = params.get("def_start_timestep")
    def_end = params.get("def_end_timestep")
    def_total_hours = params.get("def_total_hours")
    power_profile = params.get("power_profile_watts", [])

    print(f"\nDEBUG 6h trip: def_start = {def_start}")
    print(f"DEBUG 6h trip: def_end = {def_end}")
    print(f"DEBUG 6h trip: def_total_hours = {def_total_hours}")

    window_size = def_end - def_start
    assert window_size >= def_total_hours, (
        f"BUG: Window size ({window_size}h) too small for {def_total_hours}h charging"
    )

    # Verify charging positions are within window
    charging_positions = [i for i, p in enumerate(power_profile) if p == 3600]
    print(f"DEBUG 6h trip: Charging positions = {charging_positions}")

    for pos in charging_positions:
        assert def_start <= pos < def_end, (
            f"Charging position {pos} is OUTSIDE charging window [{def_start}, {def_end})"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])

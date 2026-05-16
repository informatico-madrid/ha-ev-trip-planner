"""Test that power_profile_watts has slots at the END only (not entire window).

BUG: With a single trip where def_start=0 and def_end=51 (51-hour window),
the adapter.py:async_publish_all_deferrable_loads() fills power_profile_watts
with slots for the ENTIRE range [start, end) instead of only def_total_hours
slots at the END of the window.

For a single trip with no hora_regreso:
- def_start = 0 (car is home now)
- def_end = 51 (trip departure at hour 51)
- def_total = 6 (charging takes 6 hours)

CORRECT: Only 6 slots should be non-zero, at positions [45, 46, 47, 48, 49, 50]
BUGGY: All 51 slots from [0..50] are non-zero (entire window filled)

This test verifies the BUG in power_profile_watts that exists in
adapter.py:async_publish_all_deferrable_loads() lines 297-303.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock
import pytest

# Import from integration conftest for mock_hass


@pytest.mark.asyncio
async def test_power_profile_watts_single_trip_compacted_at_end(
    mock_hass,
):
    """Test power_profile_watts with single trip where def_start=0 and def_end=51.
    
    With a single trip and NO hora_regreso:
    - def_start = 0 (car is home now, window starts now at hour 0)
    - def_end = 51 (trip departure at hour 51 from now)
    - def_total = 6 (charging takes 6 hours)
    
    Expected: 6 slots at positions [45, 46, 47, 48, 49, 50] (at END of window)
    Bug: 51 slots at positions [0..50] (entire window filled)
    
    This test uses the coordinator fallback path (_generate_mock_emhass_params)
    which builds power_profile from p_deferrable_matrix rows. Since p_deferrable_matrix
    was FIXED to only have slots at the END, the power_profile from coordinator will
    also be CORRECT (because it takes MAX across matrix rows).
    
    The BUG in power_profile_watts is in adapter.py:async_publish_all_deferrable_loads()
    which has its own code that fills [start, end) instead of using the matrix rows.
    """
    from custom_components.ev_trip_planner.coordinator import CoordinatorConfig, TripPlannerCoordinator
    
    # Create a mock entry
    mock_entry = MagicMock()
    mock_entry.data = {
        "vehicle_name": "test_vehicle",
        "battery_capacity_kwh": 50.0,
        "kwh_per_km": 0.18,
        "planning_horizon_days": 7,
        "charging_power_kw": 7.4,
    }
    mock_entry.options = {"charging_power_kw": 7.4}
    
    # Create a mock trip_manager
    mock_tm = MagicMock()
    mock_tm._crud = MagicMock()
    mock_tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
    mock_tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    mock_tm._soc_query = MagicMock()
    mock_tm._soc_query.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
    mock_tm._soc_query.async_get_hours_needed_today = AsyncMock(return_value=0.0)
    mock_tm._navigator = MagicMock()
    mock_tm._navigator.async_get_next_trip = AsyncMock(return_value=None)
    
    config = CoordinatorConfig(emhass_adapter=None)
    
    # Create coordinator
    coord = TripPlannerCoordinator(
        hass=mock_hass,
        entry=mock_entry,
        trip_manager=mock_tm,
        config=config,
    )
    
    # Create a single trip where:
    # - Trip departs 51 hours from now
    # - Charging takes 6 hours (kwh = 6 * 7.4 = 44.4)
    now = datetime.now(timezone.utc)
    departure = now + timedelta(hours=51)
    departure = departure.replace(minute=0, second=0, microsecond=0)
    
    trips = {
        "trip_1": {
            "id": "trip_1",
            "status": "active",
            "tipo": "punctual",
            "datetime": departure.isoformat(),
            "kwh": 44.4,  # 6 hours * 7.4 kW = 44.4 kWh
            "km": 200,
        }
    }
    
    result = coord._generate_mock_emhass_params(trips)
    
    # Get the power_profile (built from matrix rows)
    power_profile = result["emhass_power_profile"]
    
    params = result["per_trip_emhass_params"]["trip_1"]
    matrix = params["p_deferrable_matrix"]
    row = matrix[0]
    
    def_start = params["def_start_timestep_array"][0]
    def_end = params["def_end_timestep_array"][0]
    def_total = params["def_total_hours_array"][0]
    
    non_zero_count = sum(1 for v in power_profile if v > 0)
    matrix_non_zero = sum(1 for v in row if v > 0)
    
    print("\n=== Test: Single trip with def_start=0 ===")
    print(f"def_start_timestep = {def_start}")
    print(f"def_end_timestep = {def_end}")
    print(f"def_total_hours = {def_total}")
    print(f"power_profile length = {len(power_profile)}")
    print(f"matrix row length = {len(row)}")
    print(f"power_profile non-zero count = {non_zero_count}")
    print(f"matrix row non-zero count = {matrix_non_zero}")
    
    # Show which positions are filled in power_profile
    filled_positions = [i for i, v in enumerate(power_profile) if v > 0]
    print(f"power_profile filled positions: {filled_positions[:10]}..." if len(filled_positions) > 10 else f"power_profile filled positions: {filled_positions}")
    
    # Show which positions are filled in matrix row
    matrix_filled = [i for i, v in enumerate(row) if v > 0]
    print(f"matrix row filled positions: {matrix_filled}")
    
    # For single trip with no hora_regreso:
    # - def_start should be 0 (window starts now)
    # - def_end should be 51 (trip at hour 51)
    # - def_total should be 6 (charging hours)
    # - CORRECT: 6 slots at positions [45, 46, 47, 48, 49, 50] (END of window)
    # - BUGGY: 51 slots at positions [0..50] (entire window)
    
    # First assertion: def_start must be 0 for single trip with no previous trips
    assert def_start == 0, f"def_start should be 0 (car is home now), got {def_start}"
    
    # Second assertion: def_end should be 51 (trip at hour 51)
    assert def_end == 51, f"def_end should be 51, got {def_end}"
    
    # Third assertion: def_total should be 6 (charging takes 6 hours)
    assert def_total == 6, f"def_total should be 6, got {def_total}"
    
    # Fourth assertion: power_profile should have exactly def_total non-zero slots
    # (because coordinator builds power_profile from MAX across matrix rows)
    assert non_zero_count == def_total, (
        f"power_profile should have exactly {def_total} non-zero slots, got {non_zero_count}"
    )
    
    # Fifth assertion: matrix row should have exactly def_total non-zero slots
    assert matrix_non_zero == def_total, (
        f"matrix row should have exactly {def_total} non-zero slots, got {matrix_non_zero}"
    )
    
    # Calculate charging window boundaries
    charging_start = def_end - def_total  # 51 - 6 = 45
    charging_end = def_end  # 51
    
    power_watts = 7400.0  # 7.4 kW * 1000
    
    # ASSERTION: power_profile positions BEFORE charging_start should be 0
    for t in range(0, charging_start):
        assert power_profile[t] == 0, (
            f"power_profile[{t}] should be 0 (before charging window at {charging_start}) "
            f"but is {power_profile[t]}"
        )
    
    # ASSERTION: power_profile positions in [charging_start, charging_end) should have charging power
    for t in range(charging_start, charging_end):
        assert power_profile[t] == power_watts, (
            f"power_profile[{t}] should be {power_watts} (charging power) "
            f"but is {power_profile[t]}"
        )
    
    # ASSERTION: power_profile positions AFTER charging_end should be 0
    for t in range(charging_end, len(power_profile)):
        assert power_profile[t] == 0, (
            f"power_profile[{t}] should be 0 (after charging window at {charging_end}) "
            f"but is {power_profile[t]}"
        )
    
    # ASSERTION: matrix row positions BEFORE charging_start should be 0
    for t in range(0, charging_start):
        assert row[t] == 0, (
            f"matrix row[{t}] should be 0 (before charging window at {charging_start}) "
            f"but is {row[t]}"
        )
    
    # ASSERTION: matrix row positions in [charging_start, charging_end) should have charging power
    for t in range(charging_start, charging_end):
        assert row[t] == power_watts, (
            f"matrix row[{t}] should be {power_watts} (charging power) "
            f"but is {row[t]}"
        )
    
    # ASSERTION: matrix row positions AFTER charging_end should be 0
    for t in range(charging_end, len(row)):
        assert row[t] == 0, (
            f"matrix row[{t}] should be 0 (after charging window at {charging_end}) "
            f"but is {row[t]}"
        )
    
    print(f"\n✓ power_profile correctly compacted to {def_total} slots at positions [{charging_start}, {charging_end})")
    print(f"✓ matrix row correctly compacted to {def_total} slots at positions [{charging_start}, {charging_end})")
    print(f"✓ All {charging_start} positions before charging window are 0")
    print(f"✓ All {len(power_profile) - charging_end} positions after charging window are 0")
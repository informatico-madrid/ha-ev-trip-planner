"""Test that p_deferrable_matrix has only def_total_hours slots at the END.

BUG: With a single trip where def_start=0 and def_end=51 (51-hour window),
the code fills p_deferrable_matrix with 51 slots (range(0,51)) instead of
only def_total_hours=6 slots at the END of the window (range(45,51)).

For a single trip with no hora_regreso:
- def_start = 0 (car is home now, window starts now)
- def_end = 51 (trip departure at hour 51)
- def_total = 6 (charging takes 6 hours)

CORRECT: Only 6 slots should be filled, at positions [45, 46, 47, 48, 49, 50]
BUGGY: All 51 slots are filled at positions [0..50]
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock
import pytest

# Import from integration conftest for mock_hass


@pytest.mark.asyncio
async def test_p_deferrable_matrix_single_trip_def_start_0(
    mock_hass,
):
    """Test p_deferrable_matrix with single trip where def_start=0 and def_end=51.
    
    With a single trip and NO hora_regreso:
    - def_start = 0 (car is home now, window starts now at hour 0)
    - def_end = 51 (trip departure at hour 51 from now)
    - def_total = 6 (charging takes 6 hours)
    
    Expected: 6 slots at positions [45, 46, 47, 48, 49, 50] (at END of window)
    Bug: 51 slots at positions [0..50] (entire window filled)
    
    This test demonstrates that when there's only ONE trip and no hora_regreso,
    the code incorrectly fills the ENTIRE window instead of just the charging
    duration at the END.
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
    params = result["per_trip_emhass_params"]["trip_1"]
    matrix = params["p_deferrable_matrix"]
    row = matrix[0]
    
    def_start = params["def_start_timestep"]
    def_end = params["def_end_timestep"]
    def_total = params["def_total_hours"]
    
    non_zero_count = sum(1 for v in row if v > 0)
    
    print("\n=== Test: Single trip with def_start=0 ===")
    print(f"def_start_timestep = {def_start}")
    print(f"def_end_timestep = {def_end}")
    print(f"def_total_hours = {def_total}")
    print(f"horizon_hours = {len(row)}")
    print(f"Non-zero slots filled: {non_zero_count}")
    
    # Show which positions are filled
    filled_positions = [i for i, v in enumerate(row) if v > 0]
    print(f"Filled positions: {filled_positions[:10]}..." if len(filled_positions) > 10 else f"Filled positions: {filled_positions}")
    
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
    
    # Fourth assertion: only def_total slots should be filled, at END of window
    # The correct positions should be [45, 46, 47, 48, 49, 50]
    
    # Verify positions BEFORE charging_start are 0
    charging_start = def_end - def_total  # 51 - 6 = 45
    charging_end = def_end  # 51
    
    for t in range(0, charging_start):
        assert row[t] == 0, f"Position {t} should be 0 (before charging window) but is {row[t]}"
    
    # Verify positions in [charging_start, charging_end) have charging power
    power_watts = 7400.0  # 7.4 kW * 1000
    for t in range(charging_start, charging_end):
        expected_power = power_watts if t < charging_end else 0
        assert row[t] == expected_power, (
            f"Position {t} should be {expected_power} but is {row[t]}"
        )
    
    # Verify positions AFTER charging_end are 0
    for t in range(charging_end, len(row)):
        assert row[t] == 0, f"Position {t} should be 0 (after charging window) but is {row[t]}"
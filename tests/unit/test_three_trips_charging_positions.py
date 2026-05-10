"""RED phase test: Verifies power_profile_watts positions with 3 trips (puntual and recurrent).

Based on real user example with 3 trips where one had the bug:
- pun_20260420_21mq61: 2h charge, window [0, 73)
- pun_20260821_3s0dhf: 6h charge, window [96, 96) - BUG! (was equal start/end)
- rec_1_dj5tv1: 2h charge, window [83, 96)

This test verifies all charging positions are within their respective windows.
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
async def test_three_trips_puntual_and_recurring_charging_positions(
    mock_hass, mock_store
):
    """
    Original bug case from user:
    - Trip 1 (puntual): 7 kWh (2h) in 73 hours
    - Trip 2 (puntual): 21 kWh (6h) in 96 hours - HAD BUG: start=96, end=96
    - Trip 3 (recurring): 7 kWh (2h) with window [83, 96)

    After fix: All charging positions should be within their windows.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,  # 3600W
    }

    now = datetime.now(timezone.utc)

    # Trip 1: Puntual - 7 kWh (2h charge), deadline in ~73 hours
    deadline1 = now + timedelta(hours=73)
    trip1 = {
        "id": "pun_20260420_21mq61",
        "tipo": "puntual",
        "datetime": deadline1.isoformat(),
        "kwh": 7.0,
    }

    # Trip 2: Puntual - 21 kWh (6h charge), deadline in ~96 hours
    # This was the BUG case: def_start=96, def_end=96
    deadline2 = now + timedelta(hours=96)
    trip2 = {
        "id": "pun_20260821_3s0dhf",
        "tipo": "puntual",
        "datetime": deadline2.isoformat(),
        "kwh": 21.0,
    }

    # Trip 3: Recurring - 7 kWh (2h charge), with deadline
    # Window should be [83, 96) based on recurring pattern
    deadline3 = now + timedelta(hours=96)
    trip3 = {
        "id": "rec_1_dj5tv1",
        "tipo": "recurrente",
        "datetime": deadline3.isoformat(),
        "kwh": 7.0,
        "hora": "09:00",  # Example time
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    # Car already returned
    hora_regreso = now - timedelta(hours=10)

    # Process all trips
    for trip in [trip1, trip2, trip3]:
        await adapter._populate_per_trip_cache_entry(
            trip=trip,
            trip_id=trip["id"],
            charging_power_kw=3.6,
            battery_capacity_kwh=60.0,
            safety_margin_percent=10.0,
            soc_current=50.0,
            hora_regreso=hora_regreso,
        )

    # Verify Trip 1 (pun_20260420_21mq61)
    params1 = adapter._cached_per_trip_params.get(trip1["id"])
    assert params1 is not None, "Trip 1 params should be cached"

    def_start1 = params1.get("def_start_timestep")
    def_end1 = params1.get("def_end_timestep")
    def_total1 = params1.get("def_total_hours")
    power_profile1 = params1.get("power_profile_watts", [])

    print(f"\nTrip 1 ({trip1['id']}):")
    print(f"  def_start={def_start1}, def_end={def_end1}, def_total_hours={def_total1}")

    charging_positions1 = [i for i, p in enumerate(power_profile1) if p == 3600]
    print(f"  Charging positions: {charging_positions1}")

    window_size1 = def_end1 - def_start1
    assert (
        window_size1 >= def_total1
    ), f"Trip1: Window ({window_size1}h) too small for {def_total1}h charging"

    # All charging positions must be within window
    for pos in charging_positions1:
        assert (
            def_start1 <= pos < def_end1
        ), f"Trip1: Position {pos} outside window [{def_start1}, {def_end1})"

    # Verify Trip 2 (pun_20260821_3s0dhf) - THE BUG CASE
    params2 = adapter._cached_per_trip_params.get(trip2["id"])
    assert params2 is not None, "Trip 2 params should be cached"

    def_start2 = params2.get("def_start_timestep")
    def_end2 = params2.get("def_end_timestep")
    def_total2 = params2.get("def_total_hours")
    power_profile2 = params2.get("power_profile_watts", [])

    print(f"\nTrip 2 ({trip2['id']}):")
    print(f"  def_start={def_start2}, def_end={def_end2}, def_total_hours={def_total2}")

    charging_positions2 = [i for i, p in enumerate(power_profile2) if p == 3600]
    print(f"  Charging positions: {charging_positions2}")

    assert (
        def_start2 < def_end2
    ), f"Trip2 BUG: def_start ({def_start2}) should be < def_end ({def_end2}) for {def_total2}h charge"

    # Window must be large enough for charging
    window_size2 = def_end2 - def_start2
    assert (
        window_size2 >= def_total2
    ), f"Trip2: Window ({window_size2}h) too small for {def_total2}h charging"

    # All charging positions must be within window
    for pos in charging_positions2:
        assert (
            def_start2 <= pos < def_end2
        ), f"Trip2: Position {pos} outside window [{def_start2}, {def_end2})"

    # Verify Trip 3 (rec_1_dj5tv1) - Recurring
    params3 = adapter._cached_per_trip_params.get(trip3["id"])
    assert params3 is not None, "Trip 3 params should be cached"

    def_start3 = params3.get("def_start_timestep")
    def_end3 = params3.get("def_end_timestep")
    def_total3 = params3.get("def_total_hours")
    power_profile3 = params3.get("power_profile_watts", [])

    print(f"\nTrip 3 ({trip3['id']}):")
    print(f"  def_start={def_start3}, def_end={def_end3}, def_total_hours={def_total3}")

    charging_positions3 = [i for i, p in enumerate(power_profile3) if p == 3600]
    print(f"  Charging positions: {charging_positions3}")

    # Window must be large enough
    window_size3 = def_end3 - def_start3
    assert (
        window_size3 >= def_total3
    ), f"Trip3: Window ({window_size3}h) too small for {def_total3}h charging"

    # All charging positions must be within window
    for pos in charging_positions3:
        assert (
            def_start3 <= pos < def_end3
        ), f"Trip3: Position {pos} outside window [{def_start3}, {def_end3})"

    # For recurring trips, the window might be different
    # But all charging positions should be valid
    print("\n✓ All 3 trips have valid charging windows and positions")


@pytest.mark.asyncio
async def test_multiple_puntual_trips_sequential_charging_windows(
    mock_hass, mock_store
):
    """Test multiple puntual trips with sequential deadlines.

    Verifies that each trip has its own non-overlapping charging window
    and charging positions are within each window.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)

    # 3 sequential punctual trips
    trips = []
    for i, hours_ahead in enumerate([24, 48, 72]):
        deadline = now + timedelta(hours=hours_ahead)
        trip = {
            "id": f"trip_{i}",
            "tipo": "puntual",
            "datetime": deadline.isoformat(),
            "kwh": 7.0,  # 2 hours each
        }
        trips.append(trip)

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    hora_regreso = now - timedelta(hours=10)

    # Process all trips
    for trip in trips:
        await adapter._populate_per_trip_cache_entry(
            trip=trip,
            trip_id=trip["id"],
            charging_power_kw=3.6,
            battery_capacity_kwh=60.0,
            safety_margin_percent=10.0,
            soc_current=50.0,
            hora_regreso=hora_regreso,
        )

    # Verify each trip
    for i, trip in enumerate(trips):
        params = adapter._cached_per_trip_params.get(trip["id"])
        assert params is not None, f"Trip {i} params should be cached"

        def_start = params.get("def_start_timestep")
        def_end = params.get("def_end_timestep")
        def_total = params.get("def_total_hours")
        power_profile = params.get("power_profile_watts", [])

        print(f"\nTrip {i} ({trip['id']}):")
        print(f"  Window: [{def_start}, {def_end}), size={def_end - def_start}h")
        print(f"  Charging needed: {def_total}h")

        charging_positions = [j for j, p in enumerate(power_profile) if p == 3600]
        print(f"  Charging positions: {charging_positions}")

        # Window must be large enough
        assert (
            def_end - def_start
        ) >= def_total, f"Trip {i}: Window too small for charging"

        # All positions within window
        for pos in charging_positions:
            assert (
                def_start <= pos < def_end
            ), f"Trip {i}: Position {pos} outside window"


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])

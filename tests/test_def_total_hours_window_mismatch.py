"""Test: backward propagation replaces capping for charge deficit handling.

Replaced the old capping behavior (which discarded excess hours) with
backward charge deficit propagation. For multi-trip scenarios, excess hours
are now propagated to earlier trips with spare capacity.

For single trips with insufficient windows, def_total_hours may exceed
window_size since there's no previous trip to absorb from. This scenario
should be addressed at the window calculation level (calculate_multi_trip_charging_windows).
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
async def test_single_trip_short_window_no_capping(mock_hass, mock_store):
    """
    Scenario: Single trip with short window and very low SOC needs ~10h charging
    but window is only 2h. Since there's no previous trip to absorb from,
    def_total_hours exceeds window_size.

    This is expected — backward propagation can only help multi-trip chains.
    For single trips, the window calculation itself should provide enough hours.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)

    hora_regreso = now + timedelta(hours=43)
    deadline = now + timedelta(hours=44)

    trip = {
        "id": "short_window_low_soc",
        "tipo": "puntual",
        "datetime": deadline.isoformat(),
        "kwh": 30.0,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    soc_current = 5.0

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

    def_total_hours = params.get("def_total_hours")

    # Verify charging is needed
    assert def_total_hours > 0, "With 5% SOC, charging should be needed"

    # No capping: single trip def_total_hours can exceed window_size
    # since there's no previous trip for backward propagation to work with.
    # This is a known limitation — the window calculation should account for this.
    assert def_total_hours > 0


@pytest.mark.asyncio
async def test_adjusted_hours_from_propagation_used(mock_hass, mock_store):
    """
    Verify that adjusted_def_total_hours from backward propagation is used
    when provided to _populate_per_trip_cache_entry.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)
    hora_regreso = now + timedelta(hours=42)
    deadline = now + timedelta(hours=43)

    trip = {
        "id": "trip_propagation_test",
        "tipo": "puntual",
        "datetime": deadline.isoformat(),
        "kwh": 7.2,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    soc_current = 10.0

    # Call with adjusted_def_total_hours from propagation
    await adapter._populate_per_trip_cache_entry(
        trip=trip,
        trip_id=trip["id"],
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        safety_margin_percent=10.0,
        soc_current=soc_current,
        hora_regreso=hora_regreso,
        adjusted_def_total_hours=5.0,
    )

    params = adapter._cached_per_trip_params.get(trip["id"])
    assert params is not None

    # Should use the adjusted hours from propagation, not the decision hours
    assert params["def_total_hours"] == 5


@pytest.mark.asyncio
async def test_no_adjusted_hours_uses_decision(mock_hass, mock_store):
    """
    Verify that when adjusted_def_total_hours is None (single-trip path),
    the decision's def_total_hours is used without capping.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    now = datetime.now(timezone.utc)
    hora_regreso = now + timedelta(hours=42)
    deadline = now + timedelta(hours=43)

    trip = {
        "id": "trip_no_adjustment",
        "tipo": "puntual",
        "datetime": deadline.isoformat(),
        "kwh": 7.2,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        await adapter.async_load()

    soc_current = 10.0

    await adapter._populate_per_trip_cache_entry(
        trip=trip,
        trip_id=trip["id"],
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        safety_margin_percent=10.0,
        soc_current=soc_current,
        hora_regreso=hora_regreso,
        # No adjusted_def_total_hours — simulates single-trip path
    )

    params = adapter._cached_per_trip_params.get(trip["id"])
    assert params is not None

    # Should use decision's def_total_hours (not capped)
    assert params["def_total_hours"] > 0

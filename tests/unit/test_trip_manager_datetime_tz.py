"""Regression test: ensure TripManager handles aware datetime objects without raising

This test reproduces the reported TypeError when code subtracts an
offset-naive datetime from an offset-aware datetime. The failing path is
in `async_calcular_energia_necesaria` where `trip['datetime']` may be
a tz-aware datetime that bypasses strptime and then is compared to `dt_util.now()`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_handles_tz_aware_datetime(
    monkeypatch,
) -> None:
    """Calling async_calcular_energia_necesaria with a tz-aware datetime object
    must not raise a TypeError due to naive/aware subtraction.
    """
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # Trip with tz-aware datetime object (not a string)
    # Use a fixed future datetime to ensure hours_available > 0 deterministically
    trip_future_datetime = datetime(2027, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    trip = {"tipo": None, "datetime": trip_future_datetime}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Mock dt_util.now() to a fixed earlier aware datetime for deterministic results.
    # This prevents flakiness when the test runs after the trip's original time.
    from custom_components.ev_trip_planner import trip_manager

    fixed_now = datetime(2026, 12, 1, 8, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(trip_manager.dt_util, "now", lambda: fixed_now)

    # Should complete without raising and return the expected keys
    res = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
    assert isinstance(res, dict)
    assert "energia_necesaria_kwh" in res
    assert "horas_disponibles" in res
    # CRITICAL: assert the trip is viable (hours available > 0)
    # Without this, a past-datetime trip could pass the test while having 0 hours available
    assert res["horas_disponibles"] > 0


@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_naive_datetime_object_succeeds(
    monkeypatch,
) -> None:
    """Test that naive datetime OBJECT is handled successfully after the fix.

    When trip['datetime'] is a bare datetime object (naive, no tzinfo), the
    code path at line 1470-1471 now checks tzinfo and replaces it with UTC.
    """
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # Naive datetime object - NOT a string
    # Use a fixed future naive datetime to ensure deterministic viability
    naive_dt = datetime(2027, 6, 15, 10, 0)
    trip = {"tipo": None, "datetime": naive_dt}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Mock dt_util.now() to a fixed earlier aware datetime for deterministic results
    from custom_components.ev_trip_planner import trip_manager

    fixed_now = datetime(2026, 12, 1, 8, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(trip_manager.dt_util, "now", lambda: fixed_now)

    # Should succeed after the fix
    res = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
    assert isinstance(res, dict)
    assert "energia_necesaria_kwh" in res
    assert "horas_disponibles" in res
    # CRITICAL: assert the trip is viable (hours available > 0)
    assert res["horas_disponibles"] > 0


@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_strptime_naive_datetime_succeeds(
    monkeypatch,
) -> None:
    """Test that string datetime is handled successfully after the fix.

    When trip['datetime'] is a string, dt_util.parse_datetime may return naive
    datetime. The fix now checks tzinfo and replaces it with UTC.
    """
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # String datetime - goes through parse_datetime path
    # Use a fixed future string datetime to ensure deterministic viability
    trip = {"tipo": None, "datetime": "2027-06-15T10:00"}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Mock dt_util.now() to a fixed earlier aware datetime for deterministic results
    from custom_components.ev_trip_planner import trip_manager

    fixed_now = datetime(2026, 12, 1, 8, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(trip_manager.dt_util, "now", lambda: fixed_now)

    # Should succeed after the fix
    res = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
    assert isinstance(res, dict)
    assert "energia_necesaria_kwh" in res
    assert "horas_disponibles" in res
    # CRITICAL: assert the trip is viable (hours available > 0)
    assert res["horas_disponibles"] > 0

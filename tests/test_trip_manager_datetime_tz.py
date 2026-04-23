"""Regression test: ensure TripManager handles trip datetime strings without raising

This test reproduces the reported TypeError when code subtracts an
offset-naive datetime from an offset-aware datetime. The failing path is
in `async_calcular_energia_necesaria` where `trip['datetime']` may be
parsed with `datetime.strptime` (naive) and then compared to `dt_util.now()`
(aware).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datetime import datetime, timezone

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_handles_naive_datetime(monkeypatch) -> None:
    """Calling async_calcular_energia_necesaria with a datetime string
    must not raise a TypeError due to naive/aware subtraction.
    """
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # Trip with datetime as ISO string (no timezone)
    trip = {"tipo": None, "datetime": "2026-04-23T10:00"}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Force dt_util.now() to return an aware datetime (UTC) to reproduce
    # the runtime environment where naive/aware subtraction would fail.
    from custom_components.ev_trip_planner import trip_manager

    monkeypatch.setattr(trip_manager.dt_util, "now", lambda: datetime.now(timezone.utc))

    # Should complete without raising and return the expected keys
    res = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
    assert isinstance(res, dict)
    assert "energia_necesaria_kwh" in res
    assert "horas_disponibles" in res


@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_naive_datetime_object_succeeds(monkeypatch) -> None:
    """Test that naive datetime OBJECT is handled successfully after the fix.

    When trip['datetime'] is a bare datetime object (naive, no tzinfo), the
    code path at line 1470-1471 now checks tzinfo and replaces it with UTC.
    """
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # Naive datetime object - NOT a string
    naive_dt = datetime(2026, 4, 23, 10, 0)
    trip = {"tipo": None, "datetime": naive_dt}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Only mock dt_util.now — do NOT mock parse_datetime
    from custom_components.ev_trip_planner import trip_manager

    monkeypatch.setattr(
        trip_manager.dt_util, "now", lambda: datetime.now(timezone.utc)
    )

    # Should succeed after the fix
    res = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
    assert isinstance(res, dict)
    assert "energia_necesaria_kwh" in res
    assert "horas_disponibles" in res


@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_strptime_naive_datetime_succeeds(monkeypatch) -> None:
    """Test that string datetime is handled successfully after the fix.

    When trip['datetime'] is a string, dt_util.parse_datetime may return naive
    datetime. The fix now checks tzinfo and replaces it with UTC.
    """
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # String datetime - goes through parse_datetime path
    trip = {"tipo": None, "datetime": "2026-04-23T10:00"}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Only mock dt_util.now — NOT parse_datetime
    from custom_components.ev_trip_planner import trip_manager

    monkeypatch.setattr(
        trip_manager.dt_util, "now", lambda: datetime.now(timezone.utc)
    )

    # Should succeed after the fix
    res = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
    assert isinstance(res, dict)
    assert "energia_necesaria_kwh" in res
    assert "horas_disponibles" in res

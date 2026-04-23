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
async def test_async_calcular_energia_necesaria_raises_typeerror_on_naive_datetime_object(monkeypatch) -> None:
    """Calling async_calcular_energia_necesaria with a naive datetime OBJECT
    raises TypeError (line 1470-1471: no tz check on datetime object).

    This test uses pytest.raises to assert the TypeError IS raised when
    a naive datetime object is passed — the BUG LOCATION at
    trip_manager.py:1470-1471.

    In the RED phase (before fix): test FAILS because the TypeError
    is caught internally at line 1485 instead of being re-raised.
    After fix: the function should propagate the TypeError.
    """
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # Trip with NAIVE datetime OBJECT (no tzinfo) — triggers bug at line 1470-1471
    from datetime import datetime as dt

    naive_dt = dt(2026, 4, 23, 10, 0)
    trip = {"tipo": None, "datetime": naive_dt}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Force dt_util.now() to return an aware datetime (UTC) to reproduce
    # the runtime environment where naive/aware subtraction would fail.
    from custom_components.ev_trip_planner import trip_manager

    monkeypatch.setattr(trip_manager.dt_util, "now", lambda: dt.now(timezone.utc))

    # RED phase: assert TypeError IS raised when naive datetime object is passed
    with pytest.raises(TypeError):
        await tm.async_calcular_energia_necesaria(trip, vehicle_config)

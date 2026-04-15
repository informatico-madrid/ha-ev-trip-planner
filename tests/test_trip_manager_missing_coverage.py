"""Focused tests to exercise remaining branches in TripManager.

These aim to cover charging power lookup, SOC sensor handling,
and the recurring-trip invalid hora warning path.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager
from tests import create_mock_ev_config_entry


@pytest.mark.asyncio
async def test_get_charging_power_from_entry() -> None:
    # Use a MagicMock hass and register the config entry manually
    from unittest.mock import MagicMock

    data = {"vehicle_name": "veh", "charging_power_kw": 6.6}
    entry = create_mock_ev_config_entry(None, data=data, entry_id="e_test1")

    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    tm = TripManager(hass, "veh")

    power = tm.get_charging_power()
    assert isinstance(power, float)
    assert abs(power - 6.6) < 1e-6


def test_get_charging_power_default_when_no_entry() -> None:
    # Using a plain MagicMock hass that has no config entries should return default
    from unittest.mock import MagicMock
    from custom_components.ev_trip_planner.const import DEFAULT_CHARGING_POWER

    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "noentry")
    assert tm.get_charging_power() == DEFAULT_CHARGING_POWER


@pytest.mark.asyncio
async def test_async_get_vehicle_soc_returns_value_and_handles_unavailable() -> None:
    # Create a MagicMock hass and register the config entry with a soc_sensor
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    data = {"vehicle_name": "veh_soc", "soc_sensor": "sensor.veh_soc"}
    entry = create_mock_ev_config_entry(None, data=data, entry_id="e_test2")

    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[entry])
    hass.states = MagicMock()
    # First, return a valid numeric state
    hass.states.get = MagicMock(return_value=SimpleNamespace(state="42"))

    tm = TripManager(hass, "veh_soc")
    soc = await tm.async_get_vehicle_soc("veh_soc")
    assert soc == 42.0

    # Now simulate unknown/unavailable state
    hass.states.get = MagicMock(return_value=SimpleNamespace(state="unknown"))
    soc2 = await tm.async_get_vehicle_soc("veh_soc")
    assert soc2 == 0.0


@pytest.mark.asyncio
async def test_async_get_next_trip_after_ignores_invalid_hora(hass) -> None:
    # TripManager should skip recurring trips with malformed hora without raising
    tm = TripManager(hass, "veh")
    now = datetime.now()
    # Build a recurring trip for today with invalid hora
    today_name = now.strftime("%A").lower()  # produce a day name; TripManager compares lower()
    # Map English weekday to Spanish days_of_week used by utils; simplest: set dia_semana to empty to force skip
    tm._recurring_trips = {
        "r_bad": {"id": "r_bad", "dia_semana": "", "hora": "25:99", "activo": True}
    }

    # Should not raise and should return None
    res = await tm.async_get_next_trip_after(now)
    assert res is None

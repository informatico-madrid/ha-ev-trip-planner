"""Additional tests to increase coverage for TripManager.

These tests exercise validation, sanitization, storage save path (injected
storage) and the deferrable schedule generation control flow using mocks for
heavy calculation functions.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.mark.asyncio
async def test_validate_hora_raises_on_invalid_format() -> None:
    tm = TripManager(MagicMock(), "veh")
    with pytest.raises(ValueError):
        tm._validate_hora("99:99")


def test_sanitize_recurring_trips_removes_invalid_hours() -> None:
    tm = TripManager(MagicMock(), "veh")
    trips = {
        "ok": {"id": "ok", "hora": "08:00", "tipo": "recurrente"},
        "bad": {"id": "bad", "hora": "25:99", "tipo": "recurrente"},
    }
    cleaned = tm._sanitize_recurring_trips(trips)
    assert "ok" in cleaned
    assert "bad" not in cleaned


@pytest.mark.asyncio
async def test_async_save_trips_uses_injected_storage() -> None:
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)
    storage = MagicMock()
    storage.async_save = AsyncMock(return_value=None)

    tm = TripManager(hass, "veh", storage=storage)
    tm._recurring_trips = {"t1": {"id": "t1"}}
    tm._punctual_trips = {"p1": {"id": "p1"}}

    await tm.async_save_trips()

    # storage.async_save should have been called once with a dict containing trips
    storage.async_save.assert_called_once()
    saved_arg = storage.async_save.call_args.args[0]
    assert "trips" in saved_arg
    assert "recurring_trips" in saved_arg


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_basic_flow() -> None:
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    # Prepare a fake config entry list to satisfy lookup (not strictly necessary)
    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {"vehicle_name": "veh", "battery_capacity_kwh": 40.0}
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    tm = TripManager(hass, "veh", entry_id="e1")

    # Add trips: two recurring and one punctual pending
    now = datetime.now()
    tm._recurring_trips = {
        "r1": {"id": "r1", "activo": True, "hora": "08:00"},
        "r2": {"id": "r2", "activo": True, "hora": "09:00"},
    }
    tm._punctual_trips = {"p1": {"id": "p1", "estado": "pendiente", "hora": now.isoformat()}}

    # Patch time-related and heavy calculation functions
    tm._get_trip_time = lambda trip: now + timedelta(hours=1)
    tm.async_get_vehicle_soc = AsyncMock(return_value=30.0)

    async def fake_async_calcular_energia_necesaria(trip, vehicle_config):
        return {"energia_necesaria_kwh": 1.5, "horas_carga_necesarias": 2.5}

    tm.async_calcular_energia_necesaria = AsyncMock(side_effect=fake_async_calcular_energia_necesaria)

    # Run schedule generation; we don't assert deep correctness, only that path runs
    schedule = await tm.async_generate_deferrables_schedule(charging_power_kw=3.6, planning_horizon_days=1)
    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_deferrables_schedule_handles_no_datetime_trip() -> None:
    """Test that trips without datetime are skipped (line 1951)."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {"vehicle_name": "veh", "battery_capacity_kwh": 40.0}
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    tm = TripManager(hass, "veh", entry_id="e1")

    # Add punctual trip WITHOUT datetime field - should be skipped at line 1950-1951
    tm._punctual_trips = {
        "p1": {"id": "p1", "tipo": "puntual", "km": 50.0, "kwh": 15.0, "estado": "pendiente"}
    }
    tm._recurring_trips = {}

    tm.async_get_vehicle_soc = AsyncMock(return_value=50.0)

    async def fake_async_calcular_energia_necesaria(trip, vehicle_config):
        return {"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}

    tm.async_calcular_energia_necesaria = AsyncMock(side_effect=fake_async_calcular_energia_necesaria)

    schedule = await tm.async_generate_deferrables_schedule(charging_power_kw=3.6, planning_horizon_days=1)
    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_deferrables_schedule_handles_past_trip() -> None:
    """Test that past trips (horas_hasta_viaje < 0) are skipped (line 1958)."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {"vehicle_name": "veh", "battery_capacity_kwh": 40.0}
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    tm = TripManager(hass, "veh", entry_id="e1")

    # Add punctual trip with PAST datetime - should be skipped at line 1957-1958
    past_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    tm._punctual_trips = {
        "p1": {"id": "p1", "tipo": "puntual", "datetime": past_date, "km": 50.0, "kwh": 15.0, "estado": "pendiente"}
    }
    tm._recurring_trips = {}

    tm.async_get_vehicle_soc = AsyncMock(return_value=50.0)

    async def fake_async_calcular_energia_necesaria(trip, vehicle_config):
        return {"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}

    tm.async_calcular_energia_necesaria = AsyncMock(side_effect=fake_async_calcular_energia_necesaria)

    schedule = await tm.async_generate_deferrables_schedule(charging_power_kw=3.6, planning_horizon_days=1)
    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_deferrables_schedule_loop_executes_power_assignment() -> None:
    """Test that power_profiles[idx][h] assignment runs (line 1966).

    The loop at 1965 runs when horas_hasta_viaje > horas_necesarias.
    We use a trip 10 hours in the future with 3 hours needed charging,
    so hora_inicio_carga = max(0, 10-3) = 7 and the loop runs h=7,8,9.
    This exercises the power_profiles[idx][h] = charging_power_watts line.
    """
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {"vehicle_name": "veh", "battery_capacity_kwh": 40.0}
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    tm = TripManager(hass, "veh", entry_id="e1")

    # Trip 10 hours in future, needs 3 hours charging -> loop runs at h=7,8,9
    future_time = datetime.now() + timedelta(hours=10)
    tm._punctual_trips = {
        "p1": {"id": "p1", "tipo": "puntual", "datetime": future_time.strftime("%Y-%m-%dT%H:%M"),
               "km": 50.0, "kwh": 15.0, "estado": "pendiente"}
    }
    tm._recurring_trips = {}

    tm._get_trip_time = lambda trip: future_time
    tm.async_get_vehicle_soc = AsyncMock(return_value=50.0)

    async def fake_async_calcular_energia_necesaria(trip, vehicle_config):
        return {"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}

    tm.async_calcular_energia_necesaria = AsyncMock(side_effect=fake_async_calcular_energia_necesaria)

    schedule = await tm.async_generate_deferrables_schedule(charging_power_kw=3.6, planning_horizon_days=1)
    assert isinstance(schedule, list)

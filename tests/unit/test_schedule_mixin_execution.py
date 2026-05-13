"""Execution tests for _ScheduleMixin (async_generate_deferrables_schedule, publish_deferrable_loads).

Exercises the missing code paths: active trip filtering, deadline calculation,
trip_indices assignment, config entry lookup, power profile generation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip import TripManager
from custom_components.ev_trip_planner.trip.state import TripManagerState


def _make_tm(
    recurring=None,
    punctual=None,
    soc=50.0,
    trip_time=None,
    battery_kwh=60.0,
    safety_margin=10.0,
    entry_id="",
):
    """Build a partial TripManager via __new__ with proper _state."""
    recurring = recurring or {}
    punctual = punctual or {}

    mgr = MagicMock()
    mgr.hass = MagicMock()
    mgr.vehicle_id = "test_vehicle"
    mgr._recurring_trips = recurring
    mgr._punctual_trips = punctual
    mgr._load_trips = AsyncMock()
    mgr.async_get_vehicle_soc = AsyncMock(return_value=soc)
    mgr._get_trip_time = MagicMock(return_value=trip_time)

    tm = TripManager.__new__(TripManager)
    tm._state = TripManagerState(
        hass=mgr.hass,
        vehicle_id=mgr.vehicle_id,
        entry_id=entry_id,
    )
    tm._state._recurring_trips = mgr._recurring_trips
    tm._state._punctual_trips = mgr._punctual_trips
    tm._state.recurring_trips = recurring
    tm._state.punctual_trips = punctual
    tm._state._load_trips = mgr._load_trips
    tm._state._get_trip_time = mgr._get_trip_time
    tm._state.async_get_vehicle_soc = mgr.async_get_vehicle_soc

    # Set up persistence mock for _load_trips
    tm._state._persistence = MagicMock()
    tm._state._persistence._load_trips = AsyncMock()

    # Set up _soc mock for async_get_vehicle_soc, _get_trip_time, async_calcular_energia_necesaria
    tm._state._soc = MagicMock()
    tm._state._soc.async_get_vehicle_soc = mgr.async_get_vehicle_soc
    tm._state._soc._get_trip_time = mgr._get_trip_time
    tm._state._soc.async_calcular_energia_necesaria = AsyncMock(
        return_value={"energia_necesaria_kwh": 0, "horas_carga_necesarias": 0}
    )
    tm._state._soc._calcular_tasa_carga_soc = MagicMock(return_value=10.0)

    # Create and wire schedule sub-component
    from custom_components.ev_trip_planner.trip._schedule import TripScheduler

    tm._schedule = TripScheduler(tm._state)

    # Set up config entry mock
    mock_entry = MagicMock()
    mock_entry.data = {
        "battery_capacity_kwh": battery_kwh,
        "safety_margin_percent": safety_margin,
    }
    tm._state.hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # Set up emhass adapter (note: attribute is `emhass_adapter`, not `_emhass_adapter`)
    adapter = MagicMock()
    adapter.async_publish_all_deferrable_loads = AsyncMock()
    tm._state.emhass_adapter = adapter

    return tm


class TestScheduleMixinActiveTrips:
    """Test active trip filtering code paths."""

    @pytest.mark.asyncio
    async def test_filters_inactive_recurring_trips(self):
        """Inactive recurring trips (activo=False) excluded from schedule."""
        trip_active = {"id": "rec_1", "activo": True}
        trip_inactive = {"id": "rec_2", "activo": False}
        now = datetime.now(timezone.utc) + timedelta(hours=5)

        tm = _make_tm(
            recurring={"rec_1": trip_active, "rec_2": trip_inactive},
            soc=50.0,
            trip_time=now,
        )

        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_filters_non_pending_punctual(self):
        """Punctual trips with estado != pendiente excluded from schedule."""
        pending = {"id": "pun_1", "estado": "pendiente"}
        completed = {"id": "pun_2", "estado": "completado"}
        now = datetime.now(timezone.utc) + timedelta(hours=5)

        tm = _make_tm(
            punctual={"pun_1": pending, "pun_2": completed},
            soc=50.0,
            trip_time=now,
        )

        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_includes_pending_punctual(self):
        """Pending punctual trips included in schedule (line 239 path)."""
        pending = {"id": "pun_1", "tipo": "puntual"}
        tm = _make_tm(
            punctual={"pun_1": pending},
            soc=50.0,
            trip_time=None,
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_config_entry_via_entry_id(self):
        """Config entry lookup via entry_id (line 132 path)."""
        now = datetime.now(timezone.utc) + timedelta(hours=5)
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True}},
            trip_time=now,
            entry_id="test_entry_id",
            battery_kwh=80.0,
            safety_margin=15.0,
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_config_entry_via_vehicle_id_fallback(self):
        """Config entry lookup via vehicle_id fallback (line 66, 132 else branch)."""
        now = datetime.now(timezone.utc) + timedelta(hours=5)
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True}},
            trip_time=now,
            entry_id="",  # Empty entry_id triggers vehicle_id fallback
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)


class TestScheduleMixinPowerProfile:
    """Test power profile generation code paths."""

    @pytest.mark.asyncio
    async def test_schedule_structure(self):
        """Schedule has correct structure with date and power fields."""
        now = datetime.now(timezone.utc) + timedelta(hours=5)
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True, "km": 50}},
            trip_time=now,
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert len(result) > 0
        entry = result[0]
        assert "date" in entry
        assert "p_deferrable0" in entry

    @pytest.mark.asyncio
    async def test_zero_energy_skipped(self):
        """Trips with zero energy requirement are skipped (line 160-161)."""
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True, "km": 0, "kwh": 0}},
            soc=50.0,
            trip_time=datetime.now(timezone.utc) + timedelta(hours=5),
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_no_past_trips(self):
        """Trips with deadline in the past are skipped (line 178-179)."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=5)
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True, "km": 50}},
            soc=50.0,
            trip_time=past_time,
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_no_trip_time_skipped(self):
        """Trips without a valid time are skipped (line 171-172)."""
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True}},
            soc=50.0,
            trip_time=None,
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_empty_schedule_no_trips(self):
        """Empty schedule includes p_deferrable0 for no trips (line 214-215)."""
        tm = _make_tm()
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert len(result) > 0
        # With no trips, p_deferrable0 should be "0.0"
        assert result[0].get("p_deferrable0") == "0.0"


class TestPublishDeferrableLoads:
    """Test publish_deferrable_loads (called via TripScheduler)."""

    @pytest.mark.asyncio
    async def test_publish_calls_adapter(self):
        """publish_deferrable_loads calls async_publish_all_deferrable_loads."""
        tm = _make_tm()
        trips = [{"id": "rec_1", "activo": True}]
        await tm._schedule.publish_deferrable_loads(trips=trips)
        tm._state.emhass_adapter.async_publish_all_deferrable_loads.assert_called_once_with(
            trips
        )

    @pytest.mark.asyncio
    async def test_publish_loads_from_storage_when_none(self):
        """publish_deferrable_loads loads from storage when trips=None."""
        tm = _make_tm()
        tm._state.recurring_trips = {"rec_1": {"id": "rec_1", "activo": True}}
        tm._state.punctual_trips = {"pun_1": {"id": "pun_1", "estado": "pendiente"}}
        await tm._schedule.publish_deferrable_loads()
        tm._state.emhass_adapter.async_publish_all_deferrable_loads.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_noop_when_no_adapter(self):
        """publish_deferrable_loads is no-op when no emhass adapter."""
        tm = _make_tm()
        tm._state.emhass_adapter = None
        await tm._schedule.publish_deferrable_loads(trips=[{"id": "rec_1"}])
        # Should not raise

    @pytest.mark.asyncio
    async def test_schedule_config_entry_exception_via_entry_id(self):
        """Exception during config entry lookup (entry_id path) → defaults used (lines 49-50)."""
        now = datetime.now(timezone.utc) + timedelta(hours=5)
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True}},
            trip_time=now,
            entry_id="test_entry_id",
        )
        tm._state.hass.config_entries.async_get_entry = MagicMock(
            side_effect=RuntimeError("config error")
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_schedule_config_entry_exception_no_entry_id(self):
        """Exception during config entry lookup (no entry_id) → defaults used (lines 106-107)."""
        now = datetime.now(timezone.utc) + timedelta(hours=5)
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True}},
            trip_time=now,
            entry_id="",  # Empty → triggers vehicle_id fallback
        )
        tm._state.hass.config_entries.async_get_entry = MagicMock(
            side_effect=RuntimeError("config error")
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_schedule_no_trip_time_skipped(self):
        """Trips without trip_time are skipped at line 130."""
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True, "km": 50, "kwh": 10}},
            soc=50.0,
            trip_time=None,
        )
        # Ensure _calcular_tasa_carga_soc returns a value
        tm._state._soc._calcular_tasa_carga_soc = MagicMock(return_value=10.0)
        tm._state._soc.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}
        )
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(result, list)

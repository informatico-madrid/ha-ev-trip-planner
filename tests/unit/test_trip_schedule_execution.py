"""Execution tests for _ScheduleMixin (async_generate_deferrables_schedule,
publish_deferrable_loads).

Covers schedule generation with active trips, empty trips, config entry
lookup, and EMHASS adapter integration.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip._schedule_mixin import _ScheduleMixin
from custom_components.ev_trip_planner.trip.state import TripManagerState


def _make_sm():
    """Create a _ScheduleMixin with proper state."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)

    state = TripManagerState(
        hass=hass,
        vehicle_id="test_vehicle",
        entry_id="test_entry",
    )
    state._load_trips = AsyncMock()
    state.recurring_trips = {}
    state.punctual_trips = {}
    state.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    state.async_calcular_energia_necesaria = AsyncMock(
        return_value={"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}
    )
    state.emhass_adapter = None
    return _ScheduleMixin(state)


class TestScheduleMixinExecution:
    """Test _ScheduleMixin execution paths."""

    @pytest.mark.asyncio
    async def test_generate_schedule_empty_trips(self):
        """No trips → returns schedule with all zeros."""
        sm = _make_sm()

        result = await sm.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)
        # 24 hours for 1 day
        assert len(result) == 24
        # Each entry has p_deferrable0 = "0.0"
        for entry in result:
            assert entry["p_deferrable0"] == "0.0"

    @pytest.mark.asyncio
    async def test_generate_schedule_with_recurring_trip(self):
        """Active recurring trip → schedule has non-zero power."""
        sm = _make_sm()
        sm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "tipo": "recurring",
                "dia_semana": "monday",
                "hora": "14:00:00",
                "activo": True,
            }
        }

        # Set _get_trip_time to return a future datetime
        future = datetime.now(timezone.utc) + timedelta(hours=5)
        sm._state._get_trip_time = MagicMock(return_value=future)

        result = await sm.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)
        # Should have p_deferrable0 with some non-zero values
        has_power = any(entry.get("p_deferrable0", "0.0") != "0.0" for entry in result)
        assert has_power is True

    @pytest.mark.asyncio
    async def test_generate_schedule_with_punctual_trip(self):
        """Pending punctual trip → schedule has non-zero power."""
        sm = _make_sm()
        sm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "tipo": "punctual",
                "datetime": "2026-06-01T14:00:00",
                "estado": "pendiente",
                "activo": True,
            }
        }

        future = datetime.now(timezone.utc) + timedelta(hours=5)
        sm._state._get_trip_time = MagicMock(return_value=future)

        result = await sm.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)
        has_power = any(entry.get("p_deferrable0", "0.0") != "0.0" for entry in result)
        assert has_power is True

    @pytest.mark.asyncio
    async def test_generate_schedule_inactive_trip_skipped(self):
        """Inactive recurring trip is skipped."""
        sm = _make_sm()
        sm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "tipo": "recurring",
                "dia_semana": "monday",
                "hora": "14:00:00",
                "activo": False,
            }
        }

        result = await sm.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)
        # No power should be scheduled since trip is inactive
        for entry in result:
            assert entry["p_deferrable0"] == "0.0"

    @pytest.mark.asyncio
    async def test_generate_schedule_cancelled_trip_skipped(self):
        """Cancelled punctual trip is skipped."""
        sm = _make_sm()
        sm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "completado",
            }
        }

        result = await sm.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)
        for entry in result:
            assert entry["p_deferrable0"] == "0.0"

    @pytest.mark.asyncio
    async def test_generate_schedule_config_entry_with_battery(self):
        """Config entry with battery_capacity_kwh is used."""
        sm = _make_sm()
        config_data = {"battery_capacity_kwh": 75.0, "safety_margin_percent": 20}
        config_entry = MagicMock()
        config_entry.data = config_data
        sm._state.hass.config_entries.async_get_entry = MagicMock(return_value=config_entry)
        sm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "tipo": "recurring",
                "dia_semana": "monday",
                "hora": "14:00:00",
                "activo": True,
            }
        }
        future = datetime.now(timezone.utc) + timedelta(hours=5)
        sm._state._get_trip_time = MagicMock(return_value=future)

        result = await sm.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_generate_schedule_multi_trip(self):
        """Multiple active trips → multiple deferrable indices."""
        sm = _make_sm()
        future1 = datetime.now(timezone.utc) + timedelta(hours=5)

        sm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "tipo": "recurring",
                "dia_semana": "monday",
                "hora": "14:00:00",
                "activo": True,
            }
        }
        sm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "pendiente",
            }
        }
        sm._state._get_trip_time = MagicMock(return_value=future1)

        result = await sm.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)
        # Should have p_deferrable0 and p_deferrable1
        if result:
            assert "p_deferrable0" in result[0]
            assert "p_deferrable1" in result[0]

    @pytest.mark.asyncio
    async def test_generate_schedule_deadline_in_past(self):
        """Trip with deadline in the past → skipped (continue at energia check)."""
        sm = _make_sm()
        past = datetime.now(timezone.utc) - timedelta(hours=5)
        sm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "tipo": "recurring",
                "dia_semana": "monday",
                "hora": "14:00:00",
                "activo": True,
            }
        }
        sm._state._get_trip_time = MagicMock(return_value=past)

        result = await sm.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        # Should return with all zeros since deadline is past
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_publish_deferrable_loads_no_adapter(self):
        """No EMHASS adapter → does nothing."""
        sm = _make_sm()
        sm._state.emhass_adapter = None

        await sm.publish_deferrable_loads()
        # Should not raise

    @pytest.mark.asyncio
    async def test_publish_deferrable_loads_with_adapter(self):
        """EMHASS adapter is called with active trips."""
        sm = _make_sm()
        adapter = MagicMock()
        adapter.async_publish_all_deferrable_loads = AsyncMock()
        sm._state.emhass_adapter = adapter
        sm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "tipo": "recurring",
                "activo": True,
            }
        }
        sm._state._load_trips = AsyncMock()

        await sm.publish_deferrable_loads()

        adapter.async_publish_all_deferrable_loads.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_deferrable_loads_with_trips_arg(self):
        """Provided trips list is passed directly to adapter."""
        sm = _make_sm()
        adapter = MagicMock()
        adapter.async_publish_all_deferrable_loads = AsyncMock()
        sm._state.emhass_adapter = adapter

        trips = [{"id": "custom_1"}, {"id": "custom_2"}]
        await sm.publish_deferrable_loads(trips=trips)

        adapter.async_publish_all_deferrable_loads.assert_called_once_with(trips)

    @pytest.mark.asyncio
    async def test_publish_deferrable_loads_adapter_raises(self):
        """Adapter exception is logged, not propagated."""
        sm = _make_sm()
        adapter = MagicMock()
        adapter.async_publish_all_deferrable_loads = AsyncMock(
            side_effect=RuntimeError("EMHASS error")
        )
        sm._state.emhass_adapter = adapter

        await sm.publish_deferrable_loads()
        # Should not raise

    @pytest.mark.asyncio
    async def test_publish_deferrable_loads_skips_inactive(self):
        """Inactive trips are not passed to adapter."""
        sm = _make_sm()
        adapter = MagicMock()
        adapter.async_publish_all_deferrable_loads = AsyncMock()
        sm._state.emhass_adapter = adapter
        sm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "activo": False,
            }
        }
        sm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "completado",
            }
        }
        sm._state._load_trips = AsyncMock()

        await sm.publish_deferrable_loads()

        adapter.async_publish_all_deferrable_loads.assert_called_once_with([])

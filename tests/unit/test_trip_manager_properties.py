"""Execution tests for TripManager properties and method delegation.

Covers vehicle_controller, vehicle_id, hass, _entry_id, _sensor_callbacks,
_get_all_active_trips, async_get_next_trip, async_get_next_trip_after,
async_setup, _load_trips, and emhass_adapter property.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip.manager import TripManager
from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage


def _make_tm():
    """Create a minimal TripManager with proper state."""
    hass = MagicMock()
    hass.config_entries = MagicMock()

    storage = MagicMock(spec=YamlTripStorage)
    storage.load_recurring = MagicMock(return_value={})
    storage.load_punctual = MagicMock(return_value={})

    tm = TripManager(
        hass=hass,
        vehicle_id="test_vehicle",
        entry_id="test_entry",
        storage=storage,
    )
    # Bind method references on state (as TripManager.__init__ does)
    tm._state._validate_hora = tm._validate_hora
    tm._state._is_trip_today = tm._is_trip_today
    tm._state._parse_trip_datetime = tm._parse_trip_datetime
    tm._state._get_charging_power = tm._get_charging_power
    tm._state._sanitize_recurring_trips = tm._sanitize_recurring_trips
    tm._state.async_get_vehicle_soc = tm._soc.async_get_vehicle_soc
    tm._state.async_calcular_energia_necesaria = tm._soc.async_calcular_energia_necesaria
    tm._state._get_trip_time = tm._soc._get_trip_time
    tm._state._get_day_index = tm._soc._get_day_index
    return tm


class TestTripManagerProperties:
    """Test TripManager property accessors."""

    def test_hass_property_from_state(self):
        """hass property returns _state.hass when state exists."""
        tm = _make_tm()
        assert tm.hass is not None

    def test_hass_setter_updates_state(self):
        """Setting hass updates _state.hass."""
        tm = _make_tm()
        new_hass = MagicMock()
        tm.hass = new_hass
        assert tm._state.hass is new_hass

    def test_vehicle_id_property(self):
        """vehicle_id property returns _state.vehicle_id."""
        tm = _make_tm()
        assert tm.vehicle_id == "test_vehicle"

    def test_vehicle_id_setter(self):
        """Setting vehicle_id updates _state.vehicle_id."""
        tm = _make_tm()
        tm.vehicle_id = "new_vehicle"
        assert tm._state.vehicle_id == "new_vehicle"

    def test_entry_id_property(self):
        """_entry_id property returns _state.entry_id."""
        tm = _make_tm()
        assert tm._entry_id == "test_entry"

    def test_sensor_callbacks_property(self):
        """_sensor_callbacks property returns _state.sensor_callbacks."""
        tm = _make_tm()
        assert tm._sensor_callbacks is not None

    def test_emhass_adapter_property(self):
        """_emhass_adapter property returns _state.emhass_adapter."""
        tm = _make_tm()
        assert tm._emhass_adapter is None

    def test_vehicle_controller_property(self):
        """vehicle_controller property returns _state.vehicle_controller."""
        tm = _make_tm()
        assert tm.vehicle_controller is not None


class TestTripManagerMethods:
    """Test TripManager method delegation paths."""

    def test_get_day_index_spanish(self):
        """_get_day_index finds Spanish day names."""
        tm = _make_tm()
        assert tm._get_day_index("lunes") == 0
        assert tm._get_day_index("viernes") == 4

    def test_get_day_index_unknown(self):
        """Unknown day name returns 0 with warning."""
        tm = _make_tm()
        result = tm._get_day_index("notaday")
        assert result == 0

    def test_sanitize_recurring_trips_clean(self):
        """Clean trips pass through unchanged."""
        tm = _make_tm()
        trips = {
            "rec_1": {"hora": "14:00"},
            "rec_2": {"hora": "22:00"},
        }
        result = tm._sanitize_recurring_trips(trips)
        assert len(result) == 2

    def test_sanitize_recurring_trips_invalid(self):
        """Invalid hora is removed from trips."""
        tm = _make_tm()
        trips = {
            "rec_1": {"hora": "invalid"},
            "rec_2": {"hora": "14:00"},
        }
        result = tm._sanitize_recurring_trips(trips)
        assert len(result) < 2

    @pytest.mark.asyncio
    async def test_get_all_active_trips(self):
        """_get_all_active_trips combines active recurring + pending punctual."""
        tm = _make_tm()
        tm._state.recurring_trips = {
            "rec_1": {"id": "rec_1", "activo": True, "tipo": "recurring"},
            "rec_2": {"id": "rec_2", "activo": False, "tipo": "recurring"},
        }
        tm._state.punctual_trips = {
            "pun_1": {"id": "pun_1", "estado": "pendiente"},
            "pun_2": {"id": "pun_2", "estado": "completado"},
        }

        result = await tm._get_all_active_trips()
        assert len(result) == 2  # rec_1 + pun_1

    @pytest.mark.asyncio
    async def test_async_setup(self):
        """async_setup calls _crud.async_setup."""
        tm = _make_tm()
        tm._crud.async_setup = AsyncMock()

        await tm.async_setup()

        tm._crud.async_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_trips_fallback(self):
        """_load_trips falls back to empty dict on storage error."""
        tm = _make_tm()
        tm._state.storage.load_recurring = MagicMock(side_effect=RuntimeError("error"))
        tm._state.storage.load_punctual = MagicMock(side_effect=RuntimeError("error"))

        await tm._load_trips()

        assert tm._state.recurring_trips == {}
        assert tm._state.punctual_trips == {}

    @pytest.mark.asyncio
    async def test_get_next_trip_punctual(self):
        """Next trip is a pending punctual trip."""
        tm = _make_tm()
        future = datetime(2099, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        tm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "pendiente",
                "tipo": "punctual",
                "datetime": "2099-01-01T14:00:00",
            }
        }
        tm._state.recurring_trips = {}
        tm._soc._get_trip_time = MagicMock(return_value=future)

        result = await tm.async_get_next_trip()
        assert result is not None
        assert result["id"] == "pun_1"

    @pytest.mark.asyncio
    async def test_get_next_trip_no_trips(self):
        """No trips → returns None."""
        tm = _make_tm()
        tm._state.recurring_trips = {}
        tm._state.punctual_trips = {}

        result = await tm.async_get_next_trip()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_trip_after_punctual(self):
        """async_get_next_trip_after finds future punctual trip."""
        tm = _make_tm()
        past = datetime(2020, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        future = datetime(2099, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        tm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "pendiente",
                "tipo": "punctual",
                "datetime": "2099-01-01T14:00:00",
            }
        }
        tm._state.recurring_trips = {}
        tm._soc._get_trip_time = MagicMock(return_value=future)

        result = await tm.async_get_next_trip_after(past)
        assert result is not None
        assert result["id"] == "pun_1"

    @pytest.mark.asyncio
    async def test_get_next_trip_after_no_future(self):
        """async_get_next_trip_after returns None when no future trip."""
        tm = _make_tm()
        future = datetime(2099, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        later = datetime(2099, 1, 1, 16, 0, 0, tzinfo=timezone.utc)
        tm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "pendiente",
                "tipo": "punctual",
                "datetime": "2099-01-01T14:00:00",
            }
        }
        tm._state.recurring_trips = {}
        tm._soc._get_trip_time = MagicMock(return_value=future)

        later = datetime(2030, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        later = datetime(2099, 1, 1, 16, 0, 0, tzinfo=timezone.utc)
        result = await tm.async_get_next_trip_after(later)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_trip_after_recurring_invalid_hora(self):
        """Invalid trip hora in recurring → warning, skipped."""
        tm = _make_tm()
        past = datetime(2020, 1, 6, 10, 0, 0, tzinfo=timezone.utc)  # Monday
        tm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "activo": True,
                "dia_semana": "lunes",
                "hora": "invalid",
            }
        }
        tm._state.punctual_trips = {}

        result = await tm.async_get_next_trip_after(past)
        assert result is None

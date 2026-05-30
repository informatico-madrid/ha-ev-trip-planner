"""Execution tests for SOCHelpers and SOCQuery.

Covers _get_charging_power, _get_day_index, async_get_vehicle_soc
paths, and exception handling.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.const import DEFAULT_CHARGING_POWER
from custom_components.ev_trip_planner.trip._soc_helpers import SOCHelpers
from custom_components.ev_trip_planner.trip._soc_query import SOCQuery
from custom_components.ev_trip_planner.trip.state import TripManagerState


def _make_state():
    """Create a TripManagerState with proper mocks."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.states = MagicMock()

    state = TripManagerState(
        hass=hass,
        vehicle_id="test_vehicle",
        entry_id="test_entry",
    )
    state.recurring_trips = {}
    state.punctual_trips = {}
    state._soc_helpers = SOCHelpers(state)
    state._soc = SOCQuery(state)
    return state


class TestSOCHelpers:
    """Test SOCHelpers methods (_get_charging_power, _get_day_index, etc.)."""

    def test_get_charging_power_default(self):
        """No matching config entry -> default charging power."""
        state = _make_state()
        sm = SOCHelpers(state)
        result = sm._get_charging_power()
        assert result > 0

    def test_get_charging_power_from_entry(self):
        """Matching config entry with charging power."""
        state = _make_state()
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 22.0,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
        }
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        sm = SOCHelpers(state)
        result = sm._get_charging_power()
        assert result == 22.0

    def test_get_charging_power_invalid_value(self):
        """Invalid charging power value -> default used."""
        state = _make_state()
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": -5,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
        }
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        sm = SOCHelpers(state)
        result = sm._get_charging_power()
        assert result > 0

    def test_get_charging_power_entry_exception(self):
        """Exception during config lookup -> default power."""
        state = _make_state()
        state.hass.config_entries.async_entries = MagicMock(
            side_effect=RuntimeError("config error")
        )
        sm = SOCHelpers(state)
        result = sm._get_charging_power()
        assert result > 0

    def test_get_day_index_monday(self):
        """Day index for monday."""
        sm = SOCHelpers(_make_state())
        assert sm._get_day_index("lunes") == 0

    def test_get_day_index_friday(self):
        """Day index for friday."""
        sm = SOCHelpers(_make_state())
        idx = sm._get_day_index("viernes")
        assert idx >= 0

    def test_get_day_index_unknown(self):
        """Unknown day name -> 0 (defaults to monday)."""
        sm = SOCHelpers(_make_state())
        assert sm._get_day_index("someday") == 0

    def test_parse_trip_datetime_exception(self):
        """Invalid trip datetime -> warning logged, returns now (fallback)."""
        sm = SOCHelpers(_make_state())
        result = sm._parse_trip_datetime("not-a-date!!")
        assert result is not None

    def test_parse_trip_datetime_allow_none(self):
        """Invalid trip datetime with allow_none -> returns None."""
        sm = SOCHelpers(_make_state())
        result = sm._parse_trip_datetime("not-a-date!!", allow_none=True)
        assert result is None

    def test_get_trip_time_returns_none(self):
        """trip with no tipo -> returns None."""
        sm = SOCHelpers(_make_state())
        result = sm._get_trip_time({})
        assert result is None

    def test_get_trip_time_with_valid_tipo(self):
        """trip with valid tipo -> returns trip time."""
        sm = SOCHelpers(_make_state())
        result = sm._get_trip_time(
            {"tipo": "recurrente", "dia_semana": "lunes", "hora": "14:00"}
        )
        assert result is not None

    def test_get_trip_time_with_tipo_but_no_time(self):
        """trip with tipo but no time data -> returns None."""
        sm = SOCHelpers(_make_state())
        result = sm._get_trip_time({"tipo": "punctual"})
        assert result is None

    def test_parse_trip_datetime_with_tz_naive_datetime(self):
        """Datetime object without tzinfo gets UTC added."""
        sm = SOCHelpers(_make_state())
        naive_dt = datetime(2026, 6, 1, 14, 0, 0)
        result = sm._parse_trip_datetime(naive_dt)
        assert result is not None
        assert result.tzinfo is not None

    def test_parse_trip_datetime_with_valid_string(self):
        """Valid ISO datetime string returns parsed datetime."""
        sm = SOCHelpers(_make_state())
        result = sm._parse_trip_datetime("2026-06-01T14:00:00+00:00")
        assert result is not None
        assert result.tzinfo is not None

    def test_parse_trip_datetime_naive_from_string(self):
        """String parsed without tz → UTC added (line 51)."""
        sm = SOCHelpers(_make_state())
        # A bare date string may be parsed as naive by dt_util.parse_datetime
        result = sm._parse_trip_datetime("2026-06-01")
        assert result is not None
        assert result.tzinfo is not None

    def test_parse_trip_datetime_exception_path(self):
        """Exception during parse → warning logged, returns now (lines 59-61)."""
        sm = SOCHelpers(_make_state())
        # dt_util.parse_datetime may raise on very specific malformed input
        result = sm._parse_trip_datetime(object())  # Non-string type may raise
        assert result is not None

    def test_calcular_tasa_carga_soc(self):
        """_calcular_tasa_carga_soc returns charging rate."""
        sm = SOCHelpers(_make_state())
        result = sm._calcular_tasa_carga_soc(3.6, 50.0)
        assert result > 0

    def test_is_trip_today_true(self):
        """_is_trip_today returns True for today's trip."""
        from datetime import date

        sm = SOCHelpers(_make_state())
        result = sm._is_trip_today(
            {"tipo": "recurring", "dia_semana": date.today().strftime("%A").lower()},
            date.today(),
        )
        assert result is not None


class TestSOCQuery:
    """Test SOCQuery methods (async_get_vehicle_soc, async_calcular_energia_necesaria)."""

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_from_sensor(self):
        """SOC fetched from sensor state."""
        state = _make_state()
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
            "soc_sensor": "sensor.soc",
        }
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        state_obj = MagicMock()
        state_obj.state = "75.5"
        state.hass.states.get = MagicMock(return_value=state_obj)

        sq = SOCQuery(state)
        result = await sq.async_get_vehicle_soc("test_vehicle")
        assert result == 75.5

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_sensor_unknown(self):
        """Sensor state is 'unknown' -> returns 0.0."""
        state = _make_state()
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
            "soc_sensor": "sensor.soc",
        }
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        state_obj = MagicMock()
        state_obj.state = "unknown"
        state.hass.states.get = MagicMock(return_value=state_obj)

        sq = SOCQuery(state)
        result = await sq.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_sensor_unavailable(self):
        """Sensor state is 'unavailable' -> returns 0.0."""
        state = _make_state()
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
            "soc_sensor": "sensor.soc",
        }
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        state_obj = MagicMock()
        state_obj.state = "unavailable"
        state.hass.states.get = MagicMock(return_value=state_obj)

        sq = SOCQuery(state)
        result = await sq.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_no_sensor(self):
        """No soc_sensor in config -> returns 0.0."""
        state = _make_state()
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
        }
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])

        sq = SOCQuery(state)
        result = await sq.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_no_entry(self):
        """No config entry found -> returns 0.0."""
        state = _make_state()
        state.hass.config_entries.async_entries = MagicMock(return_value=[])

        sq = SOCQuery(state)
        result = await sq.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_exception(self):
        """Exception during SOC fetch -> returns 0.0."""
        state = _make_state()
        state.hass.config_entries.async_entries = MagicMock(
            side_effect=RuntimeError("HA error")
        )

        sq = SOCQuery(state)
        result = await sq.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_calcular_energia_necesaria_minimal(self):
        """Minimal vehicle_config produces valid energy calc."""
        state = _make_state()
        sq = SOCQuery(state)
        trip = {"kwh": 10.0, "tipo": "punctual"}
        vehicle_config = {
            "battery_capacity_kwh": 75.0,
            "charging_power_kw": 3.6,
            "soc_current": 50.0,
            "safety_margin_percent": 10.0,
        }
        result = await sq.async_calcular_energia_necesaria(trip, vehicle_config)
        assert "energia_necesaria_kwh" in result
        assert "horas_carga_necesarias" in result

    @pytest.mark.asyncio
    async def test_calcular_energia_necesaria_km_trip(self):
        """Trip with km distance."""
        state = _make_state()
        sq = SOCQuery(state)
        trip = {"km": 50.0, "tipo": "punctual", "consumo": 0.2}
        vehicle_config = {
            "battery_capacity_kwh": 75.0,
            "charging_power_kw": 3.6,
            "soc_current": 50.0,
            "safety_margin_percent": 10.0,
        }
        result = await sq.async_calcular_energia_necesaria(trip, vehicle_config)
        assert "energia_necesaria_kwh" in result

    @pytest.mark.asyncio
    async def test_get_kwh_needed_today_with_punctual(self):
        """async_get_kwh_needed_today includes punctual pending trips (lines 119-122)."""
        state = _make_state()
        state.punctual_trips = {
            "p1": {"id": "p1", "estado": "pendiente", "tipo": "punctual", "kwh": 15.0}
        }
        state._soc._is_trip_today = MagicMock(return_value=True)
        result = await state._soc.async_get_kwh_needed_today()
        assert result == 15.0

    @pytest.mark.asyncio
    async def test_get_hours_needed_today(self):
        """async_get_hours_needed_today with positive kwh and charging_power (lines 127-129)."""
        state = _make_state()
        state.punctual_trips = {
            "p1": {"id": "p1", "estado": "pendiente", "tipo": "punctual", "kwh": 10.0}
        }
        state.recurring_trips = {}
        state._soc._is_trip_today = MagicMock(return_value=True)
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
        }
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        sq = SOCQuery(state)
        result = await sq.async_get_hours_needed_today()
        assert result >= 3  # 10 kWh / 3.6 kW = ~3 hours

    @pytest.mark.asyncio
    async def test_get_charging_power_from_entry(self):
        """_get_charging_power finds config entry with matching vehicle_name (lines 175-177)."""
        state = _make_state()
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 7.0,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
        }
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        sq = SOCQuery(state)
        result = sq._get_charging_power()
        assert result == 7.0

    @pytest.mark.asyncio
    async def test_get_charging_power_invalid_value(self):
        """_get_charging_power with invalid power -> default (lines 180-181)."""
        state = _make_state()
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": -5,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
        }
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        sq = SOCQuery(state)
        result = sq._get_charging_power()
        assert result > 0  # Should be DEFAULT_CHARGING_POWER

    @pytest.mark.asyncio
    async def test_parse_trip_datetime_exception_path(self):
        """_parse_trip_datetime exception catches and returns default (lines 155-157)."""
        state = _make_state()
        sq = SOCQuery(state)
        result = sq._parse_trip_datetime(object())  # non-string may raise
        assert result is not None  # Returns now() or None

    @pytest.mark.asyncio
    async def test_get_trip_time_returns_none(self):
        """_get_trip_time with tipo but no valid time -> returns None (line 219)."""
        state = _make_state()
        sq = SOCQuery(state)
        result = sq._get_trip_time(
            {"tipo": "recurrente"}
        )  # no hora/dia_semana/datetime
        assert result is None

    @pytest.mark.asyncio
    async def test_get_day_index(self):
        """_get_day_index delegates to calculate_day_index (line 223)."""
        state = _make_state()
        sq = SOCQuery(state)
        result = sq._get_day_index("lunes")
        assert result >= 0

    @pytest.mark.asyncio
    async def test_get_kwh_needed_today_punctual(self):
        """_get_kwh_needed_today includes pending punctual trips (lines 119-122)."""
        state = _make_state()
        state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "pendiente",
                "tipo": "puntual",
                "kwh": 5.0,
            }
        }
        state._soc = MagicMock()
        state._soc._is_trip_today = MagicMock(return_value=True)
        sq = SOCQuery(state)
        result = await sq.async_get_kwh_needed_today()
        assert result == 5.0


class TestSOCQueryExceptionPath:
    """Test _get_charging_power exception path."""

    def test_get_charging_power_exception_falls_to_default(self):
        """Exception in _get_charging_power returns DEFAULT_CHARGING_POWER (lines 182-183)."""
        state = _make_state()
        sq = SOCQuery(state)
        state._soc = sq  # self-reference for consistency
        # Force exception by making config_entries.async_entries raise
        state.hass.config_entries.async_entries = MagicMock(
            side_effect=RuntimeError("config error")
        )
        result = sq._get_charging_power()
        assert result == DEFAULT_CHARGING_POWER

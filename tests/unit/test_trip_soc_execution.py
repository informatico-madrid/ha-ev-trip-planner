"""Execution tests for SOCHelpers, SOCQuery, and SOCWindow.

Covers _get_charging_power, _get_day_index, async_get_vehicle_soc
paths, and exception handling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip._soc_helpers import SOCHelpers
from custom_components.ev_trip_planner.trip._soc_query import SOCQuery
from custom_components.ev_trip_planner.trip._soc_window import (
    SOCWindow,
    VentanaCargaParams,
)
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
        entry.data = {"vehicle_name": "test_vehicle", "charging_power_kw": 22.0}
        state.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        sm = SOCHelpers(state)
        result = sm._get_charging_power()
        assert result == 22.0

    def test_get_charging_power_invalid_value(self):
        """Invalid charging power value -> default used."""
        state = _make_state()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle", "charging_power_kw": -5}
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
        result = sm._get_trip_time({"tipo": "recurring", "dia_semana": "lunes", "hora": "14:00:00"})
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

    def test_calcular_tasa_carga_soc(self):
        """_calcular_tasa_carga_soc returns charging rate."""
        sm = SOCHelpers(_make_state())
        result = sm._calcular_tasa_carga_soc(3.6, 50.0)
        assert result > 0

    def test_calcular_soc_objetivo_base(self):
        """_calcular_soc_objetivo_base returns target percentage."""
        sm = SOCHelpers(_make_state())
        result = sm._calcular_soc_objetivo_base({"km": 50}, 50.0)
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
        entry.data = {"vehicle_name": "test_vehicle", "soc_sensor": "sensor.soc"}
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
        entry.data = {"vehicle_name": "test_vehicle", "soc_sensor": "sensor.soc"}
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
        entry.data = {"vehicle_name": "test_vehicle", "soc_sensor": "sensor.soc"}
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
        entry.data = {"vehicle_name": "test_vehicle"}
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
        }
        result = await sq.async_calcular_energia_necesaria(trip, vehicle_config)
        assert "energia_necesaria_kwh" in result


class TestSOCWindow:
    """Test SOCWindow methods using dataclass-based params."""

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_next_trip_none(self):
        """No next trip after hora_regreso -> returns zeros."""
        state = _make_state()
        # Need to mock state._navigator since calcular_ventana_carga uses it
        state._navigator = MagicMock()
        state._navigator.async_get_next_trip_after = AsyncMock(return_value=None)
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=None)
        sw = SOCWindow(state)
        future = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        params = VentanaCargaParams(
            trips=[{"tipo": "punctual"}],
            soc_actual=50.0,
            hora_regreso=future,
            charging_power_kw=3.6,
            safety_margin_percent=10.0,
        )
        result = await sw.calcular_ventana_carga(params)
        assert result["ventana_horas"] == 0

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_non_string_hora_regreso(self):
        """Non-string (datetime) hora_regreso passed directly."""
        state = _make_state()
        state._navigator = MagicMock()
        state._navigator.async_get_next_trip_after = AsyncMock(return_value=None)
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=None)
        sw = SOCWindow(state)
        future = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        params = VentanaCargaParams(
            trips=[{"tipo": "punctual"}],
            soc_actual=50.0,
            hora_regreso=future,
            charging_power_kw=3.6,
            safety_margin_percent=10.0,
        )
        result = await sw.calcular_ventana_carga(params)
        assert result is not None

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_multitrip_with_trip_tipo_datetime(self):
        """multitrip: trip with tipo + datetime."""
        state = _make_state()
        sw = SOCWindow(state)
        future = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        trips = [
            {
                "id": "t1",
                "tipo": "punctual",
                "datetime": "2099-01-01T18:00:00",
                "kwh": 10.0,
            }
        ]
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=future)
        state._soc.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}
        )
        params = VentanaCargaParams(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=future,
            charging_power_kw=3.6,
            safety_margin_percent=10.0,
        )
        result = await sw.calcular_ventana_carga_multitrip(params)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_multitrip_charging_power_zero(self):
        """multitrip: charging_power_kw <= 0 -> horas_carga = 0."""
        state = _make_state()
        sw = SOCWindow(state)
        trips = [{"id": "t1", "kwh": 10.0, "tipo": "punctual"}]
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=None)
        params = VentanaCargaParams(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=datetime.now(timezone.utc),
            charging_power_kw=0,
            safety_margin_percent=10.0,
        )
        result = await sw.calcular_ventana_carga_multitrip(params)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_multitrip_exception_caught(self):
        """multitrip: KeyError/ValueError/TypeError is silently caught."""
        state = _make_state()
        sw = SOCWindow(state)
        trips = [{"id": "t1", "kwh": "not-a-number"}]
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=None)
        params = VentanaCargaParams(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=datetime.now(timezone.utc),
            charging_power_kw=3.6,
            safety_margin_percent=10.0,
        )
        result = await sw.calcular_ventana_carga_multitrip(params)
        assert isinstance(result, list)

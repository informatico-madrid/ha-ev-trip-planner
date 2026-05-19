"""Strengthened SOCWindow tests asserting ALL return dict keys.

These tests kill dict-key string mutations (mutmut replaces "kwh_necesarios"
with "XXkwh_necesariosXX" etc.) by asserting on every key in the return
dict. Without full-key assertions, dict-key mutants survive because only
a subset of keys is checked.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip._soc_window import (
    SOCInicioParams,
    SOCWindow,
    SOCWindowCalculator,
    VentanaCargaParams,
)


def _make_state():
    """Create a TripManagerState with proper mocks."""
    from custom_components.ev_trip_planner.trip._soc_helpers import SOCHelpers
    from custom_components.ev_trip_planner.trip._soc_query import SOCQuery
    from custom_components.ev_trip_planner.trip.state import TripManagerState

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


# ── Early return paths (parsed is not None, next_trip is None) ─────────

EXPECTED_EARLY_RETURN = {
    "ventana_horas": 0,
    "kwh_necesarios": 0,
    "horas_carga_necesarias": 0,
    "inicio_ventana": None,
    "fin_ventana": None,
    "es_suficiente": True,
}


class TestVentanaCargaEarlyReturnKeys:
    """Assert ALL keys in the early-return dict of calcular_ventana_carga."""

    @pytest.mark.asyncio
    async def test_all_keys_next_trip_none(self):
        """Next trip is None → early return with exact key set (lines 105-113)."""
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
        # Full-key assertion kills dict-key string mutations
        for key, expected_value in EXPECTED_EARLY_RETURN.items():
            assert result[key] == expected_value, f"Key {key} mismatch: {result[key]} != {expected_value}"
        assert set(result.keys()) == set(EXPECTED_EARLY_RETURN.keys()), (
            f"Extra/missing keys: got {set(result.keys())}, expected {set(EXPECTED_EARLY_RETURN.keys())}"
        )


# ── Early return path: no parsed, no trip_departure_time ──────────────

EXPECTED_FUTURE_RETURN = {
    "ventana_horas": 0.0,
    "kwh_necesarios": 0.0,
    "horas_carga_necesarias": 0.0,
    "inicio_ventana": None,
    "fin_ventana": None,
    "es_suficiente": True,
}


class TestVentanaCargaFutureReturnKeys:
    """Assert ALL keys when both parsed and trip_departure_time are None."""

    @pytest.mark.asyncio
    async def test_all_keys_no_parsed_no_trip_time(self):
        """Both None → future-return dict (lines 131-139)."""
        state = _make_state()
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=None)
        state._soc._parse_trip_datetime = MagicMock(return_value=None)

        sw = SOCWindow(state)
        params = VentanaCargaParams(
            trips=[{"id": "t1"}],
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=3.6,
        )
        result = await sw.calcular_ventana_carga(params)
        for key, expected_value in EXPECTED_FUTURE_RETURN.items():
            assert result[key] == expected_value
        assert set(result.keys()) == set(EXPECTED_FUTURE_RETURN.keys())


# ── Normal path: full calculation returns ─────────────────────────────

NORMAL_KEYS = {
    "ventana_horas",
    "kwh_necesarios",
    "horas_carga_necesarias",
    "inicio_ventana",
    "fin_ventana",
    "es_suficiente",
}


class TestVentanaCargaNormalPathKeys:
    """Assert ALL keys in the normal (non-early-return) path."""

    @pytest.mark.asyncio
    async def test_all_keys_with_parsed_time(self):
        """Parsed hora_regreso → normal calculation returns all keys."""
        state = _make_state()
        state._navigator = MagicMock()
        future = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        state._navigator.async_get_next_trip_after = AsyncMock(
            return_value={"tipo": "punctual", "datetime": "2099-01-02T08:00:00"}
        )
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=future)
        state._soc.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 5.0, "horas_carga_necesarias": 1.5}
        )

        sw = SOCWindow(state)
        params = VentanaCargaParams(
            trips=[{"tipo": "punctual", "datetime": "2099-01-01T18:00:00"}],
            soc_actual=50.0,
            hora_regreso=future,
            charging_power_kw=3.6,
        )
        result = await sw.calcular_ventana_carga(params)
        assert NORMAL_KEYS.issubset(set(result.keys())), (
            f"Missing keys: {NORMAL_KEYS - set(result.keys())}"
        )
        assert isinstance(result["ventana_horas"], float)
        assert isinstance(result["kwh_necesarios"], float)
        assert isinstance(result["es_suficiente"], bool)

    @pytest.mark.asyncio
    async def test_all_keys_datetime_fallback(self):
        """No parsed, fallback to trip datetime string → all keys present."""
        state = _make_state()
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=None)
        trip_dt = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        state._soc._parse_trip_datetime = MagicMock(return_value=trip_dt)
        state._soc.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 8.0, "horas_carga_necesarias": 2.0}
        )

        sw = SOCWindow(state)
        params = VentanaCargaParams(
            trips=[{"id": "t1", "datetime": "2099-01-01T18:00:00"}],
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=3.6,
        )
        result = await sw.calcular_ventana_carga(params)
        assert NORMAL_KEYS.issubset(set(result.keys()))
        assert isinstance(result["ventana_horas"], float)


# ── Multitrip key assertions ──────────────────────────────────────────

MULTI_TRIP_KEYS = {
    "ventana_horas",
    "kwh_necesarios",
    "horas_carga_necesarias",
    "inicio_ventana",
    "fin_ventana",
    "es_suficiente",
    "trip",
}


class TestVentanaCargaMultitripKeys:
    """Assert ALL keys in multitrip return entries."""

    @pytest.mark.asyncio
    async def test_multitrip_all_keys_empty_trips(self):
        """Empty trips → empty list (no dict to check)."""
        state = _make_state()
        sw = SOCWindow(state)
        params = VentanaCargaParams(
            trips=[],
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=3.6,
        )
        result = await sw.calcular_ventana_carga_multitrip(params)
        assert result == []

    @pytest.mark.asyncio
    async def test_multitrip_all_keys_single_trip(self):
        """Single trip → one entry with all keys."""
        state = _make_state()
        future = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=future)
        state._soc.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}
        )

        sw = SOCWindow(state)
        params = VentanaCargaParams(
            trips=[{"id": "t1", "tipo": "punctual", "datetime": "2099-01-01T18:00:00"}],
            soc_actual=50.0,
            hora_regreso=future,
            charging_power_kw=3.6,
        )
        result = await sw.calcular_ventana_carga_multitrip(params)
        assert len(result) == 1
        entry = result[0]
        assert MULTI_TRIP_KEYS.issubset(set(entry.keys())), (
            f"Missing keys: {MULTI_TRIP_KEYS - set(entry.keys())}"
        )

    @pytest.mark.asyncio
    async def test_multitrip_all_keys_multi_trip(self):
        """Multi-trip → each entry has all keys."""
        state = _make_state()
        future1 = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        future2 = datetime(2099, 1, 2, 18, 0, 0, tzinfo=timezone.utc)
        state._soc = MagicMock()
        state._soc._get_trip_time.side_effect = [future1, future2]
        state._soc.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}
        )

        sw = SOCWindow(state)
        params = VentanaCargaParams(
            trips=[
                {"id": "t1", "tipo": "punctual", "datetime": "2099-01-01T18:00:00"},
                {"id": "t2", "tipo": "punctual", "datetime": "2099-01-02T18:00:00"},
            ],
            soc_actual=50.0,
            hora_regreso=future1,
            charging_power_kw=3.6,
        )
        result = await sw.calcular_ventana_carga_multitrip(params)
        assert len(result) == 2
        for entry in result:
            assert MULTI_TRIP_KEYS.issubset(set(entry.keys())), (
                f"Missing keys in entry: {MULTI_TRIP_KEYS - set(entry.keys())}"
            )


# ── SOCInicioParams key assertions ────────────────────────────────────

SOC_INICIO_KEYS = {"soc_inicio", "trip", "arrival_soc"}


class TestCalcularSocInicioTripsKeys:
    """Assert ALL keys in calcular_soc_inicio_trips return entries."""

    @pytest.mark.asyncio
    async def test_all_keys_empty_trips(self):
        """Empty trips → empty list."""
        state = _make_state()
        sw = SOCWindow(state)
        params = SOCInicioParams(
            trips=[],
            soc_inicial=50.0,
            hora_regreso=None,
            charging_power_kw=3.6,
        )
        result = await sw.calcular_soc_inicio_trips(params)
        assert result == []

    @pytest.mark.asyncio
    async def test_all_keys_single_trip(self):
        """Single trip → one entry with all keys."""
        state = _make_state()
        future = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        state._soc = MagicMock()
        state._soc._get_trip_time = MagicMock(return_value=future)
        state._soc.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}
        )

        sw = SOCWindow(state)
        params = SOCInicioParams(
            trips=[{"id": "t1", "tipo": "punctual"}],
            soc_inicial=50.0,
            hora_regreso=future,
            charging_power_kw=3.6,
            battery_capacity_kwh=50.0,
        )
        result = await sw.calcular_soc_inicio_trips(params)
        assert len(result) == 1
        entry = result[0]
        assert SOC_INICIO_KEYS.issubset(set(entry.keys())), (
            f"Missing keys: {SOC_INICIO_KEYS - set(entry.keys())}"
        )
        assert isinstance(entry["soc_inicio"], float)
        assert isinstance(entry["arrival_soc"], float)


# ── Pure function: _parse_hora_regreso ────────────────────────────────


class TestParseHoraRegreso:
    """Test _parse_hora_regreso branch coverage."""

    def test_none_returns_none(self):
        """None → None."""
        from custom_components.ev_trip_planner.trip._soc_window import (
            _parse_hora_regreso,
        )
        assert _parse_hora_regreso(None) is None

    def test_datetime_unchanged_tz_aware(self):
        """TZ-aware datetime returned as-is."""
        from custom_components.ev_trip_planner.trip._soc_window import (
            _parse_hora_regreso,
        )
        dt = datetime(2026, 6, 1, 14, 0, 0, tzinfo=timezone.utc)
        assert _parse_hora_regreso(dt) is dt

    def test_naive_dt_gets_utc(self):
        """Naive datetime → UTC added."""
        from custom_components.ev_trip_planner.trip._soc_window import (
            _parse_hora_regreso,
        )
        dt = datetime(2026, 6, 1, 14, 0, 0)
        result = _parse_hora_regreso(dt)
        assert result.tzinfo is timezone.utc

    def test_valid_iso_string_parsed(self):
        """Valid ISO string → parsed datetime."""
        from custom_components.ev_trip_planner.trip._soc_window import (
            _parse_hora_regreso,
        )
        result = _parse_hora_regreso("2026-06-01T14:00:00+02:00")
        assert result is not None
        assert result.hour == 14

    def test_valid_naive_iso_string_gets_utc(self):
        """ISO string without tz → UTC added."""
        from custom_components.ev_trip_planner.trip._soc_window import (
            _parse_hora_regreso,
        )
        result = _parse_hora_regreso("2026-06-01T14:00:00")
        assert result is not None
        assert result.tzinfo is timezone.utc

    def test_invalid_string_returns_none(self):
        """Invalid string → None."""
        from custom_components.ev_trip_planner.trip._soc_window import (
            _parse_hora_regreso,
        )
        assert _parse_hora_regreso("not-a-date") is None

    def test_non_datetime_non_string_type(self):
        """Non-datetime, non-string type → None (ValueError path)."""
        from custom_components.ev_trip_planner.trip._soc_window import (
            _parse_hora_regreso,
        )
        assert _parse_hora_regreso(123) is None
        assert _parse_hora_regreso(["2026-06-01"]) is None

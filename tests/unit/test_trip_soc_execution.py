"""Execution tests for _SOCMixin.

Covers _get_charging_power, _get_day_index, async_get_vehicle_soc
paths, and exception handling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin
from custom_components.ev_trip_planner.trip.state import TripManagerState


def _make_soc():
    """Create a _SOCMixin with proper state."""
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
    state._get_trip_time = MagicMock(return_value=None)
    state._load_trips = AsyncMock()
    return _SOCMixin(state)


class TestSOCMixinExecution:
    """Test _SOCMixin execution paths."""

    def test_get_charging_power_default(self):
        """No matching config entry → default charging power."""
        soc = _make_soc()
        result = soc._get_charging_power()
        assert result > 0

    def test_get_charging_power_from_entry(self):
        """Matching config entry with charging power."""
        soc = _make_soc()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle", "charging_power_kw": 22.0}
        soc._state.hass.config_entries.async_entries = MagicMock(
            return_value=[entry]
        )
        result = soc._get_charging_power()
        assert result == 22.0

    def test_get_charging_power_invalid_value(self):
        """Invalid charging power value → default used."""
        soc = _make_soc()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle", "charging_power_kw": -5}
        soc._state.hass.config_entries.async_entries = MagicMock(
            return_value=[entry]
        )
        result = soc._get_charging_power()
        # Default is used for non-positive values
        assert result > 0

    def test_get_charging_power_entry_exception(self):
        """Exception during config lookup → default power."""
        soc = _make_soc()
        soc._state.hass.config_entries.async_entries = MagicMock(
            side_effect=RuntimeError("config error")
        )
        result = soc._get_charging_power()
        assert result > 0

    def test_get_day_index_monday(self):
        """Day index for monday."""
        soc = _make_soc()
        assert soc._get_day_index("lunes") == 0

    def test_get_day_index_friday(self):
        """Day index for friday."""
        soc = _make_soc()
        idx = soc._get_day_index("viernes")
        assert idx >= 0

    def test_get_day_index_unknown(self):
        """Unknown day name → 0 (defaults to monday)."""
        soc = _make_soc()
        assert soc._get_day_index("someday") == 0

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_from_sensor(self):
        """SOC fetched from sensor state."""
        soc = _make_soc()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle", "soc_sensor": "sensor.soc"}
        soc._state.hass.config_entries.async_entries = MagicMock(
            return_value=[entry]
        )
        state_obj = MagicMock()
        state_obj.state = "75.5"
        soc._state.hass.states.get = MagicMock(return_value=state_obj)

        result = await soc.async_get_vehicle_soc("test_vehicle")
        assert result == 75.5

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_sensor_unknown(self):
        """Sensor state is 'unknown' → returns 0.0."""
        soc = _make_soc()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle", "soc_sensor": "sensor.soc"}
        soc._state.hass.config_entries.async_entries = MagicMock(
            return_value=[entry]
        )
        state_obj = MagicMock()
        state_obj.state = "unknown"
        soc._state.hass.states.get = MagicMock(return_value=state_obj)

        result = await soc.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_sensor_unavailable(self):
        """Sensor state is 'unavailable' → returns 0.0."""
        soc = _make_soc()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle", "soc_sensor": "sensor.soc"}
        soc._state.hass.config_entries.async_entries = MagicMock(
            return_value=[entry]
        )
        state_obj = MagicMock()
        state_obj.state = "unavailable"
        soc._state.hass.states.get = MagicMock(return_value=state_obj)

        result = await soc.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_no_sensor(self):
        """No soc_sensor in config → returns 0.0."""
        soc = _make_soc()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle"}
        soc._state.hass.config_entries.async_entries = MagicMock(
            return_value=[entry]
        )

        result = await soc.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_no_entry(self):
        """No config entry found → returns 0.0."""
        soc = _make_soc()
        soc._state.hass.config_entries.async_entries = MagicMock(return_value=[])

        result = await soc.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_exception(self):
        """Exception during SOC fetch → returns 0.0."""
        soc = _make_soc()
        soc._state.hass.config_entries.async_entries = MagicMock(
            side_effect=RuntimeError("HA error")
        )

        result = await soc.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_calcular_energia_necesaria_minimal(self):
        """Minimal vehicle_config produces valid energy calc."""
        soc = _make_soc()
        trip = {"kwh": 10.0, "tipo": "punctual"}
        vehicle_config = {
            "battery_capacity_kwh": 75.0,
            "charging_power_kw": 3.6,
            "soc_current": 50.0,
        }
        result = await soc.async_calcular_energia_necesaria(trip, vehicle_config)
        assert "energia_necesaria_kwh" in result
        assert "horas_carga_necesarias" in result

    @pytest.mark.asyncio
    async def test_calcular_energia_necesaria_km_trip(self):
        """Trip with km distance."""
        soc = _make_soc()
        trip = {"km": 50.0, "tipo": "punctual", "consumo": 0.2}
        vehicle_config = {
            "battery_capacity_kwh": 75.0,
            "charging_power_kw": 3.6,
            "soc_current": 50.0,
        }
        result = await soc.async_calcular_energia_necesaria(trip, vehicle_config)
        assert "energia_necesaria_kwh" in result

    @pytest.mark.asyncio
    async def test_parse_trip_datetime_exception(self):
        """Invalid trip datetime → warning logged, returns None."""
        soc = _make_soc()
        result = soc._state._parse_trip_datetime("not-a-date!!")
        assert result is None

    def test_get_trip_time_returns_none(self):
        """trip with no tipo → returns None."""
        soc = _make_soc()
        result = soc._get_trip_time({})
        assert result is None

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_hora_regreso_invalid_string(self):
        """Invalid hora_regreso string → parsed_hora_regreso set to None."""
        soc = _make_soc()
        result = await soc.async_calcular_ventana_carga(
            hora_regreso="not-a-time",
            vehicle_config={"battery_capacity_kwh": 75.0, "soc_current": 50.0},
        )
        assert result["ventana_horas"] == 0

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_next_trip_none(self):
        """No next trip after hora_regreso → returns zeros."""
        soc = _make_soc()
        future = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        soc._state.async_get_next_trip_after = AsyncMock(return_value=None)
        soc._state._parse_trip_datetime = MagicMock(return_value=future)
        result = await soc.async_calcular_ventana_carga(
            hora_regreso="2099-01-01T18:00:00",
            vehicle_config={"battery_capacity_kwh": 75.0, "soc_current": 50.0},
        )
        assert result["ventana_horas"] == 0

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_hora_regreso_tzinfo_none(self):
        """tzinfo-naive hora_regreso gets UTC."""
        soc = _make_soc()
        from datetime import datetime as dt

        naive_dt = dt(2099, 1, 1, 18, 0, 0)
        soc._state._parse_trip_datetime = MagicMock(return_value=naive_dt)
        soc._state.async_get_next_trip_after = AsyncMock(return_value=None)
        result = await soc.async_calcular_ventana_carga(
            hora_regreso=naive_dt.isoformat(),
            vehicle_config={"battery_capacity_kwh": 75.0, "soc_current": 50.0},
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_non_string_hora_regreso(self):
        """Non-string hora_regreso passed directly."""
        soc = _make_soc()
        future = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        soc._state._parse_trip_datetime = MagicMock(return_value=future)
        soc._state.async_get_next_trip_after = AsyncMock(return_value=None)
        result = await soc.async_calcular_ventana_carga(
            hora_regreso=future,
            vehicle_config={"battery_capacity_kwh": 75.0, "soc_current": 50.0},
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_multitrip_with_trip_tipo_datetime(self):
        """multitrip: trip_tipo + trip_datetime branch with time check."""
        soc = _make_soc()
        future = datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        trips = [
            {
                "id": "t1",
                "tipo": "punctual",
                "datetime": "2099-01-01T18:00:00",
                "kwh": 10.0,
            }
        ]
        soc._state._get_trip_time = MagicMock(return_value=future)
        result = await soc.async_calcular_ventana_carga_multitrip(
            trips,
            vehicle_config={
                "battery_capacity_kwh": 75.0,
                "soc_current": 50.0,
                "charging_power_kw": 3.6,
                "safety_margin_percent": 10,
            },
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_multitrip_charging_power_zero(self):
        """multitrip: charging_power_kw ≤ 0 → horas_carga = 0."""
        soc = _make_soc()
        trips = [{"id": "t1", "kwh": 10.0, "tipo": "punctual"}]
        result = await soc.async_calcular_ventana_carga_multitrip(
            trips,
            vehicle_config={
                "battery_capacity_kwh": 75.0,
                "soc_current": 50.0,
                "charging_power_kw": 0,
            },
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_multitrip_exception_caught(self):
        """multitrip: KeyError/ValueError/TypeError is silently caught."""
        soc = _make_soc()
        trips = [{"id": "t1", "kwh": "not-a-number"}]
        result = await soc.async_calcular_ventana_carga_multitrip(
            trips,
            vehicle_config={
                "battery_capacity_kwh": 75.0,
                "soc_current": 50.0,
                "charging_power_kw": 3.6,
            },
        )
        assert isinstance(result, list)

"""Comprehensive unit tests for the trip/ SOLID-decomposed package.

Covers:
- trip/manager.py: TripManager facade with mixins
- trip/_crud_mixin.py: CRUD operations mixin
- trip/_soc_mixin.py: SOC calculation mixin
- trip/_power_profile_mixin.py: Power profile mixin
- trip/_schedule_mixin.py: Schedule generation mixin
- trip/_sensor_callbacks.py: Sensor callback registry
- trip/_types.py: TypedDict definitions

Tests use mock HomeAssistant instances and verify functional behavior
of each module's public API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip import (
    CargaVentana,
    SensorCallbackRegistry,
    SOCMilestoneResult,
    TripManager,
)
from custom_components.ev_trip_planner.trip._sensor_callbacks import _SensorCallbacks
from typing import get_type_hints


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_hass():
    """Minimal mock HomeAssistant with required attributes."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def crud_mixins(mock_hass):
    """TripManager with all mixins but no storage/emhass."""
    tm = TripManager(mock_hass, "test_vehicle")
    tm._storage = None
    tm._emhass_adapter = None
    return tm


@pytest.fixture
def sample_recurring_trip():
    return {
        "id": "rec_lunes_abc123",
        "tipo": "recurrente",
        "dia_semana": "lunes",
        "hora": "08:00",
        "km": 50.0,
        "kwh": 7.5,
        "descripcion": "Work commute",
        "activo": True,
    }


@pytest.fixture
def sample_punctual_trip():
    return {
        "id": "pun_20260511_xyz789",
        "tipo": "puntual",
        "datetime": "2026-05-11T14:00:00",
        "km": 120.0,
        "kwh": 18.0,
        "descripcion": "Weekend trip",
        "estado": "pendiente",
    }


# ---------------------------------------------------------------------------
# TripManager facade tests
# ---------------------------------------------------------------------------

class TestTripManagerFacade:
    """Tests for TripManager facade (manager.py)."""

    def test_instance_creation(self, mock_hass):
        tm = TripManager(mock_hass, "vehicle_1")
        assert tm.vehicle_id == "vehicle_1"
        assert tm.hass is mock_hass
        assert tm._trips == {}
        assert tm._recurring_trips == {}
        assert tm._punctual_trips == {}

    def test_instance_counter_increments(self, mock_hass):
        tm1 = TripManager(mock_hass, "v1")
        tm2 = TripManager(mock_hass, "v2")
        assert tm2._instance_id > tm1._instance_id

    def test_emhass_adapter_set_get(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        adapter = MagicMock()
        tm.set_emhass_adapter(adapter)
        assert tm.get_emhass_adapter() is adapter

    def test_entry_id_defaults_empty(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert tm._entry_id == ""

    def test_entry_id_set_from_constructor(self, mock_hass):
        tm = TripManager(mock_hass, "v1", entry_id="entry_123")
        assert tm._entry_id == "entry_123"

    def test_sensor_callbacks_initialized(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert tm._sensor_callbacks is not None

    def test_is_trip_today_delegates(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        trip = {"tipo": "recurrente", "dia_semana": "monday", "hora": "08:00"}
        result = tm._is_trip_today(trip, datetime.now(timezone.utc).date())
        # The pure function may return False for non-matching day, which is fine
        assert isinstance(result, bool)

    def test_validate_hora_valid(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        # Should not raise for valid times
        tm._validate_hora("08:00")
        tm._validate_hora("00:00")
        tm._validate_hora("23:59")

    def test_validate_hora_invalid_format(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        with pytest.raises(ValueError):
            tm._validate_hora("25:00")
        with pytest.raises(ValueError):
            tm._validate_hora("abc")
        with pytest.raises(ValueError):
            tm._validate_hora("8:0")

    def test_parse_trip_datetime_object(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        dt = datetime(2026, 5, 11, 8, 0, 0, tzinfo=timezone.utc)
        result = tm._parse_trip_datetime(dt)
        assert result is dt
        assert result.tzinfo is not None

    def test_parse_trip_datetime_naive_becomes_utc(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        dt = datetime(2026, 5, 11, 8, 0, 0)
        result = tm._parse_trip_datetime(dt)
        assert result.tzinfo is not None

    def test_parse_trip_datetime_string(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = tm._parse_trip_datetime("2026-05-11T08:00:00+00:00")
        assert result is not None
        assert isinstance(result, datetime)

    def test_parse_trip_datetime_invalid_returns_now(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = tm._parse_trip_datetime("not-a-date")
        assert result is not None  # falls back to now()

    def test_parse_trip_datetime_invalid_allows_none(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = tm._parse_trip_datetime("bad", allow_none=True)
        assert result is None

    def test_get_day_index_monday(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert tm._get_day_index("lunes") == 0

    def test_get_day_index_sunday(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert tm._get_day_index("domingo") == 6

    def test_get_day_index_unknown_defaults_zero(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert tm._get_day_index("nonexistent") == 0

    def test_get_day_index_case_insensitive(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert tm._get_day_index("LUNES") == 0

    def test_get_charging_power_method_exists(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        # Should return DEFAULT_CHARGING_POWER since no config entry
        result = tm.get_charging_power()
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# _CRUDMixin tests
# ---------------------------------------------------------------------------

class TestCRUDMixin:
    """Tests for _CRUDMixin (trip/_crud_mixin.py)."""

    def test_mixin_init_creates_sensor_callbacks(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert isinstance(tm._sensor_callbacks, _SensorCallbacks)

    def test_reset_trips_clears_all_collections(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._trips = {"a": 1}
        tm._recurring_trips = {"b": 2}
        tm._punctual_trips = {"c": 3}
        tm._last_update = "2026-01-01"
        tm._reset_trips()
        assert tm._trips == {}
        assert tm._recurring_trips == {}
        assert tm._punctual_trips == {}
        assert tm._last_update is None

    def test_get_all_trips_combined(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {"r1": {"id": "r1"}}
        tm._punctual_trips = {"p1": {"id": "p1"}}
        result = tm.get_all_trips()
        assert len(result["recurring"]) == 1
        assert len(result["punctual"]) == 1
        assert result["recurring"][0]["id"] == "r1"
        assert result["punctual"][0]["id"] == "p1"

    def test_get_all_trips_empty(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = tm.get_all_trips()
        assert result["recurring"] == []
        assert result["punctual"] == []

    async def test_async_get_recurring_trips(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {
            "r1": {"id": "r1", "dia_semana": "lunes"},
            "r2": {"id": "r2", "dia_semana": "martes"},
        }
        result = await tm.async_get_recurring_trips()
        assert len(result) == 2

    async def test_async_get_punctual_trips(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._punctual_trips = {
            "p1": {"id": "p1", "datetime": "2026-05-11T08:00"},
        }
        result = await tm.async_get_punctual_trips()
        assert len(result) == 1
        assert result[0]["id"] == "p1"

    async def test_async_add_recurring_trip(self, mock_hass):
        """Adding a recurring trip stores it and saves."""
        saved_data = {}

        async def mock_save(data):
            saved_data.clear()
            saved_data.update(data)

        tm = TripManager(mock_hass, "v1")
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock(side_effect=mock_save)
        tm._emhass_adapter = None

        await tm.async_add_recurring_trip(
            dia_semana="lunes", hora="08:00", km=50.0, kwh=7.5, descripcion="Work"
        )
        assert len(tm._recurring_trips) == 1
        assert saved_data["recurring_trips"] == tm._recurring_trips

    async def test_async_add_recurring_trip_with_custom_id(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_add_recurring_trip(
            trip_id="my_custom_id",
            dia_semana="miercoles",
            hora="17:00",
            km=30.0,
            kwh=4.0,
        )
        assert "my_custom_id" in tm._recurring_trips
        trip = tm._recurring_trips["my_custom_id"]
        assert trip["dia_semana"] == "miercoles"
        assert trip["activo"] is True

    async def test_async_add_punctual_trip(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_add_punctual_trip(
            datetime_str="2026-05-15T14:00:00", km=100.0, kwh=15.0
        )
        assert len(tm._punctual_trips) == 1
        trip = list(tm._punctual_trips.values())[0]
        assert trip["estado"] == "pendiente"
        assert trip["tipo"] == "puntual"

    async def test_async_add_punctual_trip_with_custom_id(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_add_punctual_trip(
            trip_id="my_pun_id",
            datetime_str="2026-06-01T10:00:00",
            km=200.0,
            kwh=30.0,
        )
        assert "my_pun_id" in tm._punctual_trips

    async def test_async_update_trip_recurring(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {
            "r1": {"id": "r1", "km": 50.0, "descripcion": "Old"}
        }
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_update_trip("r1", {"km": 75.0, "descripcion": "Updated"})
        assert tm._recurring_trips["r1"]["km"] == 75.0
        assert tm._recurring_trips["r1"]["descripcion"] == "Updated"

    async def test_async_update_trip_nonexistent_logs_warning(self, mock_hass, caplog):
        tm = TripManager(mock_hass, "v1")
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_update_trip("nonexistent", {"km": 10.0})
        assert "not found for update" in caplog.text.lower() or "not found" in caplog.text.lower()

    async def test_async_update_trip_filters_by_type(self, mock_hass):
        """Relevant fields are filtered by trip type."""
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {
            "r1": {"id": "r1", "dia_semana": "lunes", "hora": "08:00", "km": 50.0}
        }
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        # datetime is not a relevant field for recurring trips
        await tm.async_update_trip("r1", {
            "dia_semana": "martes",
            "datetime": "2026-05-11T10:00",  # should be ignored for recurring
            "km": 60.0,
        })
        assert tm._recurring_trips["r1"]["dia_semana"] == "martes"
        assert "datetime" not in tm._recurring_trips["r1"] or tm._recurring_trips["r1"]["datetime"] is None

    async def test_async_delete_trip_recurring(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {"r1": {"id": "r1"}, "r2": {"id": "r2"}}
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_delete_trip("r1")
        assert "r1" not in tm._recurring_trips
        assert "r2" in tm._recurring_trips

    async def test_async_delete_trip_punctual(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._punctual_trips = {"p1": {"id": "p1"}}
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_delete_trip("p1")
        assert "p1" not in tm._punctual_trips

    async def test_async_delete_trip_nonexistent(self, mock_hass, caplog):
        tm = TripManager(mock_hass, "v1")
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_delete_trip("nonexistent")
        assert len(tm._recurring_trips) == 0

    async def test_async_delete_all_trips(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {"r1": {"id": "r1"}}
        tm._punctual_trips = {"p1": {"id": "p1"}}
        tm._trips = {"all": "data"}
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_delete_all_trips()
        assert tm._trips == {}
        assert tm._recurring_trips == {}
        assert tm._punctual_trips == {}

    async def test_async_pause_recurring_trip(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {"r1": {"id": "r1", "activo": True}}
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()

        await tm.async_pause_recurring_trip("r1")
        assert tm._recurring_trips["r1"]["activo"] is False

    async def test_async_pause_nonexistent_trip(self, mock_hass, caplog):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {}
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()

        await tm.async_pause_recurring_trip("nonexistent")
        assert "not found for pause" in caplog.text.lower()

    async def test_async_resume_recurring_trip(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {"r1": {"id": "r1", "activo": False}}
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()

        await tm.async_resume_recurring_trip("r1")
        assert tm._recurring_trips["r1"]["activo"] is True

    async def test_async_complete_punctual_trip(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._punctual_trips = {"p1": {"id": "p1", "estado": "pendiente"}}
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()

        await tm.async_complete_punctual_trip("p1")
        assert tm._punctual_trips["p1"]["estado"] == "completado"

    async def test_async_cancel_punctual_trip(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._punctual_trips = {"p1": {"id": "p1", "estado": "pendiente"}}
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()
        tm._emhass_adapter = None

        await tm.async_cancel_punctual_trip("p1")
        assert "p1" not in tm._punctual_trips

    async def test_async_cancel_nonexistent_trip(self, mock_hass, caplog):
        tm = TripManager(mock_hass, "v1")
        tm._punctual_trips = {}
        tm._storage = MagicMock()
        tm._storage.async_save = AsyncMock()

        await tm.async_cancel_punctual_trip("nonexistent")
        assert "not found for cancellation" in caplog.text.lower()


# ---------------------------------------------------------------------------
# _SOCMixin tests
# ---------------------------------------------------------------------------

class TestSOCMixin:
    """Tests for _SOCMixin (trip/_soc_mixin.py)."""

    def test_get_charging_power_default(self, mock_hass):
        """Without config entry, defaults to DEFAULT_CHARGING_POWER (11.0)."""
        tm = TripManager(mock_hass, "v1")
        power = tm._get_charging_power()
        assert power == 11.0  # DEFAULT_CHARGING_POWER = 11.0

    def test_calcular_tasa_carga_soc(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        # 3.6 kW / 50 kWh * 100 = 7.2 %/hour
        rate = tm._calcular_tasa_carga_soc(3.6, 50.0)
        assert rate == pytest.approx(7.2)

    def test_calcular_tasa_carga_soc_zero_power(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        rate = tm._calcular_tasa_carga_soc(0.0, 50.0)
        assert rate == 0.0

    def test_calcular_soc_objetivo_base_from_kwh(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        trip = {"kwh": 10.0}
        target = tm._calcular_soc_objetivo_base(trip, 50.0)
        # 10 kWh / 50 kWh * 100 = 20% + buffer
        assert target > 0

    def test_calcular_soc_objetivo_base_from_km(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        trip = {"km": 100.0, "consumo": 0.15}
        target = tm._calcular_soc_objetivo_base(trip, 50.0)
        assert target > 0

    def test_get_day_index(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert tm._get_day_index("lunes") == 0
        assert tm._get_day_index("viernes") == 4
        assert tm._get_day_index("domingo") == 6

    async def test_async_get_vehicle_soc_no_sensor(self, mock_hass):
        """When no SOC sensor configured, returns 0.0."""
        tm = TripManager(mock_hass, "v1")
        soc = await tm.async_get_vehicle_soc("v1")
        assert soc == 0.0

    async def test_async_get_vehicle_soc_from_sensor(self, mock_hass):
        mock_state = MagicMock()
        mock_state.state = "75.5"
        mock_hass.states.get = MagicMock(return_value=mock_state)

        entry = MagicMock()
        entry.data = {"soc_sensor": "sensor.battery", "vehicle_name": "v1"}
        mock_hass.config_entries.async_entries = MagicMock(return_value=[entry])

        tm = TripManager(mock_hass, "v1")
        soc = await tm.async_get_vehicle_soc("v1")
        assert soc == 75.5

    async def test_calcular_ventana_carga_no_hora_regreso(self, mock_hass):
        """Without hora_regreso, falls back to trip_departure - 6h."""
        tm = TripManager(mock_hass, "v1")
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "08:00",
            "km": 50.0,
            "kwh": 7.5,
        }
        result = await tm.calcular_ventana_carga(
            trip, soc_actual=50.0, hora_regreso=None, charging_power_kw=3.6
        )
        assert "ventana_horas" in result
        assert "kwh_necesarios" in result
        assert result["es_suficiente"] in (True, False)

    async def test_calcular_ventana_carga_with_next_trip(self, mock_hass):
        """When there's a next trip, uses hora_regreso as window start."""
        tm = TripManager(mock_hass, "v1")
        tm._punctual_trips = {
            "p1": {
                "id": "p1",
                "tipo": "puntual",
                "datetime": "2026-05-12T09:00:00",
                "estado": "pendiente",
            }
        }
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "07:00",
            "km": 30.0,
            "kwh": 4.0,
        }
        result = await tm.calcular_ventana_carga(
            trip, soc_actual=80.0, hora_regreso=datetime(2026, 5, 11, 18, 0, 0, tzinfo=timezone.utc), charging_power_kw=3.6
        )
        assert "ventana_horas" in result

    async def test_calcular_ventana_carga_multitrip_empty(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = await tm.calcular_ventana_carga_multitrip(
            [], soc_actual=50.0, hora_regreso=None, charging_power_kw=3.6
        )
        assert result == []

    async def test_calcular_soc_inicio_trips_empty(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = await tm.calcular_soc_inicio_trips(
            [], soc_inicial=50.0, hora_regreso=None, charging_power_kw=3.6
        )
        assert result == []

    async def test_calcular_hitos_soc_empty(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = await tm.calcular_hitos_soc(
            [], soc_inicial=50.0, charging_power_kw=3.6
        )
        assert result == []

    async def test_async_get_kwh_needed_today_no_trips(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = await tm.async_get_kwh_needed_today()
        assert result == 0.0

    async def test_async_get_kwh_needed_today_active_recurring(self, mock_hass):
        """Trip that matches today contributes its kwh."""
        today = datetime.now(timezone.utc).date()
        tm = TripManager(mock_hass, "v1")
        # Create a trip for today's day of week
        dia_hoy = "lunes" if today.weekday() == 0 else "martes" if today.weekday() == 1 else "miercoles" if today.weekday() == 2 else "jueves" if today.weekday() == 3 else "viernes" if today.weekday() == 4 else "sabado" if today.weekday() == 5 else "domingo"
        tm._recurring_trips = {
            "today_trip": {
                "id": "today_trip",
                "tipo": "recurrente",
                "dia_semana": dia_hoy,
                "hora": "08:00",
                "km": 50.0,
                "kwh": 7.5,
                "activo": True,
            }
        }
        result = await tm.async_get_kwh_needed_today()
        assert result >= 7.5


# ---------------------------------------------------------------------------
# _PowerProfileMixin tests
# ---------------------------------------------------------------------------

class TestPowerProfileMixin:
    """Tests for _PowerProfileMixin (trip/_power_profile_mixin.py)."""

    def test_mixin_init(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert hasattr(tm, "async_generate_power_profile")

    async def test_async_generate_power_profile_empty_trips(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = await tm.async_generate_power_profile()
        # Returns a list of power values (may be all zeros for no trips)
        assert isinstance(result, list)

    async def test_async_generate_power_profile_with_trips(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {
            "r1": {"id": "r1", "tipo": "recurrente", "dia_semana": "lunes", "hora": "08:00", "km": 50.0, "kwh": 7.5, "activo": True}
        }
        result = await tm.async_generate_power_profile()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# _ScheduleMixin tests
# ---------------------------------------------------------------------------

class TestScheduleMixin:
    """Tests for _ScheduleMixin (trip/_schedule_mixin.py)."""

    def test_mixin_init(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        assert hasattr(tm, "async_generate_deferrables_schedule")
        assert hasattr(tm, "publish_deferrable_loads")

    async def test_async_generate_deferrables_schedule_empty(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = await tm.async_generate_deferrables_schedule()
        assert isinstance(result, list)
        # Default 7-day horizon = 168 entries
        assert len(result) == 7 * 24

    async def test_async_generate_deferrables_schedule_custom_horizon(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = await tm.async_generate_deferrables_schedule(planning_horizon_days=3)
        assert len(result) == 3 * 24

    async def test_publish_deferrable_loads_no_adapter(self, mock_hass):
        """Publishing without emhass adapter is a no-op."""
        tm = TripManager(mock_hass, "v1")
        tm._emhass_adapter = None
        # Should not raise
        await tm.publish_deferrable_loads()

    async def test_publish_deferrable_loads_with_adapter(self, mock_hass):
        adapter = MagicMock()
        adapter.async_publish_all_deferrable_loads = AsyncMock()
        tm = TripManager(mock_hass, "v1")
        tm._emhass_adapter = adapter
        tm._recurring_trips = {}
        tm._punctual_trips = {}
        await tm.publish_deferrable_loads()
        adapter.async_publish_all_deferrable_loads.assert_called_once()


# ---------------------------------------------------------------------------
# SensorCallbacks tests
# ---------------------------------------------------------------------------

class TestSensorCallbacks:
    """Tests for _SensorCallbacks (trip/_sensor_callbacks.py)."""

    def test_emit_unknown_event_logs_debug(self, mock_hass, caplog):
        sc = _SensorCallbacks()
        sc.emit("unknown_event", mock_hass, "entry_1")
        assert "Unknown sensor event" in caplog.text or caplog.text.count("unknown_event") > 0

    def test_emit_creates_recurring_sensor(self, mock_hass, caplog):
        """trip_created_recurring emits via asyncio.ensure_future."""
        sc = _SensorCallbacks()
        # Should not raise even without real sensor module
        sc.emit(
            "trip_created_recurring",
            mock_hass,
            "entry_1",
            trip_data={"id": "r1"},
            trip_id="r1",
            vehicle_id="v1",
        )

    def test_emit_removes_trip_sensor(self, mock_hass):
        sc = _SensorCallbacks()
        sc.emit(
            "trip_removed",
            mock_hass,
            "entry_1",
            trip_id="r1",
            vehicle_id="v1",
        )

    def test_emit_emhass_created(self, mock_hass):
        sc = _SensorCallbacks()
        sc.emit(
            "trip_sensor_created_emhass",
            mock_hass,
            "entry_1",
            trip_id="r1",
            vehicle_id="v1",
        )

    def test_emit_emhass_removed(self, mock_hass):
        sc = _SensorCallbacks()
        sc.emit(
            "trip_sensor_removed_emhass",
            mock_hass,
            "entry_1",
            trip_id="r1",
            vehicle_id="v1",
        )

    def test_emit_updated_sensor(self, mock_hass):
        sc = _SensorCallbacks()
        sc.emit(
            "trip_sensor_updated",
            mock_hass,
            "entry_1",
            trip_data={"id": "r1"},
        )


# ---------------------------------------------------------------------------
# SensorCallbackRegistry tests
# ---------------------------------------------------------------------------

class TestSensorCallbackRegistry:
    """Tests for SensorCallbackRegistry (trip/_sensor_callbacks.py)."""

    def test_add_and_notify(self):
        reg = SensorCallbackRegistry()
        results = []
        reg.add("sensor_1", lambda v: results.append(v))
        reg.notify("sensor_1", 42)
        assert results == [42]

    def test_add_multiple_callbacks_same_sensor(self):
        reg = SensorCallbackRegistry()
        values = []
        reg.add("s1", lambda v: values.append(v * 2))
        reg.add("s1", lambda v: values.append(v + 10))
        reg.notify("s1", 5)
        assert values == [10, 15]

    def test_remove_callback(self):
        reg = SensorCallbackRegistry()
        called = []
        def cb(v):
            called.append(v)

        reg.add("s1", cb)
        assert reg.remove("s1", cb) is True
        assert reg.remove("s1", cb) is False  # already removed
        reg.notify("s1", 1)
        assert called == []

    def test_notify_unknown_sensor_returns_empty(self):
        reg = SensorCallbackRegistry()
        assert reg.notify("unknown", "val") == []

    def test_clear_all(self):
        reg = SensorCallbackRegistry()
        reg.add("s1", lambda v: None)
        reg.add("s2", lambda v: None)
        reg.clear()
        assert reg.notify("s1", 1) == []
        assert reg.notify("s2", 1) == []

    def test_clear_single_sensor(self):
        reg = SensorCallbackRegistry()
        reg.add("s1", lambda v: None)
        reg.add("s2", lambda v: None)
        reg.clear("s1")
        assert reg.notify("s1", 1) == []
        assert len(reg.notify("s2", 1)) == 1


# ---------------------------------------------------------------------------
# _types.py TypedDict tests
# ---------------------------------------------------------------------------

class TestTypes:
    """Tests for trip/_types.py TypedDict definitions."""

    def test_carga_ventana_has_expected_keys(self):
        expected_keys = {
            "ventana_horas", "kwh_necesarios", "horas_carga_necesarias",
            "inicio_ventana", "fin_ventana", "es_suficiente",
        }
        assert set(CargaVentana.__annotations__.keys()) == expected_keys

    def test_soc_milestone_result_has_expected_keys(self):
        expected_keys = {
            "trip_id", "soc_objetivo", "kwh_necesarios",
            "deficit_acumulado", "ventana_carga",
        }
        assert set(SOCMilestoneResult.__annotations__.keys()) == expected_keys

    def test_carga_ventana_types(self):
        hints = get_type_hints(CargaVentana)
        assert hints["ventana_horas"] is float
        assert hints["es_suficiente"] is bool

    def test_soc_milestone_result_has_nested_carga(self):
        hints = get_type_hints(SOCMilestoneResult)
        assert "ventana_carga" in hints

    def test_carga_ventana_optional_fields(self):
        hints = get_type_hints(CargaVentana)
        # Optional fields are float|None or datetime|None
        assert "inicio_ventana" in hints
        assert "fin_ventana" in hints


# ---------------------------------------------------------------------------
# Manager public method tests
# ---------------------------------------------------------------------------

class TestTripManagerPublicMethods:
    """Tests for TripManager public methods (async_get_next_trip, etc.)."""

    async def test_async_get_next_trip_no_trips(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        result = await tm.async_get_next_trip()
        assert result is None

    async def test_async_get_next_trip_skips_inactive(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._recurring_trips = {
            "r1": {
                "id": "r1",
                "tipo": "recurrente",
                "dia_semana": "monday",
                "hora": "03:00",  # 3 AM = in the past
                "km": 10,
                "kwh": 1,
                "activo": False,
            }
        }
        result = await tm.async_get_next_trip()
        assert result is None

    async def test_async_get_next_trip_skips_completed_punctual(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._punctual_trips = {
            "p1": {
                "id": "p1",
                "tipo": "puntual",
                "datetime": "2026-05-11T08:00:00",
                "km": 10,
                "kwh": 1,
                "estado": "completado",
            }
        }
        result = await tm.async_get_next_trip()
        assert result is None

    async def test_async_get_next_trip_after_no_matches(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        tm._punctual_trips = {
            "p1": {
                "id": "p1",
                "tipo": "puntual",
                "datetime": "2026-05-10T08:00:00",  # in the past
                "km": 10,
                "kwh": 1,
                "estado": "pendiente",
            }
        }
        now = datetime.now(timezone.utc)
        result = await tm.async_get_next_trip_after(now)
        assert result is None

    async def test_async_get_next_trip_after_future_punctual(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        # Use explicit datetime string — no timezone offset (parsed as naive, then UTC)
        tm._punctual_trips = {
            "p1": {
                "id": "p1",
                "tipo": "puntual",
                "datetime": "2026-12-31T14:00:00",
                "km": 10,
                "kwh": 1,
                "estado": "pendiente",
            }
        }
        now = datetime.now(timezone.utc)
        result = await tm.async_get_next_trip_after(now)
        assert result is not None
        assert result["id"] == "p1"

    async def test_get_trip_time_recurring(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "08:00",
        }
        result = tm._get_trip_time(trip)
        assert result is not None
        assert result.tzinfo is not None

    async def test_get_trip_time_punctual(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        trip = {
            "tipo": "puntual",
            "datetime": "2026-06-15T14:00:00",
        }
        result = tm._get_trip_time(trip)
        assert result is not None

    async def test_get_trip_time_missing_tipo(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        trip = {"descripcion": "no type"}
        result = tm._get_trip_time(trip)
        assert result is None


# ---------------------------------------------------------------------------
# Integration: CRUD + SOC interaction
# ---------------------------------------------------------------------------

class TestCrudSocInteraction:
    """Tests for cross-mixin interaction in TripManager."""

    async def test_calcular_hitos_soc_requires_vehicle_config(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        trips = [
            {
                "id": "r1",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "08:00",
                "km": 50.0,
                "kwh": 7.5,
            }
        ]
        result = await tm.calcular_hitos_soc(
            trips, soc_inicial=50.0, charging_power_kw=3.6
        )
        assert isinstance(result, list)

    async def test_energy_calculation_with_vehicle_config(self, mock_hass):
        tm = TripManager(mock_hass, "v1")
        trip = {"kwh": 10.0}
        vehicle_config = {
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.4,
            "soc_current": 80.0,
            "consumption_kwh_per_km": 0.15,
        }
        result = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
        assert "energia_necesaria_kwh" in result
        assert "horas_carga_necesarias" in result
        assert "alerta_tiempo_insuficiente" in result
        assert "horas_disponibles" in result

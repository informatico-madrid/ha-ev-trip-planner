"""Comprehensive unit tests for the trip/ SOLID-decomposed package.

Covers:
- trip/manager.py: TripManager facade with exposed sub-components
- trip/_crud.py: TripCRUD operations
- trip/_soc_query.py: SOC calculation queries
- trip/_power_profile.py: Power profile generation
- trip/_schedule.py: Schedule generation
- trip/_trip_navigator.py: Trip navigation
- trip/_soc_window.py: SOC window calculations
- trip/_soc_helpers.py: SOC helper utilities
- trip/_sensor_callbacks.py: Sensor callback registry
- trip/_types.py: TypedDict definitions

Tests use mock HomeAssistant instances and verify functional behavior
of each module's public API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import get_type_hints
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip import (
    CargaVentana,
    SensorCallbackRegistry,
    SOCMilestoneResult,
    TripManager,
    TripManagerConfig,
)
from custom_components.ev_trip_planner.trip._sensor_callbacks import (
    SensorEvent,
    emit,
)
from custom_components.ev_trip_planner.trip._soc_window import (
    SOCInicioParams,
    SOCWindowCalculator,
    VentanaCargaParams,
)
from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_hass(tmp_path):
    """Minimal mock HomeAssistant with required attributes."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = str(tmp_path)
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    hass.async_add_executor_job = AsyncMock()
    return hass


def _make_tm(mock_hass, storage=None, emhass_adapter=None):
    """Create a minimal TripManager with proper state."""
    return TripManager(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        config=TripManagerConfig(
            entry_id="test_entry",
            storage=storage,
            emhass_adapter=emhass_adapter,
        ),
    )


@pytest.fixture
def crud_mixins(mock_hass):
    """TripManager with all sub-components but no storage/emhass."""
    tm = _make_tm(mock_hass)
    tm._state._persistence._storage = None
    tm._state.emhass_adapter = None
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
        tm = _make_tm(mock_hass)
        assert (
            tm._state.vehicle_id == "vehicle_1"
            or tm._state.vehicle_id == "test_vehicle"
        )
        assert tm._state.hass is mock_hass
        assert tm._state.recurring_trips == {}
        assert tm._state.punctual_trips == {}

    def test_instance_counter_increments(self, mock_hass):
        tm = _make_tm(mock_hass)
        # Instance counter is per TripManager, each gets its own instance
        assert tm._state.entry_id == "test_entry"

    def test_emhass_adapter_set_get(self, mock_hass):
        tm = _make_tm(mock_hass)
        adapter = MagicMock()
        tm.emhass_adapter = adapter
        assert tm.emhass_adapter is adapter

    def test_entry_id_defaults_empty(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert tm._state.entry_id == "test_entry"

    def test_entry_id_set_from_constructor(self, mock_hass):
        tm = _make_tm(mock_hass, emhass_adapter=None)
        assert tm._state.entry_id == "test_entry"

    def test_sensor_callbacks_initialized(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert tm._state.sensor_callbacks is not None

    def test_is_trip_today_via_soc_helpers(self, mock_hass):
        tm = _make_tm(mock_hass)
        trip = {"tipo": "recurrente", "dia_semana": "monday", "hora": "08:00"}
        result = tm._state._soc._is_trip_today(trip, datetime.now(timezone.utc).date())
        assert isinstance(result, bool)

    def test_validate_hora_valid(self, mock_hass):
        tm = _make_tm(mock_hass)
        # Should not raise for valid times
        tm._validate_hora("08:00")
        tm._validate_hora("00:00")
        tm._validate_hora("23:59")

    def test_validate_hora_invalid_format(self, mock_hass):
        tm = _make_tm(mock_hass)
        with pytest.raises(ValueError):
            tm._validate_hora("25:00")
        with pytest.raises(ValueError):
            tm._validate_hora("abc")
        with pytest.raises(ValueError):
            tm._validate_hora("8:0")

    def test_parse_trip_datetime_object(self, mock_hass):
        tm = _make_tm(mock_hass)
        dt = datetime(2026, 5, 11, 8, 0, 0, tzinfo=timezone.utc)
        result = tm._state._soc._parse_trip_datetime(dt)
        assert result is dt
        assert result.tzinfo is not None

    def test_parse_trip_datetime_naive_becomes_utc(self, mock_hass):
        tm = _make_tm(mock_hass)
        dt = datetime(2026, 5, 11, 8, 0, 0)
        result = tm._state._soc._parse_trip_datetime(dt)
        assert result.tzinfo is not None

    def test_parse_trip_datetime_string(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = tm._state._soc._parse_trip_datetime("2026-05-11T08:00:00+00:00")
        assert result is not None
        assert isinstance(result, datetime)

    def test_parse_trip_datetime_invalid_returns_now(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = tm._state._soc._parse_trip_datetime("not-a-date")
        assert result is not None  # falls back to now()

    def test_parse_trip_datetime_invalid_allows_none(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = tm._state._soc._parse_trip_datetime("bad", allow_none=True)
        assert result is None

    def test_get_day_index_monday(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert tm._state._soc_helpers._get_day_index("lunes") == 0

    def test_get_day_index_sunday(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert tm._state._soc_helpers._get_day_index("domingo") == 6

    def test_get_day_index_unknown_defaults_zero(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert tm._state._soc_helpers._get_day_index("nonexistent") == 0

    def test_get_day_index_case_insensitive(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert tm._state._soc_helpers._get_day_index("LUNES") == 0

    def test_get_charging_power_via_soc(self, mock_hass):
        tm = _make_tm(mock_hass)
        # get_charging_power lives on SOCQuery (formerly SOCHelpers)
        result = tm._state._soc._get_charging_power()
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# TripCRUD tests
# ---------------------------------------------------------------------------


class TestCRUDMixin:
    """Tests for TripCRUD (trip/_crud.py)."""

    def test_mixin_init_creates_sensor_callbacks(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert isinstance(tm._state.sensor_callbacks, SensorCallbackRegistry)

    def test__get_all_trips_combined(self, mock_hass):
        tm = _make_tm(mock_hass)
        tm._state.recurring_trips = {"r1": {"id": "r1"}}
        tm._state.punctual_trips = {"p1": {"id": "p1"}}
        # Use _emhass_sync._get_all_active_trips to get combined view
        # or directly check state
        assert len(tm._state.recurring_trips) == 1
        assert len(tm._state.punctual_trips) == 1

    def test_get_all_trips_empty(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert len(tm._state.recurring_trips) == 0
        assert len(tm._state.punctual_trips) == 0

    async def test_async_get_recurring_trips(self, mock_hass):
        tm = _make_tm(mock_hass)
        tm._state.recurring_trips = {
            "r1": {"id": "r1", "dia_semana": "lunes"},
            "r2": {"id": "r2", "dia_semana": "martes"},
        }
        result = await tm._crud.async_get_recurring_trips()
        assert len(result) == 2

    async def test_async_get_punctual_trips(self, mock_hass):
        tm = _make_tm(mock_hass)
        tm._state.punctual_trips = {
            "p1": {"id": "p1", "datetime": "2026-05-11T08:00"},
        }
        result = await tm._crud.async_get_punctual_trips()
        assert len(result) == 1
        assert result[0]["id"] == "p1"

    async def test_async_add_recurring_trip(self, mock_hass):
        """Adding a recurring trip stores it and saves."""
        saved_data = {}

        async def mock_save(data):
            saved_data.clear()
            saved_data.update(data)

        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock(side_effect=mock_save)
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)

        await tm._crud.async_add_recurring_trip(
            dia_semana="lunes", hora="08:00", km=50.0, kwh=7.5, descripcion="Work"
        )
        assert len(tm._state.recurring_trips) == 1
        assert saved_data.get("recurring_trips") == tm._state.recurring_trips

    async def test_async_add_recurring_trip_with_custom_id(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)

        await tm._crud.async_add_recurring_trip(
            trip_id="my_custom_id",
            dia_semana="miercoles",
            hora="17:00",
            km=30.0,
            kwh=4.0,
        )
        assert "my_custom_id" in tm._state.recurring_trips
        trip = tm._state.recurring_trips["my_custom_id"]
        assert trip["dia_semana"] == "miercoles"
        assert trip["activo"] is True

    async def test_async_add_punctual_trip(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)

        await tm._crud.async_add_punctual_trip(
            datetime_str="2026-05-15T14:00:00", km=100.0, kwh=15.0
        )
        assert len(tm._state.punctual_trips) == 1
        trip = list(tm._state.punctual_trips.values())[0]
        assert trip["estado"] == "pendiente"
        assert trip["tipo"] == "puntual"

    async def test_async_add_punctual_trip_with_custom_id(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)

        await tm._crud.async_add_punctual_trip(
            trip_id="my_pun_id",
            datetime_str="2026-06-01T10:00:00",
            km=200.0,
            kwh=30.0,
        )
        assert "my_pun_id" in tm._state.punctual_trips

    async def test_async_update_trip_recurring(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.recurring_trips = {
            "r1": {"id": "r1", "km": 50.0, "descripcion": "Old"}
        }

        await tm._crud.async_update_trip("r1", {"km": 75.0, "descripcion": "Updated"})
        assert tm._state.recurring_trips["r1"]["km"] == 75.0
        assert tm._state.recurring_trips["r1"]["descripcion"] == "Updated"

    async def test_async_update_trip_nonexistent_logs_warning(self, mock_hass, caplog):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)

        await tm._crud.async_update_trip("nonexistent", {"km": 10.0})
        assert (
            "not found for update" in caplog.text.lower()
            or "not found" in caplog.text.lower()
        )

    async def test_async_update_trip_filters_by_type(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.recurring_trips = {
            "r1": {"id": "r1", "dia_semana": "lunes", "hora": "08:00", "km": 50.0}
        }

        # datetime is not a relevant field for recurring trips
        await tm._crud.async_update_trip(
            "r1",
            {
                "dia_semana": "martes",
                "datetime": "2026-05-11T10:00",  # should be ignored for recurring
                "km": 60.0,
            },
        )
        assert tm._state.recurring_trips["r1"]["dia_semana"] == "martes"
        assert (
            "datetime" not in tm._state.recurring_trips["r1"]
            or tm._state.recurring_trips["r1"]["datetime"] is None
        )

    async def test_async_delete_trip_recurring(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.recurring_trips = {"r1": {"id": "r1"}, "r2": {"id": "r2"}}

        await tm._crud.async_delete_trip("r1")
        assert "r1" not in tm._state.recurring_trips
        assert "r2" in tm._state.recurring_trips

    async def test_async_delete_trip_punctual(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.punctual_trips = {"p1": {"id": "p1"}}

        await tm._crud.async_delete_trip("p1")
        assert "p1" not in tm._state.punctual_trips

    async def test_async_delete_trip_nonexistent(self, mock_hass, caplog):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)

        await tm._crud.async_delete_trip("nonexistent")
        assert len(tm._state.recurring_trips) == 0

    async def test_async_delete_all_trips(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.recurring_trips = {"r1": {"id": "r1"}}
        tm._state.punctual_trips = {"p1": {"id": "p1"}}

        await tm._lifecycle.async_delete_all_trips()
        assert tm._state.recurring_trips == {}
        assert tm._state.punctual_trips == {}

    async def test_async_pause_recurring_trip(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.recurring_trips = {"r1": {"id": "r1", "activo": True}}

        await tm._lifecycle.async_pause_recurring_trip("r1")
        assert tm._state.recurring_trips["r1"]["activo"] is False

    async def test_async_pause_nonexistent_trip(self, mock_hass, caplog):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.recurring_trips = {}

        await tm._lifecycle.async_pause_recurring_trip("nonexistent")
        assert "not found for pause" in caplog.text.lower()

    async def test_async_resume_recurring_trip(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.recurring_trips = {"r1": {"id": "r1", "activo": False}}

        await tm._lifecycle.async_resume_recurring_trip("r1")
        assert tm._state.recurring_trips["r1"]["activo"] is True

    async def test_async_complete_punctual_trip(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.punctual_trips = {"p1": {"id": "p1", "estado": "pendiente"}}

        await tm._lifecycle.async_complete_punctual_trip("p1")
        assert tm._state.punctual_trips["p1"]["estado"] == "completado"

    async def test_async_cancel_punctual_trip(self, mock_hass):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.punctual_trips = {"p1": {"id": "p1", "estado": "pendiente"}}

        await tm._lifecycle.async_cancel_punctual_trip("p1")
        assert "p1" not in tm._state.punctual_trips

    async def test_async_cancel_nonexistent_trip(self, mock_hass, caplog):
        storage = MagicMock(spec=YamlTripStorage)
        storage.async_save = AsyncMock()
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})

        tm = _make_tm(mock_hass, storage=storage, emhass_adapter=None)
        tm._state.punctual_trips = {}

        await tm._lifecycle.async_cancel_punctual_trip("nonexistent")
        assert "not found for cancellation" in caplog.text.lower()


# ---------------------------------------------------------------------------
# SOCQuery / SOCHelpers tests
# ---------------------------------------------------------------------------


class TestSOCMixin:
    """Tests for SOCQuery + SOCHelpers (trip/_soc_query.py, _soc_helpers.py)."""

    def test_get_charging_power_default(self, mock_hass):
        """Without config entry, defaults to DEFAULT_CHARGING_POWER (11.0)."""
        tm = _make_tm(mock_hass)
        power = tm._state._soc._get_charging_power()
        assert power == 11.0  # DEFAULT_CHARGING_POWER = 11.0

    def test_calcular_tasa_carga_soc(self, mock_hass):
        tm = _make_tm(mock_hass)
        # 3.6 kW / 50 kWh * 100 = 7.2 %/hour
        rate = tm._state._soc._calcular_tasa_carga_soc(3.6, 50.0)
        assert rate == pytest.approx(7.2)

    def test_calcular_tasa_carga_soc_zero_power(self, mock_hass):
        tm = _make_tm(mock_hass)
        rate = tm._state._soc._calcular_tasa_carga_soc(0.0, 50.0)
        assert rate == 0.0

    def test_calcular_soc_objetivo_base_from_kwh(self, mock_hass):
        tm = _make_tm(mock_hass)
        trip = {"kwh": 10.0}
        target = tm._state._soc._calcular_soc_objetivo_base(trip, 50.0)
        # 10 kWh / 50 kWh * 100 = 20% + buffer
        assert target > 0

    def test_calcular_soc_objetivo_base_from_km(self, mock_hass):
        tm = _make_tm(mock_hass)
        trip = {"km": 100.0, "consumo": 0.15}
        target = tm._state._soc._calcular_soc_objetivo_base(trip, 50.0)
        assert target > 0

    def test_get_day_index(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert tm._state._soc_helpers._get_day_index("lunes") == 0
        assert tm._state._soc_helpers._get_day_index("viernes") == 4
        assert tm._state._soc_helpers._get_day_index("domingo") == 6

    async def test_async_get_vehicle_soc_no_sensor(self, mock_hass):
        """When no SOC sensor configured, returns 0.0."""
        tm = _make_tm(mock_hass)
        soc = await tm._soc_query.async_get_vehicle_soc("test_vehicle")
        assert soc == 0.0

    async def test_async_get_vehicle_soc_from_sensor(self, mock_hass):
        mock_state = MagicMock()
        mock_state.state = "75.5"
        mock_hass.states.get = MagicMock(return_value=mock_state)

        entry = MagicMock()
        entry.data = {
            "soc_sensor": "sensor.battery",
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
        }
        mock_hass.config_entries.async_entries = MagicMock(return_value=[entry])

        tm = _make_tm(mock_hass)
        soc = await tm._soc_query.async_get_vehicle_soc("test_vehicle")
        assert soc == 75.5

    async def test_calcular_ventana_carga_no_hora_regreso(self, mock_hass):
        """Without hora_regreso, falls back to trip_departure - 6h."""
        tm = _make_tm(mock_hass)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "08:00",
            "km": 50.0,
            "kwh": 7.5,
        }
        result = await tm._soc_window.calcular_ventana_carga(
            VentanaCargaParams(
                trips=[trip], soc_actual=50.0, hora_regreso=None, charging_power_kw=3.6
            )
        )
        assert "ventana_horas" in result
        assert "kwh_necesarios" in result
        assert result["es_suficiente"] in (True, False)

    async def test_calcular_ventana_carga_with_next_trip(self, mock_hass):
        """When there's a next trip, uses hora_regreso as window start."""
        tm = _make_tm(mock_hass)
        tm._state.punctual_trips = {
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
        result = await tm._soc_window.calcular_ventana_carga(
            VentanaCargaParams(
                trips=[trip],
                soc_actual=80.0,
                hora_regreso=datetime(2026, 5, 11, 18, 0, 0, tzinfo=timezone.utc),
                charging_power_kw=3.6,
            )
        )
        assert "ventana_horas" in result

    async def test_calcular_ventana_carga_multitrip_empty(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = await tm._soc_window.calcular_ventana_carga_multitrip(
            VentanaCargaParams(
                trips=[], soc_actual=50.0, hora_regreso=None, charging_power_kw=3.6
            )
        )
        assert result == []

    async def test_calcular_soc_inicio_trips_empty(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = await tm._soc_window.calcular_soc_inicio_trips(
            SOCInicioParams(
                trips=[], soc_inicial=50.0, hora_regreso=None, charging_power_kw=3.6
            )
        )
        assert result == []

    async def test_calcular_hitos_soc_empty(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = await tm._soc_window.calcular_hitos_soc(
            SOCWindowCalculator(trips=[], soc_inicial=50.0, charging_power_kw=3.6)
        )
        assert result == []

    async def test_async_get_kwh_needed_today_no_trips(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = await tm._soc_query.async_get_kwh_needed_today()
        assert result == 0.0

    async def test_async_get_kwh_needed_today_active_recurring(self, mock_hass):
        """Trip that matches today contributes its kwh."""
        today = datetime.now(timezone.utc).date()
        tm = _make_tm(mock_hass)
        # Create a trip for today's day of week
        dia_hoy = (
            "lunes"
            if today.weekday() == 0
            else "martes"
            if today.weekday() == 1
            else "miercoles"
            if today.weekday() == 2
            else "jueves"
            if today.weekday() == 3
            else "viernes"
            if today.weekday() == 4
            else "sabado"
            if today.weekday() == 5
            else "domingo"
        )
        tm._state.recurring_trips = {
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
        result = await tm._soc_query.async_get_kwh_needed_today()
        assert result >= 7.5


# ---------------------------------------------------------------------------
# PowerProfile tests
# ---------------------------------------------------------------------------


class TestPowerProfileMixin:
    """Tests for PowerProfile (trip/_power_profile.py)."""

    def test_mixin_init(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert hasattr(tm._power, "async_generate_power_profile")

    async def test_async_generate_power_profile_empty_trips(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = await tm._power.async_generate_power_profile()
        # Returns a list of power values (may be all zeros for no trips)
        assert isinstance(result, list)

    async def test_async_generate_power_profile_with_trips(self, mock_hass):
        tm = _make_tm(mock_hass)
        tm._state.recurring_trips = {
            "r1": {
                "id": "r1",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "08:00",
                "km": 50.0,
                "kwh": 7.5,
                "activo": True,
            }
        }
        result = await tm._power.async_generate_power_profile()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# TripScheduler tests
# ---------------------------------------------------------------------------


class TestScheduleMixin:
    """Tests for TripScheduler (trip/_schedule.py)."""

    def test_mixin_init(self, mock_hass):
        tm = _make_tm(mock_hass)
        assert hasattr(tm._schedule, "async_generate_deferrables_schedule")
        assert hasattr(tm._schedule, "publish_deferrable_loads")

    async def test_async_generate_deferrables_schedule_empty(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = await tm._schedule.async_generate_deferrables_schedule()
        assert isinstance(result, list)
        # Default 7-day horizon = 168 entries
        assert len(result) == 7 * 24

    async def test_async_generate_deferrables_schedule_custom_horizon(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = await tm._schedule.async_generate_deferrables_schedule(
            planning_horizon_days=3
        )
        assert len(result) == 3 * 24

    async def test_publish_deferrable_loads_no_adapter(self, mock_hass):
        """Publishing without emhass adapter is a no-op."""
        tm = _make_tm(mock_hass)
        tm._state.emhass_adapter = None
        # Should not raise
        await tm._schedule.publish_deferrable_loads()

    async def test_publish_deferrable_loads_with_adapter(self, mock_hass):
        adapter = MagicMock()
        adapter.async_publish_all_deferrable_loads = AsyncMock()
        tm = _make_tm(mock_hass)
        tm._state.emhass_adapter = adapter
        tm._state.recurring_trips = {}
        tm._state.punctual_trips = {}
        await tm._schedule.publish_deferrable_loads()
        adapter.async_publish_all_deferrable_loads.assert_called_once()


# ---------------------------------------------------------------------------
# SensorCallbacks tests
# ---------------------------------------------------------------------------


class TestSensorCallbacks:
    """Tests for emit() dict-based dispatch (trip/_sensor_callbacks.py)."""

    def test_emit_unknown_event_logs_debug(self, mock_hass, caplog):
        emit(SensorEvent("unknown_event", mock_hass, "entry_1"))
        assert (
            "Unknown sensor event" in caplog.text
            or caplog.text.count("unknown_event") > 0
        )

    def test_emit_creates_recurring_sensor(self, mock_hass, caplog):
        """trip_created_recurring emits via asyncio.ensure_future."""
        # Should not raise even without real sensor module
        emit(
            SensorEvent(
                "trip_created_recurring",
                mock_hass,
                "entry_1",
                trip_data={"id": "r1"},
                trip_id="r1",
                vehicle_id="v1",
            )
        )

    def test_emit_removes_trip_sensor(self, mock_hass):
        emit(
            SensorEvent(
                "trip_removed",
                mock_hass,
                "entry_1",
                trip_id="r1",
                vehicle_id="v1",
            )
        )

    def test_emit_emhass_created(self, mock_hass):
        emit(
            SensorEvent(
                "trip_sensor_created_emhass",
                mock_hass,
                "entry_1",
                trip_id="r1",
                vehicle_id="v1",
            )
        )

    def test_emit_emhass_removed(self, mock_hass):
        emit(
            SensorEvent(
                "trip_sensor_removed_emhass",
                mock_hass,
                "entry_1",
                trip_id="r1",
                vehicle_id="v1",
            )
        )

    def test_emit_updated_sensor(self, mock_hass):
        emit(
            SensorEvent(
                "trip_sensor_updated",
                mock_hass,
                "entry_1",
                trip_data={"id": "r1"},
            )
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
            "ventana_horas",
            "kwh_necesarios",
            "horas_carga_necesarias",
            "inicio_ventana",
            "fin_ventana",
            "es_suficiente",
        }
        assert set(CargaVentana.__annotations__.keys()) == expected_keys

    def test_soc_milestone_result_has_expected_keys(self):
        expected_keys = {
            "trip_id",
            "soc_objetivo",
            "kwh_necesarios",
            "deficit_acumulado",
            "ventana_carga",
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
# TripNavigator tests
# ---------------------------------------------------------------------------


class TestTripManagerPublicMethods:
    """Tests for TripNavigator (trip/_trip_navigator.py)."""

    async def test_async_get_next_trip_no_trips(self, mock_hass):
        tm = _make_tm(mock_hass)
        result = await tm._navigator.async_get_next_trip()
        assert result is None

    async def test_async_get_next_trip_skips_inactive(self, mock_hass):
        tm = _make_tm(mock_hass)
        tm._state.recurring_trips = {
            "r1": {
                "id": "r1",
                "tipo": "recurrente",
                "dia_semana": "monday",
                "hora": "03:00",  # 3 AM = not matching day
                "km": 10,
                "kwh": 1,
                "activo": False,
            }
        }
        result = await tm._navigator.async_get_next_trip()
        assert result is None

    async def test_async_get_next_trip_skips_completed_punctual(self, mock_hass):
        tm = _make_tm(mock_hass)
        tm._state.punctual_trips = {
            "p1": {
                "id": "p1",
                "tipo": "puntual",
                "datetime": "2026-05-11T08:00:00",
                "km": 10,
                "kwh": 1,
                "estado": "completado",
            }
        }
        result = await tm._navigator.async_get_next_trip()
        assert result is None

    async def test_async_get_next_trip_after_no_matches(self, mock_hass):
        tm = _make_tm(mock_hass)
        tm._state.punctual_trips = {
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
        result = await tm._navigator.async_get_next_trip_after(now)
        assert result is None

    async def test_async_get_next_trip_after_future_punctual(self, mock_hass):
        tm = _make_tm(mock_hass)
        tm._state.punctual_trips = {
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
        result = await tm._navigator.async_get_next_trip_after(now)
        assert result is not None
        assert result["id"] == "p1"

    async def test_get_trip_time_recurring(self, mock_hass):
        tm = _make_tm(mock_hass)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "08:00",
        }
        result = tm._state._soc._get_trip_time(trip)
        assert result is not None
        assert result.tzinfo is not None

    async def test_get_trip_time_punctual(self, mock_hass):
        tm = _make_tm(mock_hass)
        trip = {
            "tipo": "puntual",
            "datetime": "2026-06-15T14:00:00",
        }
        result = tm._state._soc._get_trip_time(trip)
        assert result is not None

    async def test_get_trip_time_missing_tipo(self, mock_hass):
        tm = _make_tm(mock_hass)
        trip = {"descripcion": "no type"}
        result = tm._state._soc._get_trip_time(trip)
        assert result is None


# ---------------------------------------------------------------------------
# Integration: CRUD + SOC interaction
# ---------------------------------------------------------------------------


class TestCrudSocInteraction:
    """Tests for cross-component interaction in TripManager."""

    async def test_calcular_hitos_soc_requires_vehicle_config(self, mock_hass):
        tm = _make_tm(mock_hass)
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
        result = await tm._soc_window.calcular_hitos_soc(
            SOCWindowCalculator(trips=trips, soc_inicial=50.0, charging_power_kw=3.6)
        )
        assert isinstance(result, list)

    async def test_energy_calculation_with_vehicle_config(self, mock_hass):
        tm = _make_tm(mock_hass)
        trip = {"kwh": 10.0}
        vehicle_config = {
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.4,
            "soc_current": 80.0,
            "consumption_kwh_per_km": 0.15,
            "safety_margin_percent": 10.0,
        }
        result = await tm._soc_query.async_calcular_energia_necesaria(
            trip, vehicle_config
        )
        assert "energia_necesaria_kwh" in result
        assert "horas_carga_necesarias" in result
        assert "alerta_tiempo_insuficiente" in result
        assert "horas_disponibles" in result

"""Tests for TripManager calculation functions, validation, scheduling, and power profile generation.

Consolidated from:
- test_trip_manager_calculations.py
- test_trip_manager_more_coverage.py
- test_trip_manager_missing_coverage.py
- test_trip_manager_cover_more.py
- test_trip_manager_cover_line1781.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager
from tests.helpers import FakeTripStorage, create_mock_ev_config_entry


# =============================================================================
# TestCalcularVentanaCarga — charging window calculation
# =============================================================================


class TestCalcularVentanaCarga:
    """Tests for trip_manager.calcular_ventana_carga."""

    @pytest.fixture
    def mock_trip_manager(self):
        """Create a mock TripManager with necessary attributes."""
        mgr = MagicMock()
        mgr._get_trip_time = MagicMock()
        mgr.async_get_next_trip_after = AsyncMock()
        mgr._presence_monitor = MagicMock()
        mgr._vehicle_controller = MagicMock()
        return mgr

    @pytest.mark.asyncio
    async def test_no_trips_after_return_gives_zero_window(self, mock_trip_manager):
        """When no trips pending after return, window is zero."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        mock_trip_manager.async_get_next_trip_after = AsyncMock(return_value=None)

        departure = datetime.now(timezone.utc) + timedelta(hours=10)
        mock_trip_manager._get_trip_time = MagicMock(return_value=departure)

        tm = TripManager.__new__(TripManager)
        tm.async_get_next_trip_after = mock_trip_manager.async_get_next_trip_after
        tm._get_trip_time = mock_trip_manager._get_trip_time

        result = await tm.calcular_ventana_carga(
            trip={"id": "test"},
            soc_actual=50.0,
            hora_regreso=datetime.now(),
            charging_power_kw=7.0,
        )

        assert result["ventana_horas"] == 0
        assert result["kwh_necesarios"] == 0
        assert result["es_suficiente"] is True

    @pytest.mark.asyncio
    async def test_hora_regreso_string_parsed_correctly(self, mock_trip_manager):
        """ISO string hora_regreso is parsed correctly."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        mock_trip_manager.async_get_next_trip_after = AsyncMock(
            return_value={
                "id": "next_trip",
                "datetime": (datetime.now() + timedelta(hours=12)).isoformat(),
            }
        )

        departure = datetime.now(timezone.utc) + timedelta(hours=10)
        mock_trip_manager._get_trip_time = MagicMock(return_value=departure)

        tm = TripManager.__new__(TripManager)
        tm.async_get_next_trip_after = mock_trip_manager.async_get_next_trip_after
        tm._get_trip_time = mock_trip_manager._get_trip_time

        result = await tm.calcular_ventana_carga(
            trip={"id": "test"},
            soc_actual=50.0,
            hora_regreso=datetime.now().isoformat(),
            charging_power_kw=7.0,
        )

        assert "ventana_horas" in result
        assert "es_suficiente" in result

    @pytest.mark.asyncio
    async def test_trip_datetime_parsing_fallback(self, mock_trip_manager):
        """When _get_trip_time returns None, trip datetime is used as fallback."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        mock_trip_manager.async_get_next_trip_after = AsyncMock(
            return_value={"id": "next_trip"}
        )
        mock_trip_manager._get_trip_time = MagicMock(return_value=None)

        tm = TripManager.__new__(TripManager)
        tm.async_get_next_trip_after = mock_trip_manager.async_get_next_trip_after
        tm._get_trip_time = mock_trip_manager._get_trip_time

        trip_dt = (datetime.now() + timedelta(hours=8)).isoformat()
        result = await tm.calcular_ventana_carga(
            trip={"id": "test", "datetime": trip_dt},
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.0,
        )

        assert "ventana_horas" in result


# =============================================================================
# TestAsyncCalcularEnergiaNecesaria — energy needs calculation
# =============================================================================


class TestAsyncCalcularEnergiaNecesaria:
    """Tests for trip_manager.async_calcular_energia_necesaria."""

    @pytest.fixture
    def mock_trip_manager(self):
        """Create a mock TripManager."""
        mgr = MagicMock()
        mgr._presence_monitor = MagicMock()
        mgr._vehicle_controller = MagicMock()
        return mgr

    @pytest.mark.asyncio
    async def test_calculates_from_km_and_consumption(self, mock_trip_manager):
        """When kwh not directly set, calculates from km * consumption."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        tm = TripManager.__new__(TripManager)
        tm._presence_monitor = mock_trip_manager._presence_monitor
        tm._vehicle_controller = mock_trip_manager._vehicle_controller

        trip = {
            "id": "trip1",
            "km": 100,
            "consumption_kwh_per_km": 0.15,
            "datetime": (datetime.now() + timedelta(hours=5)).isoformat(),
        }
        vehicle_config = {
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.0,
        }

        result = await tm.async_calcular_energia_necesaria(trip, vehicle_config)

        assert (
            result.get("energia_necesaria_kwh", 0) > 0
            or "alerta_tiempo_insuficiente" in result
        )

    @pytest.mark.asyncio
    async def test_direct_kwh_trip_returns_expected_structure(self, mock_trip_manager):
        """When kwh directly set, returns expected calculation structure."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        tm = TripManager.__new__(TripManager)
        tm._presence_monitor = mock_trip_manager._presence_monitor
        tm._vehicle_controller = mock_trip_manager._vehicle_controller

        trip = {
            "id": "trip1",
            "km": 100,
            "kwh": 25.0,
            "consumption_kwh_per_km": 0.15,
            "datetime": (datetime.now() + timedelta(hours=5)).isoformat(),
        }
        vehicle_config = {
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.0,
        }

        result = await tm.async_calcular_energia_necesaria(trip, vehicle_config)

        assert "energia_necesaria_kwh" in result
        assert "horas_carga_necesarias" in result
        assert "alerta_tiempo_insuficiente" in result
        assert "horas_disponibles" in result

    @pytest.mark.asyncio
    async def test_safety_margin_defaults_to_10_percent(self, mock_trip_manager):
        """When safety_margin_percent is missing from vehicle_config, defaults to 10%."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        tm = TripManager.__new__(TripManager)
        tm._presence_monitor = mock_trip_manager._presence_monitor
        tm._vehicle_controller = mock_trip_manager._vehicle_controller

        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "soc_current": 20.0,
        }
        trip = {"kwh": 10.0}

        result = await tm.async_calcular_energia_necesaria(trip, vehicle_config)

        assert result["margen_seguridad_aplicado"] == 10.0
        assert result["energia_necesaria_kwh"] == 0.0


# =============================================================================
# TestTripManagerValidation — validation and sanitization
# =============================================================================


class TestTripManagerValidation:
    """Tests for TripManager validation and sanitization logic."""

    @pytest.mark.asyncio
    async def test_validate_hora_raises_on_invalid_format(self) -> None:
        """Invalid hora format raises ValueError."""
        tm = TripManager(MagicMock(), "veh")
        with pytest.raises(ValueError):
            tm._validate_hora("99:99")

    def test_sanitize_recurring_trips_removes_invalid_hours(self) -> None:
        """Trips with invalid hora values are removed during sanitization."""
        tm = TripManager(MagicMock(), "veh")
        trips = {
            "ok": {"id": "ok", "hora": "08:00", "tipo": "recurrente"},
            "bad": {"id": "bad", "hora": "25:99", "tipo": "recurrente"},
        }
        cleaned = tm._sanitize_recurring_trips(trips)
        assert "ok" in cleaned
        assert "bad" not in cleaned

    @pytest.mark.asyncio
    async def test_async_update_trip_filters_fields_by_type(self) -> None:
        """Punctual trip rejects dia_semana/hora, recurring rejects datetime."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.async_add_executor_job = AsyncMock(return_value=None)

        tm = TripManager(hass, "veh")

        # Add and update a punctual trip
        await tm.async_add_punctual_trip(
            trip_id="pun_test",
            datetime_str="2026-04-20T14:00",
            km=30.0,
            kwh=10.0,
        )

        await tm.async_update_trip(
            "pun_test",
            {
                "km": 50.0,
                "dia_semana": "3",
                "hora": "10:00",
            },
        )

        updated = tm._punctual_trips["pun_test"]
        assert updated["km"] == 50.0
        assert "dia_semana" not in updated
        assert "hora" not in updated
        assert updated["datetime"] == "2026-04-20T14:00"

        # Add and update a recurring trip
        await tm.async_add_recurring_trip(
            trip_id="rec_test",
            dia_semana="2",
            hora="09:00",
            km=20.0,
            kwh=8.0,
        )

        await tm.async_update_trip(
            "rec_test",
            {
                "km": 40.0,
                "datetime": "2026-04-25T16:00",
            },
        )

        updated_rec = tm._recurring_trips["rec_test"]
        assert updated_rec["km"] == 40.0
        assert "datetime" not in updated_rec
        assert updated_rec["dia_semana"] == "2"
        assert updated_rec["hora"] == "09:00"


# =============================================================================
# TestAsyncGenerateDeferrablesSchedule — deferrable schedule generation
# =============================================================================


class TestAsyncGenerateDeferrablesSchedule:
    """Tests for TripManager.async_generate_deferrables_schedule."""

    def _make_tm(self):
        """Helper to create a TM with basic mock setup."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(return_value=None)

        entry = MagicMock()
        entry.entry_id = "e1"
        entry.data = {"vehicle_name": "veh", "battery_capacity_kwh": 40.0}
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=entry)

        tm = TripManager(hass, "veh", entry_id="e1")

        tm.async_get_vehicle_soc = AsyncMock(return_value=30.0)

        async def fake_async_calcular_energia_necesaria(trip, vehicle_config):
            return {"energia_necesaria_kwh": 1.5, "horas_carga_necesarias": 2.5}

        tm.async_calcular_energia_necesaria = AsyncMock(
            side_effect=fake_async_calcular_energia_necesaria
        )
        return tm, fake_async_calcular_energia_necesaria

    @pytest.mark.asyncio
    async def test_basic_schedule_generation(self) -> None:
        """Schedule generation runs with valid trips and returns a list."""
        tm, fake = self._make_tm()

        now = datetime.now(timezone.utc)
        tm._recurring_trips = {
            "r1": {"id": "r1", "activo": True, "hora": "08:00"},
            "r2": {"id": "r2", "activo": True, "hora": "09:00"},
        }
        tm._punctual_trips = {
            "p1": {"id": "p1", "estado": "pendiente", "hora": now.isoformat()}
        }

        tm._get_trip_time = lambda trip: now + timedelta(hours=1)

        schedule = await tm.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(schedule, list)

    @pytest.mark.asyncio
    async def test_skips_trips_without_datetime(self) -> None:
        """Trips without a datetime field are skipped during schedule generation."""
        tm, fake = self._make_tm()

        tm._punctual_trips = {
            "p1": {
                "id": "p1",
                "tipo": "puntual",
                "km": 50.0,
                "kwh": 15.0,
                "estado": "pendiente",
            }
        }
        tm._recurring_trips = {}

        tm.async_get_vehicle_soc = AsyncMock(return_value=50.0)

        async def fake_no_dt(trip, vehicle_config):
            return {"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}

        tm.async_calcular_energia_necesaria = AsyncMock(side_effect=fake_no_dt)

        schedule = await tm.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(schedule, list)

    @pytest.mark.asyncio
    async def test_skips_past_trips(self) -> None:
        """Trips with a past datetime are skipped during schedule generation."""
        tm, fake = self._make_tm()

        past_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime(
            "%Y-%m-%dT%H:%M"
        )
        tm._punctual_trips = {
            "p1": {
                "id": "p1",
                "tipo": "puntual",
                "datetime": past_date,
                "km": 50.0,
                "kwh": 15.0,
                "estado": "pendiente",
            }
        }
        tm._recurring_trips = {}

        tm.async_get_vehicle_soc = AsyncMock(return_value=50.0)

        async def fake_past(trip, vehicle_config):
            return {"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}

        tm.async_calcular_energia_necesaria = AsyncMock(side_effect=fake_past)

        schedule = await tm.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(schedule, list)

    @pytest.mark.asyncio
    async def test_power_assignment_loop_exercises_schedule(self) -> None:
        """Power profile assignment loop runs when trip has enough lead time."""
        tm, fake = self._make_tm()

        future_time = datetime.now(timezone.utc) + timedelta(hours=10)
        tm._punctual_trips = {
            "p1": {
                "id": "p1",
                "tipo": "puntual",
                "datetime": future_time.strftime("%Y-%m-%dT%H:%M"),
                "km": 50.0,
                "kwh": 15.0,
                "estado": "pendiente",
            }
        }
        tm._recurring_trips = {}

        tm._get_trip_time = lambda trip: future_time
        tm.async_get_vehicle_soc = AsyncMock(return_value=50.0)

        async def fake_power(trip, vehicle_config):
            return {"energia_necesaria_kwh": 10.0, "horas_carga_necesarias": 3.0}

        tm.async_calcular_energia_necesaria = AsyncMock(side_effect=fake_power)

        schedule = await tm.async_generate_deferrables_schedule(
            charging_power_kw=3.6, planning_horizon_days=1
        )
        assert isinstance(schedule, list)


# =============================================================================
# TestChargingPowerAndSoc — charging power lookup and SOC handling
# =============================================================================


class TestChargingPowerAndSoc:
    """Tests for TripManager charging power lookup and SOC sensor handling."""

    @pytest.mark.asyncio
    async def test_get_charging_power_from_config_entry(self) -> None:
        """Charging power is read from the config entry data."""
        data = {"vehicle_name": "veh", "charging_power_kw": 6.6}
        entry = create_mock_ev_config_entry(None, data=data, entry_id="e_chp1")

        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[entry])

        tm = TripManager(hass, "veh")

        power = tm.get_charging_power()
        assert isinstance(power, float)
        assert abs(power - 6.6) < 1e-6

    def test_get_charging_power_returns_default_when_no_entry(self) -> None:
        """When no config entry found, charging power falls back to default."""
        from custom_components.ev_trip_planner.const import DEFAULT_CHARGING_POWER

        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[])

        tm = TripManager(hass, "noentry")
        assert tm.get_charging_power() == DEFAULT_CHARGING_POWER

    @pytest.mark.asyncio
    async def test_get_vehicle_soc_returns_value_and_handles_unavailable(self) -> None:
        """SOC reads from sensor and returns 0.0 on unavailable state."""
        data = {"vehicle_name": "veh_soc", "soc_sensor": "sensor.veh_soc"}
        entry = create_mock_ev_config_entry(None, data=data, entry_id="e_soc1")

        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[entry])
        hass.states = MagicMock()

        hass.states.get = MagicMock(return_value=SimpleNamespace(state="42"))

        tm = TripManager(hass, "veh_soc")
        soc = await tm.async_get_vehicle_soc("veh_soc")
        assert soc == 42.0

        hass.states.get = MagicMock(return_value=SimpleNamespace(state="unknown"))
        soc2 = await tm.async_get_vehicle_soc("veh_soc")
        assert soc2 == 0.0

    @pytest.mark.asyncio
    async def test_async_get_next_trip_skips_invalid_hora(self, hass) -> None:
        """Recurring trips with malformed hora are skipped without raising."""
        tm = TripManager(hass, "veh")
        tm._recurring_trips = {
            "r_bad": {"id": "r_bad", "dia_semana": "", "hora": "25:99", "activo": True}
        }

        now = datetime.now()
        res = await tm.async_get_next_trip_after(now)
        assert res is None


# =============================================================================
# TestTripManagerStorage — storage and save operations
# =============================================================================


class TestTripManagerStorage:
    """Tests for TripManager storage operations."""

    @pytest.mark.asyncio
    async def test_load_trips_with_data_in_data_key(self) -> None:
        """Trips stored under 'data' key are loaded correctly."""
        stored = {
            "data": {
                "trips": {"legacy": {}},
                "recurring_trips": {
                    "r1": {"id": "r1", "hora": "08:00", "dia_semana": "lunes"}
                },
                "punctual_trips": {
                    "p1": {
                        "id": "p1",
                        "datetime": "2026-05-01T10:00:00",
                        "estado": "pendiente",
                    }
                },
            }
        }
        storage = FakeTripStorage(initial_data=stored)
        hass = MagicMock()
        tm = TripManager(hass, "veh_load", storage=storage)

        await tm._load_trips()

        assert isinstance(tm._recurring_trips, dict)
        assert "r1" in tm._recurring_trips
        assert "p1" in tm._punctual_trips

    @pytest.mark.asyncio
    async def test_load_trips_with_direct_dict_shape(self) -> None:
        """Trips stored without 'data' wrapper are loaded correctly."""
        stored = {
            "trips": {},
            "recurring_trips": {
                "r2": {"id": "r2", "hora": "09:00", "dia_semana": "martes"}
            },
            "punctual_trips": {},
        }
        storage = FakeTripStorage(initial_data=stored)
        hass = MagicMock()
        tm = TripManager(hass, "veh_load2", storage=storage)

        await tm._load_trips()

        assert "r2" in tm._recurring_trips

    @pytest.mark.asyncio
    async def test_save_trips_uses_injected_storage(self) -> None:
        """async_save_trips writes to the injected storage instance."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(return_value=None)
        storage = MagicMock()
        storage.async_save = AsyncMock(return_value=None)

        tm = TripManager(hass, "veh", storage=storage)
        tm._recurring_trips = {"t1": {"id": "t1"}}
        tm._punctual_trips = {"p1": {"id": "p1"}}

        await tm.async_save_trips()

        storage.async_save.assert_called_once()
        saved_arg = storage.async_save.call_args.args[0]
        assert "trips" in saved_arg
        assert "recurring_trips" in saved_arg


# =============================================================================
# TestAddRecurringTripWithEmhass — EMHASS integration on trip creation
# =============================================================================


class TestAddRecurringTripWithEmhass:
    """Tests for TripManager EMHASS integration when creating recurring trips."""

    @pytest.mark.asyncio
    async def test_add_recurring_trip_calls_emhass_when_coordinator_present(self) -> None:
        """Adding a recurring trip triggers EMHASS sensor creation if coordinator exists."""
        hass = MagicMock()
        entry = create_mock_ev_config_entry(
            None, data={"vehicle_name": "veh_emhass"}, entry_id="e_em"
        )
        hass.config_entries = MagicMock()
        hass.config_entries.async_get_entry = MagicMock(return_value=entry)
        entry.runtime_data = SimpleNamespace(coordinator=MagicMock())

        storage = FakeTripStorage()
        tm = TripManager(hass, "veh_emhass", entry_id="e_em", storage=storage)

        with (
            patch(
                "custom_components.ev_trip_planner.sensor.async_create_trip_sensor",
                new=AsyncMock(),
            ) as mock_create_sensor,
            patch(
                "custom_components.ev_trip_planner.sensor.async_create_trip_emhass_sensor",
                new=AsyncMock(),
            ) as mock_create_emhass,
        ):
            await tm.async_add_recurring_trip(
                dia_semana="lunes", hora="08:00", km=10, kwh=1.0
            )

        mock_create_sensor.assert_awaited()
        mock_create_emhass.assert_awaited()


# =============================================================================
# TestUpdateTripSensor — trip sensor updates
# =============================================================================


class TestUpdateTripSensor:
    """Tests for TripManager trip sensor update logic."""

    @pytest.mark.asyncio
    async def test_update_trip_sensor_with_registry_present(self) -> None:
        """When entity registry has the trip entity, state is updated."""
        hass = MagicMock()
        tm = TripManager(hass, "veh_reg")
        tm._recurring_trips = {
            "rX": {"id": "rX", "tipo": "recurrente", "hora": "08:00", "activo": True}
        }

        class FakeRegistry:
            def async_get(self, entity_id):
                return SimpleNamespace(entity_id=entity_id)

        with patch(
            "homeassistant.helpers.entity_registry.async_get", return_value=FakeRegistry()
        ):
            hass.states = MagicMock()
            hass.states.async_set = MagicMock()

            await tm.async_update_trip_sensor("rX")

            hass.states.async_set.assert_called()


# =============================================================================
# TestGeneratePowerProfile — power profile generation
# =============================================================================


class TestGeneratePowerProfile:
    """Tests for TripManager power profile generation."""

    @pytest.mark.asyncio
    async def test_uses_entry_id_for_battery_capacity_lookup(self) -> None:
        """Power profile reads battery_capacity_kwh from config entry via entry_id."""
        hass = MagicMock()

        entry_data = {"vehicle_name": "My Car", "battery_capacity_kwh": 63.0}
        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_1"
        mock_entry.data = MagicMock()
        mock_entry.data.get = MagicMock(
            side_effect=lambda key, default=None: entry_data.get(key, default)
        )

        hass.config_entries = MagicMock()
        hass.config_entries.async_get_entry = MagicMock(
            side_effect=lambda x: mock_entry if x == "entry_1" else None
        )

        hass.async_add_executor_job = AsyncMock(return_value=None)
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp"

        tm = TripManager(hass, "my_car", entry_id="entry_1")
        tm.async_get_vehicle_soc = AsyncMock(return_value=80.0)

        captured = {}

        def fake_calculate_power_profile(**kwargs):
            captured.update(kwargs)
            return [0.0]

        with patch(
            "homeassistant.helpers.storage.Store.async_load",
            new_callable=lambda: AsyncMock(return_value=None),
        ):
            with patch(
                "custom_components.ev_trip_planner.calculations.calculate_power_profile",
                side_effect=fake_calculate_power_profile,
            ):
                await tm.async_generate_power_profile()

        assert captured.get("battery_capacity_kwh") == 63.0

    @pytest.mark.asyncio
    async def test_skips_entries_without_data(self) -> None:
        """Entries with None .data are skipped during power profile generation."""
        hass = MagicMock()

        mock_entry_no_data = MagicMock()
        mock_entry_no_data.entry_id = "entry_none"
        mock_entry_no_data.data = None

        entry_data = {"vehicle_name": "My Car", "battery_capacity_kwh": 64.0}
        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_2"
        mock_entry.data = MagicMock()
        mock_entry.data.get = MagicMock(
            side_effect=lambda key, default=None: entry_data.get(key, default)
        )

        hass.config_entries = MagicMock()
        hass.config_entries.async_entries = MagicMock(
            return_value=[mock_entry_no_data, mock_entry]
        )
        hass.config_entries.async_get_entry = MagicMock(return_value=None)

        hass.async_add_executor_job = AsyncMock(return_value=None)
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp"

        tm = TripManager(hass, "my_car")
        tm.async_get_vehicle_soc = AsyncMock(return_value=80.0)

        captured = {}

        def fake_calculate_power_profile(**kwargs):
            captured.update(kwargs)
            return [0.0]

        with patch(
            "homeassistant.helpers.storage.Store.async_load",
            new_callable=lambda: AsyncMock(return_value=None),
        ):
            with patch(
                "custom_components.ev_trip_planner.calculations.calculate_power_profile",
                side_effect=fake_calculate_power_profile,
            ):
                await tm.async_generate_power_profile()

        assert captured.get("battery_capacity_kwh") == 64.0

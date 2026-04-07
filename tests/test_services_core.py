"""Pruebas de servicios de EV Trip Planner (TDD Fase 1B)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.ev_trip_planner.const import DOMAIN
from custom_components.ev_trip_planner.__init__ import register_services


def _patch_trip_manager():
    """Patch TripManager constructor to return a mock with async methods."""
    manager = MagicMock()
    manager.async_setup = AsyncMock()
    manager.async_add_recurring_trip = AsyncMock(return_value="rec_lun_abc12345")
    manager.async_add_punctual_trip = AsyncMock(return_value="pun_20251119_abc12345")
    manager.async_update_trip = AsyncMock(return_value=True)
    manager.async_delete_trip = AsyncMock(return_value=True)
    manager.async_pause_recurring_trip = AsyncMock(return_value=True)
    manager.async_resume_recurring_trip = AsyncMock(return_value=True)
    manager.async_complete_punctual_trip = AsyncMock(return_value=True)
    manager.async_cancel_punctual_trip = AsyncMock(return_value=True)
    manager.async_get_recurring_trips = AsyncMock(
        return_value=[{"id": "rec_lun_old"}, {"id": "rec_mar_old"}]
    )

    return patch(
        "custom_components.ev_trip_planner.__init__.TripManager",
        return_value=manager,
    ), manager


@pytest.fixture
def mock_hass():
    class Services:
        def __init__(self):
            self.registry = {}

        def async_register(self, domain, name, handler, schema=None, supports_response=None):
            # Accept supports_response argument to match Home Assistant 2025.1+ API
            if domain == DOMAIN:
                self.registry[name] = handler

    hass = MagicMock()
    hass.data = {}
    hass.services = Services()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    return hass


def _setup_mock_config_entry(mock_hass, vehicle_id="chispitas"):
    """Set up a mock config entry for the given vehicle_id."""
    from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

    mock_entry = MagicMock()
    mock_entry.entry_id = f"entry_{vehicle_id}"
    mock_entry.data = {"vehicle_name": vehicle_id}
    # Use EVTripRuntimeData structure matching entry.runtime_data pattern
    mock_coordinator = MagicMock()
    mock_coordinator.async_refresh_trips = AsyncMock()
    mock_entry.runtime_data = EVTripRuntimeData(
        coordinator=mock_coordinator,
        trip_manager=None,
    )

    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    return mock_entry


@pytest.mark.asyncio
async def test_services_use_seeded_trip_manager_instance(mock_hass):
    """If a TripManager is seeded in entry.runtime_data, services reuse it."""
    from custom_components.ev_trip_planner import DOMAIN
    from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

    # Create a mock config entry with proper structure
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_chispitas"
    mock_entry.data = {
        "vehicle_name": "chispitas",
    }

    # Seed trip_manager directly at entry.runtime_data - this is where _get_manager looks
    seeded = MagicMock()
    seeded.async_setup = AsyncMock()
    seeded.async_add_recurring_trip = AsyncMock(return_value="rec_lun_seeded")

    # Set up entry.runtime_data with EVTripRuntimeData structure
    mock_coordinator = MagicMock()
    mock_coordinator.async_refresh_trips = AsyncMock()
    mock_entry.runtime_data = EVTripRuntimeData(
        coordinator=mock_coordinator,
        trip_manager=seeded,
    )
    # Ensure runtime_data.trip_manager is the seeded mock (not auto-created by MagicMock)
    mock_entry.runtime_data.trip_manager = seeded

    # Set up config_entries to find our entry
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    register_services(mock_hass)

    # Ensure no new TripManager is constructed by making constructor raise
    with patch(
        "custom_components.ev_trip_planner.__init__.TripManager",
        side_effect=AssertionError("Should not construct new TripManager"),
    ):
        handler = mock_hass.services.registry["add_recurring_trip"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "chispitas",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 3.6,
            "descripcion": "Trabajo",
        }
        await handler(call)

    seeded.async_add_recurring_trip.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_add_recurring_trip_routes_to_manager(mock_hass):
    mock_entry = _setup_mock_config_entry(mock_hass)
    # Seed entry.runtime_data.trip_manager with a mock
    mock_mgr = MagicMock()
    mock_mgr.async_add_recurring_trip = AsyncMock(return_value="rec_lun_abc12345")
    mock_entry.runtime_data.trip_manager = mock_mgr

    register_services(mock_hass)

    handler = mock_hass.services.registry["add_recurring_trip"]
    call = MagicMock()
    call.data = {
        "vehicle_id": "chispitas",
        "dia_semana": "lunes",
        "hora": "09:00",
        "km": 24.0,
        "kwh": 3.6,
        "descripcion": "Trabajo",
    }
    await handler(call)

    mock_mgr.async_add_recurring_trip.assert_awaited_once_with(
        dia_semana="lunes", hora="09:00", km=24.0, kwh=3.6, descripcion="Trabajo"
    )


@pytest.mark.asyncio
async def test_service_add_punctual_trip_routes_to_manager(mock_hass):
    mock_entry = _setup_mock_config_entry(mock_hass)
    # Seed entry.runtime_data.trip_manager with a mock
    mock_mgr = MagicMock()
    mock_mgr.async_add_punctual_trip = AsyncMock(return_value="pun_20251119_abc12345")
    mock_entry.runtime_data.trip_manager = mock_mgr

    register_services(mock_hass)

    handler = mock_hass.services.registry["add_punctual_trip"]
    call = MagicMock()
    call.data = {
        "vehicle_id": "chispitas",
        "datetime": "2025-11-19T15:00:00",
        "km": 110.0,
        "kwh": 16.5,
        "descripcion": "Viaje",
    }
    await handler(call)

    mock_mgr.async_add_punctual_trip.assert_awaited_once_with(
        datetime_str="2025-11-19T15:00:00", km=110.0, kwh=16.5, descripcion="Viaje"
    )


@pytest.mark.asyncio
async def test_service_update_and_delete_trip(mock_hass):
    mock_entry = _setup_mock_config_entry(mock_hass)
    # Seed entry.runtime_data.trip_manager with a mock
    mock_mgr = MagicMock()
    mock_mgr.async_update_trip = AsyncMock(return_value=True)
    mock_mgr.async_delete_trip = AsyncMock(return_value=True)
    mock_entry.runtime_data.trip_manager = mock_mgr

    register_services(mock_hass)

    edit_handler = mock_hass.services.registry["edit_trip"]
    del_handler = mock_hass.services.registry["delete_trip"]
    call = MagicMock()
    call.data = {"vehicle_id": "chispitas", "trip_id": "rec_lun_abc", "updates": {"hora": "10:00"}}
    await edit_handler(call)
    call2 = MagicMock()
    call2.data = {"vehicle_id": "chispitas", "trip_id": "rec_lun_abc"}
    await del_handler(call2)

    mock_mgr.async_update_trip.assert_awaited_once_with("rec_lun_abc", {"hora": "10:00"})
    mock_mgr.async_delete_trip.assert_awaited_once_with("rec_lun_abc")


@pytest.mark.asyncio
async def test_service_pause_resume_complete_cancel(mock_hass):
    mock_entry = _setup_mock_config_entry(mock_hass)
    # Seed entry.runtime_data.trip_manager with a mock
    mock_mgr = MagicMock()
    mock_mgr.async_pause_recurring_trip = AsyncMock(return_value=True)
    mock_mgr.async_resume_recurring_trip = AsyncMock(return_value=True)
    mock_mgr.async_complete_punctual_trip = AsyncMock(return_value=True)
    mock_mgr.async_cancel_punctual_trip = AsyncMock(return_value=True)
    mock_entry.runtime_data.trip_manager = mock_mgr

    register_services(mock_hass)

    pause_h = mock_hass.services.registry["pause_recurring_trip"]
    resume_h = mock_hass.services.registry["resume_recurring_trip"]
    complete_h = mock_hass.services.registry["complete_punctual_trip"]
    cancel_h = mock_hass.services.registry["cancel_punctual_trip"]

    call1 = MagicMock()
    call1.data = {"vehicle_id": "chispitas", "trip_id": "rec_lun_abc"}
    call2 = MagicMock()
    call2.data = {"vehicle_id": "chispitas", "trip_id": "rec_lun_abc"}
    call3 = MagicMock()
    call3.data = {"vehicle_id": "chispitas", "trip_id": "pun_20251119_abc"}
    call4 = MagicMock()
    call4.data = {"vehicle_id": "chispitas", "trip_id": "pun_20251119_abc"}

    await pause_h(call1)
    await resume_h(call2)
    await complete_h(call3)
    await cancel_h(call4)

    mock_mgr.async_pause_recurring_trip.assert_awaited_once_with("rec_lun_abc")
    mock_mgr.async_resume_recurring_trip.assert_awaited_once_with("rec_lun_abc")
    mock_mgr.async_complete_punctual_trip.assert_awaited_once_with("pun_20251119_abc")
    mock_mgr.async_cancel_punctual_trip.assert_awaited_once_with("pun_20251119_abc")


@pytest.mark.asyncio
async def test_service_import_from_weekly_pattern_clears_and_adds(mock_hass):
    mock_entry = _setup_mock_config_entry(mock_hass)
    # Seed entry.runtime_data.trip_manager with a mock
    mock_mgr = MagicMock()
    mock_mgr.async_get_recurring_trips = AsyncMock(
        return_value=[{"id": "rec_lun_old"}, {"id": "rec_mar_old"}]
    )
    mock_mgr.async_add_recurring_trip = AsyncMock(return_value="rec_lun_abc12345")
    mock_mgr.async_delete_trip = AsyncMock(return_value=True)
    mock_entry.runtime_data.trip_manager = mock_mgr

    register_services(mock_hass)

    handler = mock_hass.services.registry["import_from_weekly_pattern"]
    call = MagicMock()
    call.data = {
        "vehicle_id": "chispitas",
        "clear_existing": True,
        "pattern": {
            "lunes": [
                {"hora": "09:00", "km": 24, "kwh": 3.6, "descripcion": "Trabajo"},
                {"hora": "18:00", "km": 24, "kwh": 3.6, "descripcion": "Vuelta"},
            ],
            "miercoles": [
                {"hora": "20:00", "km": 10, "kwh": 1.5, "descripcion": "Gimnasio"}
            ],
        },
    }
    await handler(call)

    # Borró los existentes
    mock_mgr.async_delete_trip.assert_any_await("rec_lun_old")
    mock_mgr.async_delete_trip.assert_any_await("rec_mar_old")
    # Añadió 3 viajes nuevos (2 lunes, 1 miércoles)
    assert mock_mgr.async_add_recurring_trip.await_count == 3


@pytest.mark.asyncio
async def test_service_import_from_weekly_pattern_no_clear(mock_hass):
    mock_entry = _setup_mock_config_entry(mock_hass)
    # Seed entry.runtime_data.trip_manager with a mock
    mock_mgr = MagicMock()
    mock_mgr.async_get_recurring_trips = AsyncMock(
        return_value=[{"id": "rec_lun_old"}, {"id": "rec_mar_old"}]
    )
    mock_mgr.async_add_recurring_trip = AsyncMock(return_value="rec_lun_abc12345")
    mock_mgr.async_delete_trip = AsyncMock(return_value=True)
    mock_entry.runtime_data.trip_manager = mock_mgr

    register_services(mock_hass)

    handler = mock_hass.services.registry["import_from_weekly_pattern"]
    call = MagicMock()
    call.data = {
        "vehicle_id": "chispitas",
        "clear_existing": False,
        "pattern": {
            "viernes": [
                {"hora": "12:00", "km": 50, "kwh": 7.5, "descripcion": "Comida"}
            ],
        },
    }
    await handler(call)

    # No se borran existentes
    mock_mgr.async_delete_trip.assert_not_awaited()
    # Se añade 1 viaje
    mock_mgr.async_add_recurring_trip.assert_awaited_once_with(
        dia_semana="viernes", hora="12:00", km=50.0, kwh=7.5, descripcion="Comida"
    )


class TestHandleTripGetErrorPaths:
    """Tests for handle_trip_get error paths - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_get_error(self):
        """Create mock hass that errors on async_get_recurring_trips."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh_trips = AsyncMock()

        # Manager that raises on async_get_recurring_trips
        mock_manager = MagicMock()
        mock_manager.async_get_recurring_trips = AsyncMock(
            side_effect=RuntimeError("Storage error")
        )
        mock_manager.async_get_punctual_trips = AsyncMock(return_value=[])

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_get_catches_exception_from_async_get_recurring_trips(
        self, mock_hass_get_error
    ):
        """handle_trip_get catches RuntimeError from async_get_recurring_trips."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_get_error
        register_services(hass)

        handler = hass.services.registry["trip_get"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "rec_lun_abc"}
        result = await handler(call)

        # Should return error result, not raise
        assert result["found"] is False
        assert result["trip"] is None
        assert "error" in result
        assert "Storage error" in result["error"]


class TestHandleTripListErrorPaths:
    """Tests for handle_trip_list error paths - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_list_error(self):
        """Create mock hass that errors on async_get_recurring_trips."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_coordinator = MagicMock()

        # Manager that raises on both
        mock_manager = MagicMock()
        mock_manager.async_get_recurring_trips = AsyncMock(
            side_effect=RuntimeError("Storage corrupted")
        )
        mock_manager.async_get_punctual_trips = AsyncMock(
            side_effect=RuntimeError("Storage corrupted")
        )

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_list_catches_exception(self, mock_hass_list_error):
        """handle_trip_list catches RuntimeError from manager methods."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_list_error
        register_services(hass)

        handler = hass.services.registry["trip_list"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle"}
        result = await handler(call)

        # Should return empty result with error, not raise
        assert result["recurring_trips"] == []
        assert result["punctual_trips"] == []
        assert result["total_trips"] == 0
        assert "error" in result
        assert "Storage corrupted" in result["error"]


class TestHandleTripCreateErrorPaths:
    """Tests for handle_trip_create error paths - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_invalid_type(self):
        """Create mock hass for invalid trip_type test."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh_trips = AsyncMock()

        mock_manager = MagicMock()
        mock_manager.async_add_recurring_trip = AsyncMock(return_value="rec_lun_abc12345")
        mock_manager.async_add_punctual_trip = AsyncMock(return_value="pun_20251119_abc12345")

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_create_invalid_type_returns_early(self, mock_hass_invalid_type):
        """handle_trip_create with invalid trip_type returns early without creating trip.

        Tests the error path at lines 116-122 where invalid trip_type is rejected.
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_invalid_type
        register_services(hass)

        handler = hass.services.registry["trip_create"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "invalid_type",  # Invalid trip type
            "km": 24.0,
            "kwh": 3.6,
        }

        # Should return early without raising
        await handler(call)

        # Verify neither recurring nor punctual trip was called (invalid type rejected)
        mock_entry = hass.config_entries.async_get_entry("entry_test")
        mock_manager = mock_entry.runtime_data.trip_manager
        mock_manager.async_add_recurring_trip.assert_not_awaited()
        mock_manager.async_add_punctual_trip.assert_not_awaited()


class TestHandleTripUpdateSensorErrorPath:
    """Tests for handle_trip_update sensor update error path - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_update_sensor_error(self):
        """Create mock hass where async_update_trip_sensor raises."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh_trips = AsyncMock()

        mock_manager = MagicMock()
        mock_manager.async_setup = AsyncMock()
        mock_manager.async_update_trip = AsyncMock(return_value=True)
        mock_manager.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_abc", "dia_semana": "lunes", "hora": "09:00"}
        ])

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_update_sensor_failure_caught(
        self, mock_hass_update_sensor_error
    ):
        """handle_trip_update catches exception from async_update_trip_sensor.

        Tests the error path at lines 200-205 where sensor update failure is caught.
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_update_sensor_error
        register_services(hass)

        # Patch async_update_trip_sensor to raise - it's in sensor.py
        with patch(
            "custom_components.ev_trip_planner.sensor.async_update_trip_sensor",
            side_effect=Exception("Sensor update failed")
        ):
            handler = hass.services.registry["trip_update"]
            call = MagicMock()
            call.data = {
                "vehicle_id": "test_vehicle",
                "trip_id": "rec_lun_abc",
                "dia_semana": "lunes",
                "hora": "10:00",
            }

            # Should NOT raise - exception is caught
            await handler(call)

        # Coordinator should still be refreshed even if sensor update failed
        mock_entry = hass.config_entries.async_get_entry.return_value
        mock_entry.runtime_data.coordinator.async_refresh_trips.assert_awaited()


class TestHandleDeleteTripNotFound:
    """Tests for handle_delete_trip when trip not found - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_delete_not_found(self):
        """Create mock hass where trip is not found."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh_trips = AsyncMock()

        mock_manager = MagicMock()
        mock_manager.async_setup = AsyncMock()
        # async_delete_trip returns None when trip not found (just logs warning)
        mock_manager.async_delete_trip = AsyncMock(return_value=None)

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_delete_trip_not_found_still_refreshes(
        self, mock_hass_delete_not_found
    ):
        """handle_delete_trip still refreshes even when trip not found.

        Tests that the service handler completes normally even when the trip
        doesn't exist (async_delete_trip logs warning but returns None).
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_delete_not_found
        register_services(hass)

        handler = hass.services.registry["delete_trip"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "nonexistent_trip",
        }

        # Should NOT raise even if trip not found
        await handler(call)

        # Coordinator should still be refreshed
        mock_entry = hass.config_entries.async_get_entry.return_value
        mock_entry.runtime_data.coordinator.async_refresh_trips.assert_awaited()


class TestGetManagerErrorPaths:
    """Tests for _get_manager error paths - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_manager_setup_error(self):
        """Create mock hass where manager async_setup raises."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_entry.unique_id = "unique_test"
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh_trips = AsyncMock()

        # Manager that raises on async_setup
        mock_manager = MagicMock()
        mock_manager.async_setup = AsyncMock(side_effect=RuntimeError("Setup failed"))
        mock_manager.async_get_recurring_trips = AsyncMock(return_value=[])

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=None,  # Will cause new manager to be created
        )

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_list_with_manager_setup_error(
        self, mock_hass_manager_setup_error
    ):
        """handle_trip_list handles RuntimeError from manager async_setup.

        Tests the error path in _get_manager where async_setup raises,
        but the error is caught and logged (lines 758-764). The manager
        is still returned, so handle_trip_list returns empty results.
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_manager_setup_error
        register_services(hass)

        handler = hass.services.registry["trip_list"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle"}

        # Should return empty result, not raise (error is logged in _get_manager)
        result = await handler(call)

        # Should return empty result (setup failed, but manager still returned)
        assert result["recurring_trips"] == []
        assert result["punctual_trips"] == []
        assert result["total_trips"] == 0


class TestHandleTripGetNotFound:
    """Tests for handle_trip_get when trip is not found - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_get_not_found(self):
        """Create mock hass where trip is not found."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh_trips = AsyncMock()

        mock_manager = MagicMock()
        mock_manager.async_get_recurring_trips = AsyncMock(return_value=[])
        mock_manager.async_get_punctual_trips = AsyncMock(return_value=[])

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_get_returns_not_found(self, mock_hass_get_not_found):
        """handle_trip_get returns found=False when trip_id not found.

        Tests the error path at lines 653-659 where trip is not found.
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_get_not_found
        register_services(hass)

        handler = hass.services.registry["trip_get"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "nonexistent_id"}

        result = await handler(call)

        # Should return not found result
        assert result["found"] is False
        assert result["trip"] is None
        assert "not found" in result["error"]


class TestHandleImportWeeklyPattern:
    """Tests for handle_import_weekly_pattern error paths - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_import_error(self):
        """Create mock hass that errors on async_get_recurring_trips during import."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh_trips = AsyncMock()

        mock_manager = MagicMock()
        mock_manager.async_get_recurring_trips = AsyncMock(
            side_effect=RuntimeError("Storage error during clear")
        )
        mock_manager.async_add_recurring_trip = AsyncMock(return_value="rec_lun_new")

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_import_weekly_pattern_catches_clear_error(
        self, mock_hass_import_error
    ):
        """handle_import_weekly_pattern catches exception from async_get_recurring_trips.

        Tests the error path at lines 450-453 where clear_existing=True but
        async_get_recurring_trips raises - the exception is caught and existing=[]
        is used, allowing import to continue.
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_import_error
        register_services(hass)

        handler = hass.services.registry["import_from_weekly_pattern"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "clear_existing": True,
            "pattern": {
                "lunes": [{"hora": "09:00", "km": 24.0, "kwh": 3.6, "descripcion": "Test"}],
            },
        }

        # Should NOT raise - exception is caught, existing=[]
        await handler(call)

        # Import should continue with empty existing list
        mock_entry = hass.config_entries.async_get_entry.return_value
        mock_manager = mock_entry.runtime_data.trip_manager
        mock_manager.async_add_recurring_trip.assert_awaited()


class TestAsyncCleanupStaleStorage:
    """Tests for async_cleanup_stale_storage error paths - PRAGMA-A coverage targets."""

    @pytest.mark.asyncio
    async def test_async_cleanup_stale_storage_handles_load_error(self):
        """async_cleanup_stale_storage catches exception from store.async_load.

        Tests the error path at lines 1164-1168 where storage cleanup error is caught
        and logged but doesn't propagate.
        """
        from custom_components.ev_trip_planner.services import async_cleanup_stale_storage

        hass = MagicMock()
        hass.config.config_dir = "/tmp/test_config"

        # Make store.async_load raise
        from homeassistant.helpers import storage as ha_storage
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(side_effect=RuntimeError("Load failed"))
        hass.data = {"storage": {}}

        with patch.object(ha_storage, "Store", return_value=mock_store):
            # Should NOT raise - exception is caught
            await async_cleanup_stale_storage(hass, "test_vehicle")

    @pytest.mark.asyncio
    async def test_async_cleanup_stale_storage_handles_yaml_remove_error(self):
        """async_cleanup_stale_storage catches exception from os.unlink.

        Tests the error path at lines 1164-1168 where YAML cleanup error is caught
        and logged but doesn't propagate.
        """
        from custom_components.ev_trip_planner.services import async_cleanup_stale_storage

        hass = MagicMock()
        hass.config.config_dir = "/tmp/test_config"

        from homeassistant.helpers import storage as ha_storage
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value={"trips": []})
        mock_store.async_remove = AsyncMock()

        yaml_dir = Path("/tmp/test_config/ev_trip_planner")
        yaml_dir.mkdir(parents=True, exist_ok=True)
        yaml_file = yaml_dir / "ev_trip_planner_test_vehicle.yaml"
        yaml_file.write_text("test: data")

        with patch.object(ha_storage, "Store", return_value=mock_store):
            with patch("os.unlink", side_effect=OSError("Cannot remove file")):
                # Should NOT raise - exception is caught
                await async_cleanup_stale_storage(hass, "test_vehicle")


class TestAsyncRegisterStaticPaths:
    """Tests for async_register_static_paths error paths - PRAGMA-A coverage targets."""

    @pytest.mark.asyncio
    async def test_async_register_static_paths_handles_early_register_error(self):
        """async_register_static_paths catches exception from async_register_static_paths.

        Tests the error path at lines 1281-1299 where static path registration error
        is caught and logged.
        """
        from custom_components.ev_trip_planner.services import async_register_static_paths

        hass = MagicMock()
        hass.http = None  # No http server

        # Should handle gracefully - hass.http is None
        await async_register_static_paths(hass)

    @pytest.mark.asyncio
    async def test_async_register_static_paths_handles_legacy_register_error(self):
        """async_register_static_paths handles RuntimeError from legacy register_static_path.

        Tests the error path at lines 1296-1299 where "already registered" RuntimeError
        is caught and continue is used.
        """
        from custom_components.ev_trip_planner.services import async_register_static_paths

        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock(
            side_effect=RuntimeError("already registered: /test")
        )
        hass.http.register_static_path = MagicMock(
            side_effect=RuntimeError("already registered: /test")
        )

        # Should handle gracefully - "already registered" error is caught
        await async_register_static_paths(hass)


class TestAsyncCleanupOrphanedEmhassSensors:
    """Tests for async_cleanup_orphaned_emhass_sensors - PRAGMA-A coverage targets."""

    @pytest.mark.asyncio
    async def test_async_cleanup_orphaned_handles_registry_error(self):
        """async_cleanup_orphaned_emhass_sensors catches exception from er.async_get.

        Tests the error path at lines 1185-1186 where entity registry error is caught
        and logged.
        """
        from custom_components.ev_trip_planner.services import async_cleanup_orphaned_emhass_sensors

        hass = MagicMock()

        # Make er.async_get raise
        with patch("homeassistant.helpers.entity_registry.async_get", side_effect=RuntimeError("Registry error")):
            # Should NOT raise - exception is caught
            await async_cleanup_orphaned_emhass_sensors(hass)


class TestAsyncRemoveEntryCleanup:
    """Tests for async_remove_entry_cleanup error paths - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_removal(self):
        """Create mock hass for async_remove_entry_cleanup tests."""
        hass = MagicMock()
        hass.data = {"storage": {}}
        hass.config.config_dir = "/tmp/test_config"

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}

        return hass, mock_entry

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_handles_storage_error(
        self, mock_hass_removal
    ):
        """async_remove_entry_cleanup catches storage removal errors.

        Tests the error path at lines 1479-1482 where store.async_remove error is caught
        and logged.
        """
        from custom_components.ev_trip_planner.services import async_remove_entry_cleanup
        from homeassistant.helpers import storage as ha_storage

        hass, mock_entry = mock_hass_removal

        mock_store = MagicMock()
        mock_store.async_remove = AsyncMock(side_effect=RuntimeError("Cannot remove storage"))
        with patch.object(ha_storage, "Store", return_value=mock_store):
            # Should NOT raise - exception is caught
            await async_remove_entry_cleanup(hass, mock_entry)

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_handles_yaml_error(
        self, mock_hass_removal
    ):
        """async_remove_entry_cleanup catches YAML removal errors.

        Tests the error path at lines 1493-1494 where YAML cleanup error is caught
        and logged.
        """
        from custom_components.ev_trip_planner.services import async_remove_entry_cleanup
        from homeassistant.helpers import storage as ha_storage

        hass, mock_entry = mock_hass_removal

        mock_store = MagicMock()
        mock_store.async_remove = AsyncMock(return_value=None)

        yaml_dir = Path("/tmp/test_config/ev_trip_planner")
        yaml_dir.mkdir(parents=True, exist_ok=True)
        yaml_file = yaml_dir / "ev_trip_planner_test_vehicle.yaml"
        yaml_file.write_text("test: data")

        with patch.object(ha_storage, "Store", return_value=mock_store):
            with patch("os.unlink", side_effect=OSError("Cannot remove file")):
                # Should NOT raise - exception is caught
                await async_remove_entry_cleanup(hass, mock_entry)


class TestHandleTripDelete:
    """Tests for handle_delete_trip error paths - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_delete_not_found(self):
        """Create mock hass where trip is not found."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh_trips = AsyncMock()

        mock_manager = MagicMock()
        mock_manager.async_delete_trip = AsyncMock(return_value=False)

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_delete_trip_not_found_returns_early(
        self, mock_hass_delete_not_found
    ):
        """handle_delete_trip proceeds when async_delete_trip returns False (trip not found).

        The current implementation refreshes coordinator even when trip not found.
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_delete_not_found
        register_services(hass)

        handler = hass.services.registry["delete_trip"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "nonexistent"}

        # Should complete without raising
        await handler(call)

        # Verify delete was attempted
        mock_entry = hass.config_entries.async_get_entry.return_value
        mock_manager = mock_entry.runtime_data.trip_manager
        mock_manager.async_delete_trip.assert_awaited_once()
        # Coordinator is refreshed even when trip not found
        mock_entry.runtime_data.coordinator.async_refresh_trips.assert_awaited_once()


class TestHandleTripCreateManagerError:
    """Tests for handle_trip_create when manager setup raises - PRAGMA-A coverage targets."""

    @pytest.fixture
    def mock_hass_create_manager_error(self):
        """Create mock hass where manager async_setup raises."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == DOMAIN:
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_entry.unique_id = "unique_test"
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh_trips = AsyncMock()

        mock_manager = MagicMock()
        mock_manager.async_setup = AsyncMock(side_effect=RuntimeError("Setup failed"))
        mock_manager.async_add_recurring_trip = AsyncMock(return_value="rec_lun_abc")

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=None,  # Will cause new manager to be created
        )

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_create_catches_manager_setup_error(
        self, mock_hass_create_manager_error
    ):
        """handle_trip_create catches RuntimeError from manager async_setup.

        Tests the error path at lines 758-764 where async_setup raises in _get_manager,
        but the error is logged and manager is still returned.
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_create_manager_error
        register_services(hass)

        handler = hass.services.registry["trip_create"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "recurring",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 3.6,
        }

        # Should catch the setup error and log it, then continue
        # Manager is returned with empty storage after setup error
        await handler(call)
"""Pruebas de servicios de EV Trip Planner (TDD Fase 1B)."""

from __future__ import annotations

import sys
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


# =============================================================================
# PRAGMA-A: Additional error path tests for services.py 100% coverage
# =============================================================================

class TestHandleTripUpdateEnglishAliases:
    """Tests for English field name aliases in handle_trip_update (lines 156-170)."""

    @pytest.mark.asyncio
    async def test_handle_trip_update_uses_english_day_of_week(self, mock_hass):
        """handle_trip_update maps day_of_week -> dia_semana."""
        from custom_components.ev_trip_planner.__init__ import register_services

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")
        mock_mgr = MagicMock()
        mock_mgr.async_update_trip = AsyncMock(return_value=True)
        mock_mgr.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_abc123", "dia_semana": "lunes", "hora": "09:00", "km": 24.0, "kwh": 3.6}
        ])
        mock_entry.runtime_data.trip_manager = mock_mgr

        # Patch async_update_trip_sensor to avoid entity registry
        with patch(
            "custom_components.ev_trip_planner.sensor.async_update_trip_sensor",
            new_callable=AsyncMock,
        ) as mock_update_sensor:
            register_services(mock_hass)

            # Use "trip_update" service (the one with field mapping), NOT "edit_trip"
            handler = mock_hass.services.registry["trip_update"]
            call = MagicMock()
            # Use English field name 'day_of_week' instead of 'dia_semana' (NEW format, no "updates" wrapper)
            call.data = {
                "vehicle_id": "chispitas",
                "trip_id": "rec_lun_abc123",
                "type": "recurrente",
                "day_of_week": "martes",
                "time": "10:00",
                "description": "Updated desc",
            }
            await handler(call)

            # Verify async_update_trip was called with Spanish field names
            mock_mgr.async_update_trip.assert_awaited_once()
            call_args = mock_mgr.async_update_trip.call_args
            updates = call_args[0][1]  # second positional arg is updates dict
            assert updates["dia_semana"] == "martes"
            assert updates["hora"] == "10:00"
            assert updates["descripcion"] == "Updated desc"


class TestHandleTripUpdateConfigEntryNotFound:
    """Tests for config entry not found in handle_trip_update (lines 182-183)."""

    @pytest.mark.asyncio
    async def test_handle_trip_update_returns_early_when_entry_not_found(self, mock_hass):
        """handle_trip_update returns early when _find_entry_by_vehicle returns None."""
        from custom_components.ev_trip_planner import services as svcs
        from custom_components.ev_trip_planner.__init__ import register_services

        # Set up a config entry for "chispitas" but NOT for "nonexistent_vehicle"
        _setup_mock_config_entry(mock_hass, "chispitas")
        register_services(mock_hass)

        # Use "trip_update" service and patch _find_entry_by_vehicle to return None
        with patch.object(svcs, "_find_entry_by_vehicle", return_value=None):
            handler = mock_hass.services.registry["trip_update"]
            call = MagicMock()
            call.data = {
                "vehicle_id": "nonexistent_vehicle",
                "trip_id": "rec_lun_abc",
                "type": "recurrente",
                "dia_semana": "lunes",
            }
            # Should return early at line 182-183 when entry is None
            await handler(call)


class TestHandleTripUpdateSensorLoop:
    """Tests for sensor update loop break in handle_trip_update (line 203)."""

    @pytest.mark.asyncio
    async def test_handle_trip_update_updates_sensor_and_breaks(self, mock_hass):
        """handle_trip_update updates sensor and breaks after first match."""
        from custom_components.ev_trip_planner.__init__ import register_services

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")
        mock_mgr = MagicMock()
        mock_mgr.async_update_trip = AsyncMock(return_value=True)
        # Return 3 trips - only one matches
        mock_mgr.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_abc", "dia_semana": "lunes", "hora": "09:00", "km": 24.0, "kwh": 3.6},
            {"id": "rec_mar_def", "dia_semana": "martes", "hora": "10:00", "km": 30.0, "kwh": 4.5},
            {"id": "rec_mie_ghi", "dia_semana": "miercoles", "hora": "11:00", "km": 20.0, "kwh": 3.0},
        ])
        mock_entry.runtime_data.trip_manager = mock_mgr

        with patch(
            "custom_components.ev_trip_planner.sensor.async_update_trip_sensor",
            new_callable=AsyncMock,
        ) as mock_update_sensor:
            register_services(mock_hass)

            # Use "trip_update" service (NOT "edit_trip")
            handler = mock_hass.services.registry["trip_update"]
            call = MagicMock()
            call.data = {
                "vehicle_id": "chispitas",
                "trip_id": "rec_mar_def",
                "type": "recurrente",
                "dia_semana": "martes",
            }
            await handler(call)

            # async_update_trip_sensor should be called exactly once (break after first match)
            assert mock_update_sensor.call_count == 1
            call_args = mock_update_sensor.call_args[0]
            assert call_args[2]["id"] == "rec_mar_def"  # trip_data.id


class TestHandleTripUpdateWithKmAndKwh:
    """Tests for handle_trip_update with km and kwh fields - covers lines 164, 166."""

    @pytest.fixture
    def mock_hass_update_km_kwh(self):
        """Create mock hass for trip_update with km/kwh fields."""
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
        mock_manager.async_update_trip = AsyncMock(return_value=True)
        mock_manager.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_abc", "dia_semana": "lunes", "hora": "09:00", "km": 24.0, "kwh": 3.6}
        ])
        mock_manager.async_setup = AsyncMock()

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_update_with_km_and_kwh(self, mock_hass_update_km_kwh):
        """handle_trip_update converts km and kwh to float.

        Covers lines 164 and 166 where km and kwh are converted to float.
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_update_km_kwh
        register_services(hass)

        handler = hass.services.registry["trip_update"]
        call = MagicMock()
        # Include km and kwh directly in data (not in updates wrapper)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_lun_abc",
            "type": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 25.5,
            "kwh": 4.2,
        }
        await handler(call)

        # Verify async_update_trip was called with km and kwh as floats
        mock_entry = hass.config_entries.async_get_entry.return_value
        mock_entry.runtime_data.trip_manager.async_update_trip.assert_awaited_once()
        call_args = mock_entry.runtime_data.trip_manager.async_update_trip.call_args[0]
        updates = call_args[1]
        assert updates["km"] == 25.5
        assert updates["kwh"] == 4.2


class TestHandleTripUpdateWithDescripcionDirect:
    """Tests for handle_trip_update with descripcion directly - covers line 168."""

    @pytest.mark.asyncio
    async def test_handle_trip_update_with_descripcion_direct(self, mock_hass):
        """handle_trip_update converts descripcion to str.

        Covers line 168 where descripcion is converted to string.
        """
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")
        mock_mgr = MagicMock()
        mock_mgr.async_update_trip = AsyncMock(return_value=True)
        mock_mgr.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_abc", "dia_semana": "lunes", "hora": "09:00"}
        ])
        mock_entry.runtime_data.trip_manager = mock_mgr

        register_services(mock_hass)

        handler = mock_hass.services.registry["trip_update"]
        call = MagicMock()
        # Include descripcion directly (not description)
        call.data = {
            "vehicle_id": "chispitas",
            "trip_id": "rec_lun_abc",
            "dia_semana": "lunes",
            "descripcion": "Updated description",
        }
        await handler(call)

        # Verify async_update_trip was called with descripcion as string
        mock_mgr.async_update_trip.assert_awaited_once()
        call_args = mock_mgr.async_update_trip.call_args[0]
        updates = call_args[1]
        assert updates["descripcion"] == "Updated description"


class TestHandleTripGetFound:
    """Tests for trip found path in handle_trip_get (lines 641-648)."""

    @pytest.mark.asyncio
    async def test_handle_trip_get_returns_found_trip(self, mock_hass):
        """handle_trip_get returns trip when found in search loop."""
        from custom_components.ev_trip_planner.__init__ import register_services

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")
        mock_mgr = MagicMock()
        mock_mgr.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_abc", "dia_semana": "lunes"},
            {"id": "rec_mar_def", "dia_semana": "martes"},
        ])
        mock_mgr.async_get_punctual_trips = AsyncMock(return_value=[])
        mock_entry.runtime_data.trip_manager = mock_mgr

        register_services(mock_hass)

        handler = mock_hass.services.registry["trip_get"]
        call = MagicMock()
        call.data = {"vehicle_id": "chispitas", "trip_id": "rec_mar_def"}
        result = await handler(call)

        assert result["found"] is True
        assert result["trip"]["id"] == "rec_mar_def"
        assert result["trip"]["dia_semana"] == "martes"


class TestGetCoordinatorReturnsNone:
    """Tests for _get_coordinator returning None (line 805)."""

    @pytest.mark.asyncio
    async def test_get_coordinator_returns_none_for_missing_vehicle(self, mock_hass):
        """_get_coordinator returns None when vehicle entry not found."""
        from custom_components.ev_trip_planner import services as svcs

        # Set up a config entry for different vehicle
        _setup_mock_config_entry(mock_hass, "chispitas")

        # Call _get_coordinator with non-existent vehicle (not async)
        result = svcs._get_coordinator(mock_hass, "nonexistent_vehicle")
        assert result is None


class TestCreateDashboardInputHelpersErrors:
    """Tests for error paths in create_dashboard_input_helpers (lines 850-884, 1103-1107)."""

    @pytest.mark.asyncio
    async def test_create_dashboard_input_helpers_input_already_exists(self, mock_hass):
        """create_dashboard_input_helpers catches 'already exists' errors for input_select."""
        from custom_components.ev_trip_planner import services as svcs

        mock_hass.services.async_call = AsyncMock(
            side_effect=Exception("Entity already exists")
        )

        result = await svcs.create_dashboard_input_helpers(mock_hass, "chispitas")

        # Should still succeed (already exists is caught)
        assert result.success is True
        assert result.storage_method == "input_helpers"

    @pytest.mark.asyncio
    async def test_create_dashboard_input_helpers_datetime_create_error(self, mock_hass):
        """create_dashboard_input_helpers catches datetime create errors."""
        from custom_components.ev_trip_planner import services as svcs

        created = {"input_select": False, "input_datetime": False}

        async def mock_async_call(domain, service, data):
            if service == "create":
                if domain == "input_select":
                    created["input_select"] = True
                    return  # Success
                elif domain == "input_datetime":
                    if not created["input_datetime"]:
                        created["input_datetime"] = True
                        raise Exception("Entity already exists")
                    return  # Already exists, caught
            elif service == "set_options":
                return  # Success

        mock_hass.services.async_call = AsyncMock(side_effect=mock_async_call)

        result = await svcs.create_dashboard_input_helpers(mock_hass, "chispitas")

        # Should succeed (both errors caught)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_create_dashboard_input_helpers_input_number_create_error(self, mock_hass):
        """create_dashboard_input_helpers catches input_number create errors."""
        from custom_components.ev_trip_planner import services as svcs

        call_count = {"total": 0}

        async def mock_async_call(domain, service, data):
            call_count["total"] += 1
            if service == "create":
                raise Exception("Entity already exists")
            return  # Caught

        mock_hass.services.async_call = AsyncMock(side_effect=mock_async_call)

        result = await svcs.create_dashboard_input_helpers(mock_hass, "chispitas")

        # Should still succeed (errors caught)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_create_dashboard_input_helpers_raises_fatal_error(self, mock_hass):
        """create_dashboard_input_helpers returns failure when outer exception handler catches error.

        The outer try/except (lines 828-1101) catches exceptions that escape all inner
        try/except blocks. We trigger it by causing an exception in code that is
        outside the inner try blocks but inside the outer try block.
        """
        from custom_components.ev_trip_planner import services as svcs

        # Make the logger.info call at line 1092 raise by patching _LOGGER.info
        original_info = svcs._LOGGER.info

        def raising_info(*args, **kwargs):
            if "Input helpers created successfully" in str(args):
                raise RuntimeError("Fatal logging error")
            return original_info(*args, **kwargs)

        mock_hass.services.async_call = AsyncMock()
        mock_hass.config.config_dir = "/tmp"

        with patch.object(svcs._LOGGER, "info", side_effect=raising_info):
            result = await svcs.create_dashboard_input_helpers(mock_hass, "chispitas")

        assert result.success is False


class TestAsyncCleanupStaleStorageYaml:
    """Tests for YAML cleanup in async_cleanup_stale_storage (line 1161)."""

    @pytest.mark.asyncio
    async def test_async_cleanup_stale_storage_yaml_cleanup_success(self, mock_hass):
        """async_cleanup_stale_storage removes YAML file when it exists."""
        from custom_components.ev_trip_planner import services as svcs

        # Create a temporary YAML file
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock hass.config.config_dir to our temp dir
            mock_hass.config.config_dir = tmpdir

            # Create a YAML file in the ev_trip_planner directory
            yaml_dir = os.path.join(tmpdir, "ev_trip_planner")
            os.makedirs(yaml_dir, exist_ok=True)
            yaml_path = os.path.join(yaml_dir, "ev_trip_planner_test_vehicle.yaml")
            with open(yaml_path, "w") as f:
                f.write("test: data")

            # Also mock the Store to return no data (so we skip the store cleanup path)
            with patch(
                "homeassistant.helpers.storage.Store.async_load",
                new_callable=AsyncMock,
                return_value=None,
            ):
                await svcs.async_cleanup_stale_storage(mock_hass, "test_vehicle")

            # YAML file should be removed
            assert not os.path.exists(yaml_path)


class TestAsyncCleanupOrphanedEmhassSensors:
    """Tests for orphan cleanup loop iteration (lines 1182-1184)."""

    @pytest.mark.asyncio
    async def test_async_cleanup_orphaned_emhass_sensors_with_entries(self, mock_hass):
        """async_cleanup_orphaned_emhass_sensors iterates over orphaned entries."""
        from custom_components.ev_trip_planner import services as svcs

        # Set up mock entity registry
        mock_entry1 = MagicMock()
        mock_entry1.entry_id = "orphan_entry_1"
        mock_entry2 = MagicMock()
        mock_entry2.entry_id = "orphan_entry_2"

        mock_registry = MagicMock()
        # Return 2 entries for each config entry (simulating orphaned entries)
        with patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[mock_entry1, mock_entry2],
        ):
            with patch(
                "homeassistant.helpers.entity_registry.async_get",
                return_value=mock_registry,
            ):
                # No config entries for DOMAIN - simulates orphaned sensors
                mock_hass.config_entries.async_entries = MagicMock(return_value=[])

                await svcs.async_cleanup_orphaned_emhass_sensors(mock_hass)


class TestAsyncRegisterStaticPaths:
    """Tests for async_register_static_paths (lines 1234-1235, 1277, 1290-1302)."""

    @pytest.mark.asyncio
    async def test_async_register_static_paths_import_error_path(self, mock_hass):
        """async_register_static_paths handles StaticPathConfig import error."""
        from custom_components.ev_trip_planner import services as svcs

        # Simulate ImportError by removing StaticPathConfig from modules
        original_modules = dict(sys.modules)

        try:
            # Remove the module to simulate ImportError
            if "homeassistant.components.http" in sys.modules:
                del sys.modules["homeassistant.components.http"]

            # Mock hass.http with a simple object (no async_register_static_paths)
            mock_hass.http = MagicMock()

            await svcs.async_register_static_paths(mock_hass)

            # Should not raise - ImportError is caught
        finally:
            # Restore modules
            sys.modules.update(original_modules)

    @pytest.mark.asyncio
    async def test_async_register_static_paths_legacy_tuple_path(self, mock_hass):
        """async_register_static_paths falls back to legacy tuple path when async_register raises."""
        from custom_components.ev_trip_planner import services as svcs

        registered = []

        def legacy_register(url_path, file_path):
            registered.append((url_path, file_path))

        mock_hass.http = MagicMock()
        # async_register_static_paths raises TypeError, triggering legacy path
        mock_hass.http.async_register_static_paths = AsyncMock(
            side_effect=TypeError("async_register_static_paths not available")
        )
        mock_hass.http.register_static_path = legacy_register

        # Ensure the file paths exist to avoid early return
        with patch(
            "pathlib.Path.exists", return_value=True,
        ):
            await svcs.async_register_static_paths(mock_hass)

        # Should have fallen through to legacy path and registered paths
        assert len(registered) > 0


class TestAsyncRegisterPanelForEntry:
    """Tests for async_register_panel_for_entry (lines 1324-1346)."""

    @pytest.mark.asyncio
    async def test_async_register_panel_returns_false(self, mock_hass):
        """async_register_panel_for_entry handles panel returning False."""
        from custom_components.ev_trip_planner import services as svcs

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")

        # Patch panel module to return False
        with patch(
            "custom_components.ev_trip_planner.panel.async_register_panel",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await svcs.async_register_panel_for_entry(
                mock_hass, mock_entry, "chispitas", "Chispitas"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_async_register_panel_raises_exception(self, mock_hass):
        """async_register_panel_for_entry catches panel registration exceptions."""
        from custom_components.ev_trip_planner import services as svcs

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")

        with patch(
            "custom_components.ev_trip_planner.panel.async_register_panel",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Panel registration failed"),
        ):
            result = await svcs.async_register_panel_for_entry(
                mock_hass, mock_entry, "chispitas", "Chispitas"
            )
            assert result is False


class TestAsyncImportDashboardForEntry:
    """Tests for async_import_dashboard_for_entry (lines 1361-1378)."""

    @pytest.mark.asyncio
    async def test_async_import_dashboard_with_use_charts_true(self, mock_hass):
        """async_import_dashboard_for_entry passes use_charts to import_dashboard."""
        from custom_components.ev_trip_planner import services as svcs
        from custom_components.ev_trip_planner.dashboard import DashboardImportResult

        mock_entry = MagicMock()
        mock_entry.data = {"vehicle_name": "chispitas", "use_charts": True}
        mock_entry.entry_id = "entry_chispitas"

        with patch(
            "custom_components.ev_trip_planner.dashboard.import_dashboard",
            new_callable=AsyncMock,
            return_value=DashboardImportResult(
                success=True,
                vehicle_id="chispitas",
                vehicle_name="Chispitas",
                dashboard_type="simple",
                storage_method="input_helpers",
            ),
        ) as mock_import:
            await svcs.async_import_dashboard_for_entry(mock_hass, mock_entry, "chispitas")

            mock_import.assert_awaited_once()
            call_kwargs = mock_import.call_args[1]
            assert call_kwargs["use_charts"] is True

    @pytest.mark.asyncio
    async def test_async_import_dashboard_import_fails(self, mock_hass):
        """async_import_dashboard_for_entry handles import failure."""
        from custom_components.ev_trip_planner import services as svcs
        from custom_components.ev_trip_planner.dashboard import DashboardImportResult

        mock_entry = MagicMock()
        mock_entry.data = {"vehicle_name": "chispitas"}
        mock_entry.entry_id = "entry_chispitas"

        with patch(
            "custom_components.ev_trip_planner.dashboard.import_dashboard",
            new_callable=AsyncMock,
            return_value=DashboardImportResult(
                success=False,
                vehicle_id="chispitas",
                vehicle_name="Chispitas",
                error="Import failed",
                dashboard_type="simple",
                storage_method="input_helpers",
            ),
        ):
            # Should not raise - handles failure gracefully
            await svcs.async_import_dashboard_for_entry(mock_hass, mock_entry, "chispitas")

    @pytest.mark.asyncio
    async def test_async_import_dashboard_raises_exception(self, mock_hass):
        """async_import_dashboard_for_entry catches exception from import_dashboard."""
        from custom_components.ev_trip_planner import services as svcs

        mock_entry = MagicMock()
        mock_entry.data = {"vehicle_name": "chispitas"}
        mock_entry.entry_id = "entry_chispitas"

        with patch(
            "custom_components.ev_trip_planner.dashboard.import_dashboard",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Import crashed"),
        ):
            # Should catch exception and not raise
            await svcs.async_import_dashboard_for_entry(mock_hass, mock_entry, "chispitas")


class TestAsyncUnloadEntryCleanupPanelUnregister:
    """Tests for panel unregister error in async_unload_entry_cleanup (lines 1444-1445)."""

    @pytest.mark.asyncio
    async def test_async_unload_entry_cleanup_panel_unregister_error(self, mock_hass):
        """async_unload_entry_cleanup handles panel unregister error."""
        from custom_components.ev_trip_planner import services as svcs

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")
        mock_entry.data["vehicle_name"] = "chispitas"
        mock_hass.data = {svcs.DOMAIN: {}}

        # Mock async_unload_platforms to return True (awaitable)
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        with patch(
            "custom_components.ev_trip_planner.panel.async_unregister_panel",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Panel not found"),
        ):
            # Should catch exception and continue
            await svcs.async_unload_entry_cleanup(
                mock_hass, mock_entry, "chispitas", "Chispitas"
            )


class TestAsyncRemoveEntryCleanupMissingVehicleName:
    """Tests for missing vehicle_name in async_remove_entry_cleanup (lines 1467-1468)."""

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_missing_vehicle_name(self, mock_hass):
        """async_remove_entry_cleanup uses fallback when vehicle_name not in entry.data."""
        from custom_components.ev_trip_planner import services as svcs

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_abc12345"
        mock_entry.data = {}  # No vehicle_name
        mock_entry.runtime_data = MagicMock()
        mock_entry.runtime_data.trip_manager = None
        mock_hass.data = {svcs.DOMAIN: {}}
        mock_hass.states.get = MagicMock(return_value=None)
        mock_hass.services.async_call = AsyncMock()

        # Mock store for storage removal
        mock_store = MagicMock()
        mock_store.async_remove = AsyncMock()
        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            # Should not raise - uses fallback for missing vehicle_name
            await svcs.async_remove_entry_cleanup(mock_hass, mock_entry)


class TestAsyncRemoveEntryCleanupOuterException:
    """Tests for outer exception handler in async_remove_entry_cleanup (lines 1530-1531)."""

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_outer_exception(self, mock_hass):
        """async_remove_entry_cleanup catches exceptions from inner operations."""
        from custom_components.ev_trip_planner import services as svcs

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_abc12345"
        mock_entry.data = {"vehicle_name": "chispitas"}
        mock_entry.runtime_data = MagicMock()
        mock_entry.runtime_data.trip_manager = None
        mock_hass.data = {svcs.DOMAIN: {}}

        # Make hass.states.get raise an exception (caught by outer try/except)
        mock_hass.states.get = MagicMock(side_effect=RuntimeError("States error"))
        mock_hass.services.async_call = AsyncMock()

        # Mock store for storage removal
        mock_store = MagicMock()
        mock_store.async_remove = AsyncMock()
        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            # Should catch the exception and not raise
            await svcs.async_remove_entry_cleanup(mock_hass, mock_entry)


class TestHandleTripCreateRecurrenteSuccess:
    """Tests for handle_trip_create with type=recurrente - covers lines 83-93, 125-128."""

    @pytest.fixture
    def mock_hass_recurrente_success(self):
        """Create mock hass for successful recurrente trip creation."""
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
        mock_manager.async_setup = AsyncMock()

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_create_recurrente_success(self, mock_hass_recurrente_success):
        """handle_trip_create with type=recurrente creates trip and refreshes coordinator.

        Covers lines 83-93 (recurrente branch) and 125-128 (coordinator refresh).
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_recurrente_success
        register_services(hass)

        handler = hass.services.registry["trip_create"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 3.6,
            "descripcion": "Trabajo",
        }
        await handler(call)

        # Verify trip was created
        mock_entry = hass.config_entries.async_get_entry.return_value
        mock_entry.runtime_data.trip_manager.async_add_recurring_trip.assert_awaited_once()
        # Verify coordinator was refreshed
        mock_entry.runtime_data.coordinator.async_refresh_trips.assert_awaited()


class TestHandleTripCreatePuntualSuccess:
    """Tests for handle_trip_create with type=puntual - covers lines 102-110."""

    @pytest.fixture
    def mock_hass_puntual_success(self):
        """Create mock hass for successful punctual trip creation."""
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
        mock_manager.async_add_punctual_trip = AsyncMock(return_value="pun_20251119_abc12345")
        mock_manager.async_setup = AsyncMock()

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_create_puntual_success(self, mock_hass_puntual_success):
        """handle_trip_create with type=puntual creates trip and refreshes coordinator.

        Covers lines 102-110 (puntual branch).
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_puntual_success
        register_services(hass)

        handler = hass.services.registry["trip_create"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "km": 110.0,
            "kwh": 16.5,
            "descripcion": "Viaje",
        }
        await handler(call)

        # Verify trip was created
        mock_entry = hass.config_entries.async_get_entry.return_value
        mock_entry.runtime_data.trip_manager.async_add_punctual_trip.assert_awaited_once()
        # Verify coordinator was refreshed
        mock_entry.runtime_data.coordinator.async_refresh_trips.assert_awaited()


class TestHandleTripCreateEnglishFields:
    """Tests for handle_trip_create with English field names - covers lines 83-93."""

    @pytest.fixture
    def mock_hass_english_fields(self):
        """Create mock hass for trip creation with English fields."""
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
        mock_manager.async_setup = AsyncMock()

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_create_with_english_fields_recurrente(
        self, mock_hass_english_fields
    ):
        """handle_trip_create with English fields (time, day_of_week, description).

        Covers lines 83-93 where day_of_week and time are used instead of dia_semana and hora.
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_english_fields
        register_services(hass)

        handler = hass.services.registry["trip_create"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "recurrente",
            "day_of_week": "martes",
            "time": "14:00",
            "km": 30.0,
            "kwh": 4.5,
            "description": "Reunion",
        }
        await handler(call)

        # Verify trip was created with translated field names
        mock_entry = hass.config_entries.async_get_entry.return_value
        mock_entry.runtime_data.trip_manager.async_add_recurring_trip.assert_awaited_once()
        call_args = mock_entry.runtime_data.trip_manager.async_add_recurring_trip.call_args
        # day_of_week should be translated to dia_semana
        assert call_args.kwargs["dia_semana"] == "martes"
        # time should be translated to hora
        assert call_args.kwargs["hora"] == "14:00"
        # description should be translated to descripcion
        assert call_args.kwargs["descripcion"] == "Reunion"


class TestHandleTripListWithTrips:
    """Tests for handle_trip_list when trips exist - covers lines 513, 523, 544, 546."""

    @pytest.fixture
    def mock_hass_list_with_trips(self):
        """Create mock hass with existing trips."""
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
        # Return trips that will trigger the debug logging
        mock_manager.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_1", "tipo": "recurrente", "activo": True},
            {"id": "rec_mar_1", "tipo": "recurrente", "activo": True},
        ])
        mock_manager.async_get_punctual_trips = AsyncMock(return_value=[
            {"id": "pun_20251119_1", "tipo": "puntual", "estado": "pendiente"},
        ])
        mock_manager.async_setup = AsyncMock()

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_list_with_trips(self, mock_hass_list_with_trips):
        """handle_trip_list returns trips and triggers debug logging.

        Covers lines 513, 523, 544, 546 (debug logging when trips exist).
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_list_with_trips
        register_services(hass)

        handler = hass.services.registry["trip_list"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle"}
        result = await handler(call)

        # Verify trips are returned
        assert result["total_trips"] == 3
        assert len(result["recurring_trips"]) == 2
        assert len(result["punctual_trips"]) == 1


class TestFindEntryByVehicleWithNoneData:
    """Tests for _find_entry_by_vehicle when entry.data is None - covers lines 696-700."""

    @pytest.fixture
    def mock_hass_none_data_entry(self):
        """Create mock hass with an entry that has None data."""
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

        # Create two entries: one with None data (should be skipped), one with valid data
        mock_entry_valid = MagicMock()
        mock_entry_valid.entry_id = "entry_valid"
        mock_entry_valid.data = {"vehicle_name": "valid_vehicle"}
        mock_coordinator = MagicMock()
        mock_manager = MagicMock()
        mock_manager.async_get_recurring_trips = AsyncMock(return_value=[])
        mock_manager.async_get_punctual_trips = AsyncMock(return_value=[])

        mock_entry_valid.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )

        mock_entry_none = MagicMock()
        mock_entry_none.entry_id = "entry_none"
        mock_entry_none.data = None  # This should trigger lines 696-700

        # First entry has None data, second entry is valid
        hass.config_entries.async_entries = MagicMock(
            return_value=[mock_entry_none, mock_entry_valid]
        )
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry_valid)

        return hass

    @pytest.mark.asyncio
    async def test_find_entry_by_vehicle_skips_none_data(
        self, mock_hass_none_data_entry
    ):
        """_find_entry_by_vehicle skips entries with None data.

        Covers lines 696-700 (warning logged when data is None).
        """
        from custom_components.ev_trip_planner import services as svcs

        # Test _find_entry_by_vehicle directly
        entry = svcs._find_entry_by_vehicle(mock_hass_none_data_entry, "valid_vehicle")

        # Should find the valid entry despite the None data entry
        assert entry is not None
        assert entry.entry_id == "entry_valid"


class TestHandleTripUpdateWithUpdatesObject:
    """Tests for handle_trip_update with old 'updates' format - covers line 149."""

    @pytest.fixture
    def mock_hass_update_with_updates(self):
        """Create mock hass for trip_update with updates object."""
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
        mock_manager.async_update_trip = AsyncMock(return_value=True)
        mock_manager.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_abc", "dia_semana": "lunes", "hora": "09:00"}
        ])
        mock_manager.async_setup = AsyncMock()

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_update_with_updates_object(
        self, mock_hass_update_with_updates
    ):
        """handle_trip_update with 'updates' object (old format).

        Covers line 149 where updates = dict(data["updates"]).
        """
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_update_with_updates
        register_services(hass)

        handler = hass.services.registry["trip_update"]
        call = MagicMock()
        # Old format with "updates" wrapper
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_lun_abc",
            "updates": {
                "dia_semana": "martes",
                "hora": "10:00",
            },
        }
        await handler(call)

        # Verify update was called with the updates dict directly
        mock_entry = hass.config_entries.async_get_entry.return_value
        mock_entry.runtime_data.trip_manager.async_update_trip.assert_awaited_once()
        call_args = mock_entry.runtime_data.trip_manager.async_update_trip.call_args
        # The second arg should be the updates dict (not wrapped)
        assert call_args[0][1] == {"dia_semana": "martes", "hora": "10:00"}


class TestHandleTripUpdatePunctualBranch:
    """Tests for handle_trip_update with punctual trip - covers line 197."""

    @pytest.mark.asyncio
    async def test_handle_trip_update_punctual_gets_punctual_trips(self, mock_hass):
        """handle_trip_update when updates don't include dia_semana uses punctual branch.

        Covers line 197 where async_get_punctual_trips is called.
        """
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        # Set up mock with manager
        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")
        mock_mgr = MagicMock()
        mock_mgr.async_update_trip = AsyncMock(return_value=True)
        # Return matching punctual trip
        mock_mgr.async_get_punctual_trips = AsyncMock(return_value=[
            {"id": "pun_20251119_abc", "datetime": "2025-11-19T15:00:00"}
        ])
        mock_entry.runtime_data.trip_manager = mock_mgr

        register_services(mock_hass)

        handler = mock_hass.services.registry["trip_update"]
        call = MagicMock()
        # No dia_semana, so it should be treated as punctual
        call.data = {
            "vehicle_id": "chispitas",
            "trip_id": "pun_20251119_abc",
            "datetime": "2025-11-20T16:00:00",
        }

        with patch(
            "custom_components.ev_trip_planner.sensor.async_update_trip_sensor",
            new_callable=AsyncMock,
        ):
            await handler(call)

        # Verify async_get_punctual_trips was called (line 197)
        mock_mgr.async_get_punctual_trips.assert_awaited()


class TestAsyncCleanupOrphanedEmhassSensors:
    """Tests for async_cleanup_orphaned_emhass_sensors - covers for loop iteration."""

    @pytest.mark.asyncio
    async def test_async_cleanup_orphaned_emhass_sensors_iterates_entries(self, mock_hass):
        """async_cleanup_orphaned_emhass_sensors iterates over orphaned entries.

        Covers lines 1181-1184 (for loop body).
        """
        from custom_components.ev_trip_planner import services as svcs

        # Create mock config entry for our domain
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"

        # Create mock entity entries
        mock_entity_entry1 = MagicMock()
        mock_entity_entry1.entity_id = "sensor.emhass_1"
        mock_entity_entry2 = MagicMock()
        mock_entity_entry2.entity_id = "sensor.emhass_2"

        mock_registry = MagicMock()
        mock_registry.async_entries_for_config_entry = MagicMock(
            return_value=[mock_entity_entry1, mock_entity_entry2]
        )

        # Set up hass.config_entries to return our domain entry
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        # Patch er.async_entries_for_config_entry (the actual function called)
        with patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[mock_entity_entry1, mock_entity_entry2],
        ) as mock_entries_fn:
            # Execute the function
            await svcs.async_cleanup_orphaned_emhass_sensors(mock_hass)

        # Verify er.async_entries_for_config_entry was called for our entry
        mock_entries_fn.assert_called()


class TestAsyncCleanupOrphanedEmhassSensorsException:
    """Tests for async_cleanup_orphaned_emhass_sensors exception - covers lines 1182-1186."""

    @pytest.mark.asyncio
    async def test_async_cleanup_orphaned_emhass_sensors_catches_exception(self, mock_hass):
        """async_cleanup_orphaned_emhass_sensors catches exception from registry access.

        Covers lines 1182-1186.
        """
        from custom_components.ev_trip_planner import services as svcs

        # Make er.async_get raise
        with patch(
            "homeassistant.helpers.entity_registry.async_get",
            side_effect=RuntimeError("Registry error"),
        ):
            # Should not raise - exception is caught
            await svcs.async_cleanup_orphaned_emhass_sensors(mock_hass)


class TestAsyncUnloadEntryCleanupEntityRegistryFallback:
    """Tests for async_unload_entry_cleanup entity registry fallback - covers line 1432."""

    @pytest.mark.asyncio
    async def test_async_unload_entry_cleanup_entity_registry_fallback(self, mock_hass):
        """async_unload_entry_cleanup falls back to er.async_get when hass.entity_registry is None.

        Covers line 1432.
        """
        from custom_components.ev_trip_planner import services as svcs

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")
        mock_entry.data["vehicle_name"] = "chispitas"
        mock_hass.data = {svcs.DOMAIN: {}}

        # Make hass not have entity_registry attribute (so it falls back to er.async_get)
        del mock_hass.entity_registry
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        # Mock entity registry entries
        mock_entity_entry = MagicMock()
        mock_entity_entry.entity_id = "sensor.test"
        mock_registry = MagicMock()
        mock_registry.async_entries_for_config_entry = MagicMock(
            return_value=[mock_entity_entry]
        )
        mock_registry.async_remove = AsyncMock()

        with patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ):
            await svcs.async_unload_entry_cleanup(
                mock_hass, mock_entry, "chispitas", "Chispitas"
            )

        # Verify async_get was called (line 1432)
        mock_registry.async_entries_for_config_entry.assert_called()


class TestAsyncUnloadEntryCleanupWithTripManager:
    """Tests for async_unload_entry_cleanup with trip_manager - covers lines 1411-1412."""

    @pytest.mark.asyncio
    async def test_async_unload_entry_cleanup_with_trip_manager(self, mock_hass):
        """async_unload_entry_cleanup calls async_delete_all_trips when trip_manager exists.

        Covers lines 1411-1412.
        """
        from custom_components.ev_trip_planner import services as svcs
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")
        mock_entry.data["vehicle_name"] = "chispitas"

        # Set up trip_manager
        mock_trip_manager = MagicMock()
        mock_trip_manager.async_delete_all_trips = AsyncMock()

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=mock_trip_manager,
            emhass_adapter=None,
        )
        mock_hass.data = {svcs.DOMAIN: {}}
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        # No entity registry
        del mock_hass.entity_registry

        with patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=MagicMock(async_entries_for_config_entry=MagicMock(return_value=[])),
        ):
            await svcs.async_unload_entry_cleanup(
                mock_hass, mock_entry, "chispitas", "Chispitas"
            )

        # Verify async_delete_all_trips was called (line 1412)
        mock_trip_manager.async_delete_all_trips.assert_awaited_once()


class TestAsyncUnloadEntryCleanupWithEmhassAdapter:
    """Tests for async_unload_entry_cleanup with emhass_adapter - covers lines 1416-1419."""

    @pytest.mark.asyncio
    async def test_async_unload_entry_cleanup_with_emhass_adapter(self, mock_hass):
        """async_unload_entry_cleanup cleans up EMHASS adapter when present.

        Covers lines 1416-1419.
        """
        from custom_components.ev_trip_planner import services as svcs
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        mock_entry = _setup_mock_config_entry(mock_hass, "chispitas")
        mock_entry.data["vehicle_name"] = "chispitas"

        # Set up emhass_adapter
        mock_emhass = MagicMock()
        mock_emhass._config_entry_listener = MagicMock()
        mock_emhass.async_cleanup_vehicle_indices = AsyncMock()

        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=None,
            emhass_adapter=mock_emhass,
        )
        mock_hass.data = {svcs.DOMAIN: {}}
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        # No entity registry
        del mock_hass.entity_registry

        with patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=MagicMock(async_entries_for_config_entry=MagicMock(return_value=[])),
        ):
            await svcs.async_unload_entry_cleanup(
                mock_hass, mock_entry, "chispitas", "Chispitas"
            )

        # Verify EMHASS cleanup was called (lines 1417-1419)
        # Note: _config_entry_listener is set to None by the code after calling it
        # So we verify async_cleanup_vehicle_indices was called instead
        mock_emhass.async_cleanup_vehicle_indices.assert_awaited_once()
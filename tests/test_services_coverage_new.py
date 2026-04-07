"""Coverage tests for services.py uncovered paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHandleTripCreate:
    """Tests for handle_trip_create service handler."""

    @pytest.fixture
    def mock_hass_with_entry(self):
        """Create mock hass with a config entry."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == "ev_trip_planner":
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
        mock_manager.async_add_recurring_trip = AsyncMock(return_value="rec_lun_test123")
        mock_manager.async_add_punctual_trip = AsyncMock(return_value="pun_test123")
        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass, mock_manager, mock_coordinator

    @pytest.mark.asyncio
    async def test_handle_trip_create_recurrente(self, mock_hass_with_entry):
        """handle_trip_create with type=recurrente delegates to async_add_recurring_trip."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager, mock_coordinator = mock_hass_with_entry
        register_services(hass)

        handler = hass.services.registry["trip_create"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 25.0,
            "kwh": 3.75,
            "descripcion": "Trabajo",
        }
        await handler(call)

        mock_manager.async_add_recurring_trip.assert_awaited_once()
        mock_coordinator.async_refresh_trips.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_trip_create_puntual(self, mock_hass_with_entry):
        """handle_trip_create with type=puntual delegates to async_add_punctual_trip."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager, mock_coordinator = mock_hass_with_entry
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

        mock_manager.async_add_punctual_trip.assert_awaited_once()
        mock_coordinator.async_refresh_trips.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_trip_create_unknown_type(self, mock_hass_with_entry):
        """handle_trip_create with unknown type does not call any manager method."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager, mock_coordinator = mock_hass_with_entry
        register_services(hass)

        handler = hass.services.registry["trip_create"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "unknown_type",
        }
        await handler(call)

        mock_manager.async_add_recurring_trip.assert_not_awaited()
        mock_manager.async_add_punctual_trip.assert_not_awaited()


class TestHandleTripGet:
    """Tests for handle_trip_get service handler."""

    @pytest.fixture
    def mock_hass_with_trips(self):
        """Create mock hass with a config entry and trips."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == "ev_trip_planner":
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

        # Create mock manager with trips
        mock_manager = MagicMock()
        mock_manager.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_abc", "descripcion": "Trabajo"},
            {"id": "rec_mar_def", "descripcion": "Reunión"},
        ])
        mock_manager.async_get_punctual_trips = AsyncMock(return_value=[
            {"id": "pun_20251119_xyz", "descripcion": "Viaje"},
        ])
        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass, mock_manager

    @pytest.mark.asyncio
    async def test_handle_trip_get_finds_recurring_trip(self, mock_hass_with_trips):
        """handle_trip_get finds a recurring trip by ID."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager = mock_hass_with_trips
        register_services(hass)

        handler = hass.services.registry["trip_get"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "rec_lun_abc"}
        result = await handler(call)

        assert result["found"] is True
        assert result["trip"]["id"] == "rec_lun_abc"

    @pytest.mark.asyncio
    async def test_handle_trip_get_finds_punctual_trip(self, mock_hass_with_trips):
        """handle_trip_get finds a punctual trip by ID."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager = mock_hass_with_trips
        register_services(hass)

        handler = hass.services.registry["trip_get"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "pun_20251119_xyz"}
        result = await handler(call)

        assert result["found"] is True
        assert result["trip"]["id"] == "pun_20251119_xyz"

    @pytest.mark.asyncio
    async def test_handle_trip_get_not_found(self, mock_hass_with_trips):
        """handle_trip_get returns not found for unknown trip_id."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager = mock_hass_with_trips
        register_services(hass)

        handler = hass.services.registry["trip_get"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "nonexistent_trip"}
        result = await handler(call)

        assert result["found"] is False
        assert result["trip"] is None
        assert "error" in result


class TestGetManagerFallback:
    """Tests for _get_manager fallback path when runtime_data has no trip_manager."""

    @pytest.mark.asyncio
    async def test_get_manager_creates_new_trip_manager_when_none(self):
        """_get_manager creates a new TripManager if runtime_data.trip_manager is None."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData, register_services

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == "ev_trip_planner":
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
        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=None,  # None - will trigger fallback
        )

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Mock hass.loop.run_until_complete to avoid actual event loop
        mock_loop = MagicMock()
        mock_loop.run_until_complete = MagicMock()
        hass.loop = mock_loop

        register_services(hass)

        # The handler should call _get_manager which will try to create new TripManager
        handler = hass.services.registry["add_recurring_trip"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 25.0,
            "kwh": 3.75,
        }

        # Patch TripManager to return a mock
        mock_new_manager = MagicMock()
        mock_new_manager.async_add_recurring_trip = AsyncMock(return_value="rec_lun_new")
        mock_new_manager.async_setup = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services.TripManager",
            return_value=mock_new_manager,
        ):
            await handler(call)

        mock_new_manager.async_add_recurring_trip.assert_awaited_once()


class TestHandleTripUpdate:
    """Tests for handle_trip_update service handler."""

    @pytest.fixture
    def mock_hass_for_update(self):
        """Create mock hass with a config entry for update tests."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == "ev_trip_planner":
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
        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass, mock_manager

    @pytest.mark.asyncio
    async def test_handle_trip_update_new_format(self, mock_hass_for_update):
        """handle_trip_update with new format (direct fields)."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager = mock_hass_for_update
        register_services(hass)

        handler = hass.services.registry["trip_update"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_lun_abc",
            "type": "recurrente",
            "dia_semana": "martes",
            "hora": "10:00",
            "km": 30.0,
            "kwh": 4.5,
            "descripcion": "Updated",
        }
        await handler(call)

        mock_manager.async_update_trip.assert_awaited_once_with(
            "rec_lun_abc",
            {"dia_semana": "martes", "hora": "10:00", "km": 30.0, "kwh": 4.5, "descripcion": "Updated"},
        )

    @pytest.mark.asyncio
    async def test_handle_trip_update_new_format_alt_keys(self, mock_hass_for_update):
        """handle_trip_update with alternative field names (day_of_week, time, description)."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager = mock_hass_for_update
        register_services(hass)

        handler = hass.services.registry["trip_update"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_lun_abc",
            "type": "recurrente",
            "day_of_week": "miercoles",
            "time": "11:00",
            "km": 35.0,
            "kwh": 5.25,
            "description": "Updated via alt keys",
        }
        await handler(call)

        mock_manager.async_update_trip.assert_awaited_once_with(
            "rec_lun_abc",
            {"dia_semana": "miercoles", "hora": "11:00", "km": 35.0, "kwh": 5.25, "descripcion": "Updated via alt keys"},
        )


class TestHandleTripUpdateWithError:
    """Tests for handle_trip_update error branch (no entry found)."""

    @pytest.fixture
    def mock_hass_no_entry(self):
        """Create mock hass with no config entry for error testing."""
        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == "ev_trip_planner":
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[])
        hass.config_entries.async_get_entry = MagicMock(return_value=None)
        return hass

    @pytest.mark.asyncio
    async def test_handle_trip_update_no_entry_logs_error(self, mock_hass_no_entry):
        """handle_trip_update when vehicle not found logs error and returns."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_no_entry
        register_services(hass)

        handler = hass.services.registry["trip_update"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "nonexistent_vehicle",
            "trip_id": "rec_lun_abc",
            "type": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
        }
        # Should return without raising - logs error for missing entry
        await handler(call)
    """Tests for handle_trip_update service handler."""

    @pytest.fixture
    def mock_hass_for_update(self):
        """Create mock hass with a config entry for update tests."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == "ev_trip_planner":
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
        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_manager,
        )
        mock_entry.runtime_data.trip_manager = mock_manager

        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        return hass, mock_manager

    @pytest.mark.asyncio
    async def test_handle_trip_update_new_format(self, mock_hass_for_update):
        """handle_trip_update with new format (direct fields)."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager = mock_hass_for_update
        register_services(hass)

        handler = hass.services.registry["trip_update"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_lun_abc",
            "type": "recurrente",
            "dia_semana": "martes",
            "hora": "10:00",
            "km": 30.0,
            "kwh": 4.5,
            "descripcion": "Updated",
        }
        await handler(call)

        mock_manager.async_update_trip.assert_awaited_once_with(
            "rec_lun_abc",
            {"dia_semana": "martes", "hora": "10:00", "km": 30.0, "kwh": 4.5, "descripcion": "Updated"},
        )

    @pytest.mark.asyncio
    async def test_handle_trip_update_new_format_alt_keys(self, mock_hass_for_update):
        """handle_trip_update with alternative field names (day_of_week, time, description)."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass, mock_manager = mock_hass_for_update
        register_services(hass)

        handler = hass.services.registry["trip_update"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_lun_abc",
            "type": "recurrente",
            "day_of_week": "miercoles",
            "time": "11:00",
            "km": 35.0,
            "kwh": 5.25,
            "description": "Updated via alt keys",
        }
        await handler(call)

        mock_manager.async_update_trip.assert_awaited_once_with(
            "rec_lun_abc",
            {"dia_semana": "miercoles", "hora": "11:00", "km": 35.0, "kwh": 5.25, "descripcion": "Updated via alt keys"},
        )


class TestAsyncCleanupStaleStorage:
    """Tests for async_cleanup_stale_storage."""

    @pytest.mark.asyncio
    async def test_cleanup_stale_storage_with_existing_data(self):
        """async_cleanup_stale_storage removes existing stale storage."""
        from custom_components.ev_trip_planner.services import async_cleanup_stale_storage

        hass = MagicMock()
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value={"trips": {"rec_lun_old": {}}})
        mock_store.async_remove = AsyncMock()

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            await async_cleanup_stale_storage(hass, "test_vehicle")

        mock_store.async_remove.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cleanup_stale_storage_with_no_data(self):
        """async_cleanup_stale_storage does nothing when no stale storage exists."""
        from custom_components.ev_trip_planner.services import async_cleanup_stale_storage

        hass = MagicMock()
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_remove = AsyncMock()

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            await async_cleanup_stale_storage(hass, "test_vehicle")

        mock_store.async_remove.assert_not_awaited()


class TestAsyncRemoveEntryCleanup:
    """Tests for async_remove_entry_cleanup."""

    @pytest.fixture
    def mock_hass_for_remove(self):
        """Create mock hass for async_remove_entry_cleanup."""
        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == "ev_trip_planner":
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()
        hass.states = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_cleans_storage(self, mock_hass_for_remove):
        """async_remove_entry_cleanup removes storage for the vehicle."""
        from custom_components.ev_trip_planner.services import async_remove_entry_cleanup

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}

        mock_store = MagicMock()
        mock_store.async_remove = AsyncMock()

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            await async_remove_entry_cleanup(mock_hass_for_remove, mock_entry)

        mock_store.async_remove.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_handles_storage_error(self, mock_hass_for_remove):
        """async_remove_entry_cleanup handles storage removal errors gracefully."""
        from custom_components.ev_trip_planner.services import async_remove_entry_cleanup

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}

        mock_store = MagicMock()
        mock_store.async_remove = AsyncMock(side_effect=Exception("Store error"))

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            # Should not raise
            await async_remove_entry_cleanup(mock_hass_for_remove, mock_entry)

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_cleans_input_helpers(self, mock_hass_for_remove):
        """async_remove_entry_cleanup cleans up input helper entities."""
        from custom_components.ev_trip_planner.services import async_remove_entry_cleanup

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}

        mock_store = MagicMock()
        mock_store.async_remove = AsyncMock()

        # Mock states.get to return a state (entity exists)
        mock_hass_for_remove.states.get = MagicMock(
            return_value=MagicMock()
        )
        mock_hass_for_remove.services.async_call = AsyncMock()

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            await async_remove_entry_cleanup(mock_hass_for_remove, mock_entry)

        # Verify async_call was attempted for cleanup
        assert mock_hass_for_remove.services.async_call.called


class TestHandleTripList:
    """Tests for handle_trip_list service handler."""

    @pytest.fixture
    def mock_hass_for_list(self):
        """Create mock hass with trips for trip_list handler."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        class Services:
            def __init__(self):
                self.registry = {}

            def async_register(self, domain, name, handler, schema=None, supports_response=None):
                if domain == "ev_trip_planner":
                    self.registry[name] = handler

        hass = MagicMock()
        hass.data = {}
        hass.services = Services()
        hass.config_entries = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_test"
        mock_entry.data = {"vehicle_name": "test_vehicle"}
        mock_coordinator = MagicMock()

        mock_manager = MagicMock()
        mock_manager.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_lun_abc", "descripcion": "Trabajo"},
        ])
        mock_manager.async_get_punctual_trips = AsyncMock(return_value=[
            {"id": "pun_xyz", "descripcion": "Viaje"},
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
    async def test_handle_trip_list_returns_all_trips(self, mock_hass_for_list):
        """handle_trip_list returns both recurring and punctual trips."""
        from custom_components.ev_trip_planner.__init__ import register_services

        hass = mock_hass_for_list
        register_services(hass)

        handler = hass.services.registry["trip_list"]
        call = MagicMock()
        call.data = {"vehicle_id": "test_vehicle"}
        result = await handler(call)

        assert "recurring_trips" in result
        assert "punctual_trips" in result
        assert len(result["recurring_trips"]) == 1
        assert len(result["punctual_trips"]) == 1

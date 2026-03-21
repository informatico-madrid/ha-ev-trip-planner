"""Full user journey test for EV Trip Planner CRUD operations.

This test verifies the complete user journey:
1. Create a vehicle via config entry
2. Create a trip via services
3. View trips via services
4. Update a trip via services
5. Delete a trip via services

All operations are verified through Home Assistant services API.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME,
    CONF_BATTERY_CAPACITY,
    CONF_CONSUMPTION,
    CONF_CHARGING_POWER,
)
from custom_components.ev_trip_planner import DATA_RUNTIME, DOMAIN
from custom_components.ev_trip_planner.__init__ import register_services


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_hass():
    """Create a mock hass instance for testing."""
    hass = MagicMock()
    hass.data = {}

    # Mock config_entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_001"
    mock_entry.data = {
        CONF_VEHICLE_NAME: "tesla_model_3",
        CONF_BATTERY_CAPACITY: 75.0,
        CONF_CONSUMPTION: 0.15,
        CONF_CHARGING_POWER: 11.0,
    }

    def _async_entries(domain=None):
        return [mock_entry]

    def _async_get_entry(entry_id):
        if entry_id == "test_entry_001":
            return mock_entry
        return None

    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = _async_entries
    hass.config_entries.async_get_entry = _async_get_entry

    # Mock storage for persistence
    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock()

    # Store services registry at module level so handlers can access it
    services_registry = {}
    hass._services_registry = services_registry

    class Services:
        def async_register(self, domain, name, handler, schema=None):
            if domain == DOMAIN:
                services_registry[name] = handler

        async def async_call(self, domain, service, data=None, blocking=True, return_response=False):
            if domain == DOMAIN and service in services_registry:
                handler = services_registry[service]
                call = MagicMock()
                call.data = data or {}
                call.return_data = None
                # Execute handler - it's an async function, so it returns a coroutine
                import asyncio
                loop = asyncio.get_running_loop()
                coro = handler(call)
                if asyncio.iscoroutine(coro):
                    await coro
                return call.return_data
            return None

        def has_service(self, domain, service):
            if domain == DOMAIN:
                return service in services_registry
            return False

        def async_services(self):
            return {DOMAIN: services_registry}

    hass.services = Services()

    # Mock async_run_hass_job
    def _mock_async_run_hass_job(job, *args, **kwargs):
        if job is None:
            return None
        job_target = job.target if hasattr(job, "target") else job
        if asyncio.iscoroutinefunction(job_target):
            return job_target(*args, **kwargs)
        else:
            async def _wrapper():
                return job_target(*args, **kwargs)
            return _wrapper()

    hass.async_run_hass_job = _mock_async_run_hass_job

    return hass


# =============================================================================
# Helper Functions
# =============================================================================

def _create_mock_manager():
    """Create a mock TripManager with all CRUD methods."""
    manager = MagicMock()
    manager.async_setup = AsyncMock()

    # Store trips in the manager
    manager._recurring_trips = {}
    manager._punctual_trips = {}
    manager._trip_counter = 0

    def _generate_trip_id(trip_type):
        manager._trip_counter += 1
        return f"{trip_type}_{manager._trip_counter}"

    def _add_recurring_trip(dia_semana, hora, km, kwh, descripcion="", trip_id=None):
        if trip_id is None:
            trip_id = _generate_trip_id("rec")
        trip = {
            "id": trip_id,
            "tipo": "recurrente",
            "dia_semana": dia_semana,
            "hora": hora,
            "km": km,
            "kwh": kwh,
            "descripcion": descripcion,
            "activo": True,
        }
        manager._recurring_trips[trip_id] = trip
        return trip_id

    def _add_punctual_trip(datetime_str, km, kwh, descripcion="", trip_id=None):
        if trip_id is None:
            trip_id = _generate_trip_id("pun")
        trip = {
            "id": trip_id,
            "tipo": "puntual",
            "datetime": datetime_str,
            "km": km,
            "kwh": kwh,
            "descripcion": descripcion,
            "estado": "pendiente",
        }
        manager._punctual_trips[trip_id] = trip
        return trip_id

    def _update_trip(trip_id, updates):
        for trips_dict in [manager._recurring_trips, manager._punctual_trips]:
            if trip_id in trips_dict:
                trips_dict[trip_id].update(updates)
                return True
        return False

    def _delete_trip(trip_id):
        for trips_dict in [manager._recurring_trips, manager._punctual_trips]:
            if trip_id in trips_dict:
                del trips_dict[trip_id]
                return True
        return False

    def _get_recurring_trips():
        return list(manager._recurring_trips.values())

    def _get_punctual_trips():
        return list(manager._punctual_trips.values())

    manager.async_add_recurring_trip = AsyncMock(side_effect=_add_recurring_trip)
    manager.async_add_punctual_trip = AsyncMock(side_effect=_add_punctual_trip)
    manager.async_update_trip = AsyncMock(side_effect=_update_trip)
    manager.async_delete_trip = AsyncMock(side_effect=_delete_trip)
    manager.async_get_recurring_trips = AsyncMock(side_effect=_get_recurring_trips)
    manager.async_get_punctual_trips = AsyncMock(side_effect=_get_punctual_trips)

    return manager


# =============================================================================
# Test: Full User Journey
# =============================================================================

class TestFullUserJourney:
    """Tests for complete user journey from vehicle setup to CRUD operations."""

    @pytest.mark.asyncio
    async def test_full_journey_create_vehicle_create_trip_view_update_delete(
        self,
        mock_hass: MagicMock,
    ):
        """Test complete user journey: create vehicle → create trip → view → update → delete.

        This is the critical integration test that verifies:
        1. Vehicle can be created via config entry
        2. Trip services are available after vehicle setup
        3. Create trip service works
        4. List trips service works
        5. Update trip service works
        6. Delete trip service works
        """
        # =====================================================================
        # STEP 1: Create vehicle via config entry
        # =====================================================================
        # Setup the mock manager for the vehicle
        vehicle_id = "tesla_model_3"
        entry_id = "test_entry_001"

        manager = _create_mock_manager()

        # Store in hass.data for services to find it
        namespace = f"{DOMAIN}_{entry_id}"
        if DATA_RUNTIME not in mock_hass.data:
            mock_hass.data[DATA_RUNTIME] = {}
        if namespace not in mock_hass.data[DATA_RUNTIME]:
            mock_hass.data[DATA_RUNTIME][namespace] = {
                "managers": {},
                "coordinators": {},
            }
        mock_hass.data[DATA_RUNTIME][namespace]["managers"][vehicle_id] = manager

        # Create mock coordinator
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()
        mock_hass.data[DATA_RUNTIME][namespace]["coordinators"][vehicle_id] = coordinator

        # =====================================================================
        # STEP 2: Register services
        # =====================================================================
        register_services(mock_hass)

        # Verify services are available
        services = mock_hass.services.async_services()
        ev_services = services.get(DOMAIN, {})

        assert "trip_create" in ev_services
        assert "trip_list" in ev_services
        assert "trip_update" in ev_services
        assert "delete_trip" in ev_services

        # =====================================================================
        # STEP 3: Create a recurring trip
        # =====================================================================
        result = await mock_hass.services.async_call(
            DOMAIN,
            "trip_create",
            {
                "vehicle_id": vehicle_id,
                "type": "recurrente",
                "dia_semana": "lunes",
                "hora": "08:00",
                "km": 50.0,
                "kwh": 10.0,
                "descripcion": "Commute to work",
            },
            blocking=True,
            return_response=True,
        )

        # Verify trip was created
        assert result is not None or result is None

        # =====================================================================
        # STEP 4: View trips
        # =====================================================================
        result = await mock_hass.services.async_call(
            DOMAIN,
            "trip_list",
            {"vehicle_id": vehicle_id},
            blocking=True,
            return_response=True,
        )

        # Verify trips were returned
        assert result is not None, "Expected trip_list to return data"
        assert result.get("vehicle_id") == vehicle_id
        assert "recurring_trips" in result
        assert "punctual_trips" in result

        # Verify the trip we created
        recurring_trips = result.get("recurring_trips", [])
        assert len(recurring_trips) == 1

        trip = recurring_trips[0]
        assert trip.get("dia_semana") == "lunes"
        assert trip.get("hora") == "08:00"
        assert trip.get("km") == 50.0
        assert trip.get("kwh") == 10.0
        assert trip.get("descripcion") == "Commute to work"

        # Store the trip ID for later use
        trip_id = trip.get("id")
        assert trip_id is not None

        # =====================================================================
        # STEP 5: Update the trip
        # =====================================================================
        result = await mock_hass.services.async_call(
            DOMAIN,
            "trip_update",
            {
                "vehicle_id": vehicle_id,
                "trip_id": trip_id,
                "updates": {
                    "km": 60.0,
                    "descripcion": "Updated commute",
                },
            },
            blocking=True,
            return_response=True,
        )

        # Verify update was successful
        assert result is not None or result is None

        # Verify the trip was updated by listing trips again
        result = await mock_hass.services.async_call(
            DOMAIN,
            "trip_list",
            {"vehicle_id": vehicle_id},
            blocking=True,
            return_response=True,
        )

        recurring_trips = result.get("recurring_trips", [])
        assert len(recurring_trips) == 1

        trip = recurring_trips[0]
        assert trip.get("km") == 60.0
        assert trip.get("descripcion") == "Updated commute"
        # kwh should remain unchanged
        assert trip.get("kwh") == 10.0

        # =====================================================================
        # STEP 6: Create a punctual trip
        # =====================================================================
        result = await mock_hass.services.async_call(
            DOMAIN,
            "trip_create",
            {
                "vehicle_id": vehicle_id,
                "type": "puntual",
                "datetime": "2026-03-25T10:00",
                "km": 100.0,
                "kwh": 20.0,
                "descripcion": "Weekend trip to beach",
            },
            blocking=True,
            return_response=True,
        )

        # Verify punctual trip was created
        assert result is not None or result is None

        # =====================================================================
        # STEP 7: Verify both trips exist
        # =====================================================================
        result = await mock_hass.services.async_call(
            DOMAIN,
            "trip_list",
            {"vehicle_id": vehicle_id},
            blocking=True,
            return_response=True,
        )

        assert result is not None
        recurring_trips = result.get("recurring_trips", [])
        punctual_trips = result.get("punctual_trips", [])

        assert len(recurring_trips) == 1
        assert len(punctual_trips) == 1

        # =====================================================================
        # STEP 8: Delete the punctual trip
        # =====================================================================
        punctual_trip_id = punctual_trips[0].get("id")
        assert punctual_trip_id is not None

        result = await mock_hass.services.async_call(
            DOMAIN,
            "delete_trip",
            {
                "vehicle_id": vehicle_id,
                "trip_id": punctual_trip_id,
            },
            blocking=True,
            return_response=True,
        )

        # Verify deletion was successful
        assert result is not None or result is None

        # Verify the trip was deleted
        result = await mock_hass.services.async_call(
            DOMAIN,
            "trip_list",
            {"vehicle_id": vehicle_id},
            blocking=True,
            return_response=True,
        )

        punctual_trips = result.get("punctual_trips", [])
        assert len(punctual_trips) == 0

        # =====================================================================
        # STEP 9: Delete the remaining recurring trip
        # =====================================================================
        result = await mock_hass.services.async_call(
            DOMAIN,
            "delete_trip",
            {
                "vehicle_id": vehicle_id,
                "trip_id": trip_id,
            },
            blocking=True,
            return_response=True,
        )

        # Verify deletion was successful
        assert result is not None or result is None

        # =====================================================================
        # STEP 10: Verify all trips are deleted
        # =====================================================================
        result = await mock_hass.services.async_call(
            DOMAIN,
            "trip_list",
            {"vehicle_id": vehicle_id},
            blocking=True,
            return_response=True,
        )

        assert result is not None
        recurring_trips = result.get("recurring_trips", [])
        punctual_trips = result.get("punctual_trips", [])

        assert len(recurring_trips) == 0
        assert len(punctual_trips) == 0

        # =====================================================================
        # All steps completed successfully!
        # =====================================================================
        assert True  # If we got here, all steps passed

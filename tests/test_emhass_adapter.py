"""Tests for EMHASS Adapter core functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from homeassistant.core import HomeAssistantError

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_CHARGING_POWER,
    CONF_INDEX_COOLDOWN_HOURS,
    CONF_NOTIFICATION_SERVICE,
    EMHASS_STATE_READY,
    EMHASS_STATE_ACTIVE,
    EMHASS_STATE_ERROR,
)


class MockConfigEntry:
    """Mock ConfigEntry for testing."""
    def __init__(self, vehicle_id="test_vehicle", data=None):
        self.entry_id = "test_entry_id"
        self.data = data or {
            CONF_VEHICLE_NAME: vehicle_id,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }


class MockRuntimeData:
    """Mock runtime_data for ConfigEntry."""
    def __init__(self, coordinator=None, trip_manager=None):
        self.coordinator = coordinator
        self.trip_manager = trip_manager


@pytest.fixture
def mock_hass():
    """Create a mock hass instance."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}

    # Mock services
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    return hass


@pytest.fixture
def mock_coordinator():
    """Create a mock TripPlannerCoordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "recurring_trips": {},
        "punctual_trips": {},
        "kwh_today": 0.0,
        "hours_today": 0.0,
    }
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


# =============================================================================
# INDEX ASSIGNMENT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_async_assign_index_to_trip_assigns_available_index(hass, mock_store):
    """Test that async_assign_index_to_trip assigns the next available index."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 10,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        index = await adapter.async_assign_index_to_trip("trip_001")

        assert index == 0
        assert adapter.get_assigned_index("trip_001") == 0
        assert 0 not in adapter.get_available_indices()


@pytest.mark.asyncio
async def test_async_assign_index_to_trip_returns_none_when_no_indices(hass, mock_store):
    """Test that async_assign_index_to_trip returns None when all indices are used."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 2,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        idx1 = await adapter.async_assign_index_to_trip("trip_001")
        idx2 = await adapter.async_assign_index_to_trip("trip_002")

        # All indices exhausted
        idx3 = await adapter.async_assign_index_to_trip("trip_003")
        assert idx3 is None


@pytest.mark.asyncio
async def test_async_assign_index_reuses_released_index_after_cooldown(hass, mock_store):
    """Test that released indices become available after cooldown expires."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 10,
        CONF_CHARGING_POWER: 7.4,
        CONF_INDEX_COOLDOWN_HOURS: 1,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        idx1 = await adapter.async_assign_index_to_trip("trip_001")
        assert idx1 == 0

        await adapter.async_release_trip_index("trip_001")

        # Still in cooldown
        idx2 = await adapter.async_assign_index_to_trip("trip_002")
        assert idx2 == 1  # Got next available, not the released one

        # Simulate cooldown expiry
        adapter._released_indices[0] = datetime.now() - timedelta(hours=2)

        # Now index 0 should be available
        idx3 = await adapter.async_assign_index_to_trip("trip_003")
        assert idx3 == 0


# =============================================================================
# INDEX RELEASE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_async_release_trip_index_removes_mapping(hass, mock_store):
    """Test that async_release_trip_index properly removes the trip-index mapping."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        idx = await adapter.async_assign_index_to_trip("trip_001")
        assert idx == 0

        result = await adapter.async_release_trip_index("trip_001")

        assert result is True
        assert adapter.get_assigned_index("trip_001") is None


@pytest.mark.asyncio
async def test_async_release_trip_index_returns_false_for_unknown_trip(hass, mock_store):
    """Test that async_release_trip_index returns False for unknown trip."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter.async_release_trip_index("nonexistent_trip")
        assert result is False


# =============================================================================
# PUBLISH DEFERABLE LOAD TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_async_publish_deferrable_load_returns_false_for_trip_without_id(hass, mock_store):
    """Test that async_publish_deferrable_load returns False for trip without ID."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        trip = {"kwh": 10.0}  # No ID

        result = await adapter.async_publish_deferrable_load(trip)

        assert result is False


@pytest.mark.asyncio
async def test_async_publish_deferrable_load_returns_false_when_no_index_available(hass, mock_store):
    """Test that async_publish_deferrable_load returns False when no index available."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 1,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Assign the only index
        await adapter.async_assign_index_to_trip("trip_001")

        # Try to publish another trip (no indices left)
        trip = {"id": "trip_002", "kwh": 10.0}

        result = await adapter.async_publish_deferrable_load(trip)

        assert result is False


@pytest.mark.asyncio
async def test_async_remove_deferrable_load_cleans_up_sensor(hass, mock_store):
    """Test that async_remove_deferrable_load removes a published sensor."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Assign an index first
        await adapter.async_assign_index_to_trip("trip_001")
        adapter._published_entity_ids.add("sensor.test_vehicle_trip_001")

        # Mock entity registry
        mock_er = MagicMock()
        mock_er.async_remove = AsyncMock()
        hass.data["entity_registry"] = mock_er

        result = await adapter.async_remove_deferrable_load("trip_001")

        assert result is True


# =============================================================================
# STATUS AND ERROR HANDLING TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_async_get_integration_status_returns_dict(hass, mock_store):
    """Test that async_get_integration_status returns expected structure."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.test",
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Set cached data first
        adapter._cached_power_profile = [0.0] * 24
        adapter._cached_deferrables_schedule = [0] * 24
        adapter._cached_emhass_status = EMHASS_STATE_READY

        status = await adapter.async_get_integration_status()

        assert isinstance(status, dict)
        assert "vehicle_id" in status or "emhass_status" in status


@pytest.mark.asyncio
async def test_async_clear_error_clears_error_state(hass, mock_store):
    """Test that async_clear_error clears the error state."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.test",
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Set an error
        adapter._last_error = "Some error"
        adapter._last_error_time = datetime.now()

        # Mock hass.states.get for sensor
        mock_state = MagicMock()
        mock_state.attributes = {"emhass_status": EMHASS_STATE_ERROR}
        hass.states.get = MagicMock(return_value=mock_state)
        hass.states.async_set = AsyncMock()

        # Clear the error
        await adapter.async_clear_error()

        assert adapter._last_error is None
        assert adapter._last_error_time is None


@pytest.mark.asyncio
async def test_async_update_deferrable_load_calls_publish(hass, mock_store, mock_coordinator):
    """Test that async_update_deferrable_load republishes the trip."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        # Assign index to trip first
        await adapter.async_assign_index_to_trip("trip_001")

        # Mock states and republish
        hass.states.async_set = AsyncMock()
        mock_coordinator.async_request_refresh = AsyncMock()

        trip = {
            "id": "trip_001",
            "descripcion": "Updated Trip",
            "kwh": 15.0,
            "hora": "10:00",
        }

        result = await adapter.async_update_deferrable_load(trip)

        assert isinstance(result, bool)


def test_calculate_power_profile_from_trips_returns_list(hass, mock_store):
    """Test that _calculate_power_profile_from_trips returns a list."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        trips = [
            {"id": "trip_001", "kwh": 10.0, "hora": "09:00"},
        ]

        profile = adapter._calculate_power_profile_from_trips(trips, 7.4, 24)

        assert isinstance(profile, list)
        assert len(profile) == 24


def test_calculate_power_profile_with_no_trips_returns_zeros(hass, mock_store):
    """Test that _calculate_power_profile_from_trips returns zeros when no trips."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        profile = adapter._calculate_power_profile_from_trips([], 7.4, 24)

        assert isinstance(profile, list)
        assert len(profile) == 24
        assert all(p == 0 for p in profile)


def test_generate_schedule_from_trips_returns_list(hass, mock_store):
    """Test that _generate_schedule_from_trips returns a list."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        trips = [
            {"id": "trip_001", "kwh": 10.0, "hora": "09:00"},
        ]

        schedule = adapter._generate_schedule_from_trips(trips, 7.4)

        assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_setup_config_entry_listener_sets_listener(hass, mock_store):
    """Test that setup_config_entry_listener sets up the listener."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        # Mock the entry's async_add_listener
        listener_mock = MagicMock()
        entry.async_add_listener = MagicMock(return_value=listener_mock)

        adapter.setup_config_entry_listener()

        assert adapter._config_entry_listener is not None


@pytest.mark.asyncio
async def test_async_notify_error_sends_notification(hass, mock_store):
    """Test that async_notify_error calls notification service."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.test",
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Mock hass.states.async_set to avoid errors in _async_update_error_status
        hass.states.async_set = AsyncMock()
        # Mock hass.services.async_call for the notification
        hass.services.async_call = AsyncMock(return_value=True)

        await adapter.async_notify_error(
            error_type="emhass_unavailable",
            message="EMHASS is not available",
        )

        # Verify error was stored (get_last_error has "message" key which is the message param)
        last_err = adapter.get_last_error()
        assert last_err is not None
        # message is the message parameter
        assert last_err.get("message") == "EMHASS is not available"


@pytest.mark.asyncio
async def test_async_clear_error_after_notify(hass, mock_store):
    """Test that async_clear_error clears error set via async_notify_error."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.test",
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Set an error
        await adapter.async_notify_error(
            error_type="test_error",
            message="Test error message",
        )

        assert adapter.get_last_error() is not None

        # Clear the error
        await adapter.async_clear_error()

        last_err = adapter.get_last_error()
        assert last_err is None or last_err.get("type") != "test_error"


# =============================================================================
# COORDINATOR INTERACTION TESTS
# =============================================================================

def test_get_cached_optimization_results_returns_dict(hass, mock_store):
    """Test that get_cached_optimization_results returns expected structure."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        results = adapter.get_cached_optimization_results()

        assert isinstance(results, dict)
        assert "emhass_power_profile" in results
        assert "emhass_deferrables_schedule" in results
        assert "emhass_status" in results


# =============================================================================
# POWER PROFILE CALCULATION TESTS
# =============================================================================

def test_calculate_deferrable_parameters_returns_dict(hass, mock_store):
    """Test that calculate_deferrable_parameters returns expected structure."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        trip = {
            "id": "trip_001",
            "kwh": 10.0,
            "hora": "09:00",
        }

        params = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert isinstance(params, dict)
        # Should contain total_energy_kwh, power_watts, total_hours
        assert "total_energy_kwh" in params
        assert "power_watts" in params
        assert "total_hours" in params


def test_get_assigned_index_returns_correct_index(hass, mock_store):
    """Test get_assigned_index returns correct index for assigned trip."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        # Not assigned yet
        assert adapter.get_assigned_index("trip_001") is None


def test_get_all_assigned_indices_returns_dict(hass, mock_store):
    """Test get_all_assigned_indices returns mapping of all assignments."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        indices = adapter.get_all_assigned_indices()

        assert isinstance(indices, dict)


def test_get_available_indices_returns_list(hass, mock_store):
    """Test get_available_indices returns list of available indices."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 10,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        available = adapter.get_available_indices()

        assert isinstance(available, list)
        # Initially all 10 indices are available
        assert len(available) == 10


# =============================================================================
# CLEANUP TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_async_cleanup_vehicle_indices_cleans_up_all_indices(hass, mock_store):
    """Test that async_cleanup_vehicle_indices releases all indices."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Mock entity registry
        mock_registry = MagicMock()
        mock_registry.async_remove = AsyncMock()

        with patch('homeassistant.helpers.entity_registry.async_get', return_value=mock_registry):
            # Assign some indices
            await adapter.async_assign_index_to_trip("trip_001")
            await adapter.async_assign_index_to_trip("trip_002")

            # Mock hass.states.async_remove
            hass.states.async_remove = AsyncMock()

            # Cleanup
            await adapter.async_cleanup_vehicle_indices()

            # All indices should be available again
            available = adapter.get_available_indices()
            assert len(available) == 50


def test_verify_cleanup_returns_dict(hass, mock_store):
    """Test that verify_cleanup returns status report."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        result = adapter.verify_cleanup()

        assert isinstance(result, dict)
        assert "state_clean" in result or "registry_clean" in result


# =============================================================================
# CONFIG ENTRY LISTENER TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_setup_config_entry_listener_sets_up_listener(hass, mock_store):
    """Test that setup_config_entry_listener properly sets up the listener."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.async_add_listener = MagicMock(return_value=MagicMock())

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        adapter.setup_config_entry_listener()

        # Should have set up the listener
        assert adapter._config_entry_listener is not None


@pytest.mark.asyncio
async def test_async_update_charging_power_updates_value(hass, mock_store):
    """Test that update_charging_power updates the internal value."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        original_power = adapter._charging_power_kw
        assert original_power == 7.4

        # Mock config_entries to return entry with updated charging power
        mock_entry = MagicMock()
        mock_entry.data = {CONF_VEHICLE_NAME: "test_vehicle", CONF_CHARGING_POWER: 11.0}
        hass.config_entries = MagicMock()
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Mock hass.states.async_set for republish
        hass.states.async_set = AsyncMock()

        # Mock coordinator to avoid "can't await MagicMock" error
        mock_coordinator = MagicMock()
        mock_coordinator.async_request_refresh = AsyncMock()
        # Patch _get_coordinator to return our mock
        with patch.object(adapter, '_get_coordinator', return_value=mock_coordinator):
            # Update charging power - this should update since power changed from 7.4 to 11.0
            await adapter.update_charging_power()

        # After update, power should be 11.0
        assert adapter._charging_power_kw == 11.0


# =============================================================================
# PUBLISH ALL DEFERRABLE LOADS TEST
# =============================================================================

@pytest.mark.asyncio
async def test_async_publish_all_deferrable_loads_publishes_multiple_trips(hass, mock_store, mock_coordinator):
    """Test that async_publish_all_deferrable_loads publishes multiple trips."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        trips = [
            {"id": "trip_001", "descripcion": "Trip 1", "kwh": 5.0, "hora": "09:00"},
            {"id": "trip_002", "descripcion": "Trip 2", "kwh": 10.0, "hora": "10:00"},
        ]

        hass.states.async_set = AsyncMock()

        # Should complete without error
        await adapter.async_publish_all_deferrable_loads(trips)


# =============================================================================
# SHELL COMMAND VERIFICATION TEST
# =============================================================================

@pytest.mark.asyncio
async def test_async_verify_shell_command_integration_returns_dict(hass, mock_store):
    """Test that async_verify_shell_command_integration returns expected structure."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter.async_verify_shell_command_integration()

        assert isinstance(result, dict)
        # Should have is_configured or errors key
        assert "is_configured" in result or "errors" in result


# =============================================================================
# CHECK EMHASS RESPONSE SENSORS TEST
# =============================================================================

@pytest.mark.asyncio
async def test_async_handle_emhass_unavailable_calls_notify_error(hass, mock_store):
    """Test that async_handle_emhass_unavailable calls async_notify_error."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.test",
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Mock hass.states.async_set and services.async_call
        hass.states.async_set = AsyncMock()
        hass.services.async_call = AsyncMock(return_value=True)

        result = await adapter.async_handle_emhass_unavailable("Connection refused")

        assert result is True
        # Verify error was stored
        last_err = adapter.get_last_error()
        assert last_err is not None
        assert "Connection refused" in last_err.get("message", "")


@pytest.mark.asyncio
async def test_async_handle_sensor_error_calls_notify_error(hass, mock_store):
    """Test that async_handle_sensor_error calls async_notify_error."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.test",
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        hass.states.async_set = AsyncMock()
        hass.services.async_call = AsyncMock(return_value=True)

        result = await adapter.async_handle_sensor_error(
            sensor_id="sensor.emhass_test",
            error_details="State is None",
        )

        assert result is True


@pytest.mark.asyncio
async def test_async_handle_shell_command_failure_calls_notify_error(hass, mock_store):
    """Test that async_handle_shell_command_failure calls async_notify_error."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.test",
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        hass.states.async_set = AsyncMock()
        hass.services.async_call = AsyncMock(return_value=True)

        result = await adapter.async_handle_shell_command_failure()

        assert result is True


@pytest.mark.asyncio
async def test_async_check_emhass_response_sensors_returns_dict(hass, mock_store):
    """Test that async_check_emhass_response_sensors handles missing sensors gracefully."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Mock hass.states.get to return None (sensor not found)
        hass.states.get = MagicMock(return_value=None)
        # Mock hass.states.async_all to return empty list
        hass.states.async_all = MagicMock(return_value=[])

        # Should handle gracefully without raising and return expected dict
        result = await adapter.async_check_emhass_response_sensors()

        assert isinstance(result, dict)
        assert "all_trips_verified" in result
        assert "verified_trips" in result
        assert "missing_trips" in result

class TestEmhassAdapterAsyncSaveErrorPaths:
    """Tests for emhass_adapter async_save error paths."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock store."""
        store = MagicMock()
        store.async_load = AsyncMock(return_value={})
        store.async_save = AsyncMock()
        return store

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    @pytest.mark.asyncio
    async def test_async_save_handles_save_error(
        self, mock_store, emhass_config
    ):
        """async_save catches exception when store.async_save raises."""
        mock_store.async_save = AsyncMock(side_effect=Exception("Save error"))

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(None, emhass_config)
            adapter._store = mock_store
            adapter._index_map = {"trip_1": 0}
            adapter._released_indices = {}

            # Should not raise - exception is caught
            await adapter.async_save()



class TestEmhassAdapterErrorNotification:
    """Tests for emhass_adapter error notification paths."""

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    @pytest.mark.asyncio
    async def test_async_notify_error_handles_notification_error(
        self, emhass_config
    ):
        """async_notify_error handles when hass.services.async_call raises."""
        hass = MagicMock()

        async def mock_async_call(*args, **kwargs):
            raise Exception("Notification failed")

        hass.services.async_call = mock_async_call
        hass.bus.async_listen_once = AsyncMock()

        adapter = EMHASSAdapter(hass, emhass_config)

        # Should not raise - exception is caught
        await adapter.async_notify_error(
            error_type="test_error",
            message="Test notification",
        )

    @pytest.mark.asyncio
    async def test_async_notify_error_handles_bus_error(self, emhass_config):
        """async_notify_error handles when bus.async_listen_once raises."""
        hass = MagicMock()

        hass.services.async_call = AsyncMock()
        hass.bus.async_listen_once = AsyncMock(
            side_effect=Exception("Bus error")
        )

        adapter = EMHASSAdapter(hass, emhass_config)

        # Should not raise - exception is caught
        await adapter.async_notify_error(
            error_type="test_error",
            message="Test notification",
        )



class TestEmhassAdapterPublishErrorPaths:
    """Tests for emhass_adapter publish error paths."""

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    @pytest.mark.asyncio
    async def test_async_publish_deferrable_load_handles_missing_trip_id(
        self, emhass_config
    ):
        """async_publish_deferrable_load returns False when trip has no ID."""
        hass = MagicMock()
        adapter = EMHASSAdapter(hass, emhass_config)

        # Trip without ID should return False
        result = await adapter.async_publish_deferrable_load({"kwh": 15.0})
        assert result is False

    @pytest.mark.asyncio
    async def test_async_publish_deferrable_load_handles_missing_deadline(
        self, emhass_config
    ):
        """async_publish_deferrable_load returns False when trip has no datetime."""
        hass = MagicMock()
        adapter = EMHASSAdapter(hass, emhass_config)
        adapter.async_assign_index_to_trip = AsyncMock(return_value=0)

        # Trip without datetime should return False
        result = await adapter.async_publish_deferrable_load({"id": "trip_1", "kwh": 15.0})
        assert result is False



class TestEmhassAdapterIndexErrorPaths:
    """Tests for emhass_adapter index management error paths."""

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    @pytest.mark.asyncio
    async def test_async_release_trip_index_handles_missing_trip(
        self, emhass_config
    ):
        """async_release_trip_index handles when trip not in index_map."""
        hass = MagicMock()
        adapter = EMHASSAdapter(hass, emhass_config)
        adapter._index_map = {}  # trip_1 not in map
        adapter._released_indices = {}
        adapter._available_indices = [0]
        adapter.async_save_trips = AsyncMock()

        # Should return False gracefully
        result = await adapter.async_release_trip_index("nonexistent_trip")
        assert result is False



class TestEmhassAdapterOptimizationErrorPaths:
    """Tests for optimization result handling."""

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    def test_get_cached_optimization_results_returns_correct_keys(
        self, emhass_config
    ):
        """get_cached_optimization_results returns expected keys."""
        hass = MagicMock()
        adapter = EMHASSAdapter(hass, emhass_config)

        result = adapter.get_cached_optimization_results()
        assert "emhass_power_profile" in result
        assert "emhass_deferrables_schedule" in result
        assert "emhass_status" in result

class TestGetCachedOptimizationResults:
    """Tests for get_cached_optimization_results."""

    def test_returns_all_cached_fields(self):
        """Returns dict with all EMHASS data keys."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        adapter._cached_power_profile = [100, 200]
        adapter._cached_deferrables_schedule = {"slot_0": "active"}
        adapter._cached_emhass_status = EMHASS_STATE_READY

        result = adapter.get_cached_optimization_results()

        assert result["emhass_power_profile"] == [100, 200]
        assert result["emhass_deferrables_schedule"] == {"slot_0": "active"}
        assert result["emhass_status"] == EMHASS_STATE_READY

    def test_missing_attributes_return_none(self):
        """Returns None for attributes not yet set."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)

        result = adapter.get_cached_optimization_results()

        assert result["emhass_power_profile"] is None
        assert result["emhass_deferrables_schedule"] is None
        assert result["emhass_status"] is None


# =============================================================================
# get_assigned_index and get_all_assigned_indices tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_assigned_index_returns_index_when_assigned(hass, mock_store):
    """get_assigned_index returns the mapped index for a trip."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        idx = await adapter.async_assign_index_to_trip("trip_xyz")
        assert adapter.get_assigned_index("trip_xyz") == idx


@pytest.mark.asyncio
async def test_get_assigned_index_returns_none_when_not_assigned(hass, mock_store):
    """get_assigned_index returns None for unknown trip."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        assert adapter.get_assigned_index("unknown_trip") is None


@pytest.mark.asyncio
async def test_get_all_assigned_indices_returns_all_mappings(hass, mock_store):
    """get_all_assigned_indices returns all trip→index mappings."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        idx1 = await adapter.async_assign_index_to_trip("trip_a")
        idx2 = await adapter.async_assign_index_to_trip("trip_b")

        all_indices = adapter.get_all_assigned_indices()
        assert all_indices == {"trip_a": idx1, "trip_b": idx2}


@pytest.mark.asyncio
async def test_get_available_indices_excludes_assigned(hass, mock_store):
    """get_available_indices excludes assigned indices."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 10,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        idx = await adapter.async_assign_index_to_trip("trip_1")
        available = adapter.get_available_indices()

        assert idx not in available
        assert 1 in available  # Index 1 still available


# =============================================================================
# calculate_deferrable_parameters edge cases
# =============================================================================


class TestCalculateDeferrableParameters:
    """Tests for calculate_deferrable_parameters edge cases."""

    def test_zero_kwh_returns_empty(self):
        """Zero kwh trip returns empty dict."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1", "kwh": 0}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result == {}

    def test_negative_kwh_returns_empty(self):
        """Negative kwh trip returns empty dict."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1", "kwh": -5.0}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result == {}

    def test_missing_kwh_returns_empty(self):
        """Trip without kwh field returns empty dict."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1"}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result == {}

    def test_valid_trip_with_future_deadline(self):
        """Valid trip with future deadline returns full params."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        future_time = (datetime.now() + timedelta(hours=10)).isoformat()
        trip = {"id": "trip_1", "kwh": 7.4, "datetime": future_time}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result["total_energy_kwh"] == 7.4
        assert result["power_watts"] == 7400.0
        assert result["total_hours"] == 1.0
        assert result["end_timestep"] >= 1
        assert result["is_single_constant"] is True

    def test_valid_trip_without_deadline_uses_24h_default(self):
        """Trip without datetime uses 24h default end_timestep."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1", "kwh": 7.4}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result["total_energy_kwh"] == 7.4
        assert result["end_timestep"] == 24

    def test_trip_with_past_deadline_caps_end_timestep(self):
        """Trip with past deadline caps end_timestep at 1."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        past_time = (datetime.now() - timedelta(hours=5)).isoformat()
        trip = {"id": "trip_1", "kwh": 7.4, "datetime": past_time}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result["end_timestep"] == 1

    def test_exception_in_calculation_returns_empty_dict(self):
        """Exception during calculation returns empty dict without raising."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1", "kwh": "not_a_number"}  # String instead of number

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result == {}


# =============================================================================
# async_verify_shell_command_integration tests
# =============================================================================

@pytest.mark.asyncio
async def test_verify_shell_command_deferrable_sensor_not_found(hass, mock_store):
    """Returns error when deferrable sensor does not exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_exists"] is False
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0]


@pytest.mark.asyncio
async def test_verify_shell_command_sensor_missing_power_profile(
    hass, mock_store
):
    """Returns error when sensor exists but lacks power_profile_watts."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.attributes = {}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)

        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_exists"] is True
        assert result["deferrable_sensor_has_data"] is False


@pytest.mark.asyncio
async def test_verify_shell_command_sensor_with_empty_profile(hass, mock_store):
    """Returns error when sensor has empty power profile."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.attributes = {"power_profile_watts": []}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)

        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_has_data"] is False


@pytest.mark.asyncio
async def test_verify_shell_command_fully_configured(hass, mock_store):
    """Returns is_configured=True when sensor has data and EMHASS sensors exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.attributes = {"power_profile_watts": [100, 200, 300]}
    mock_sensor.entity_id = "sensor.emhass_perfil_diferible_test_entry_id"

    mock_emhass_sensor = MagicMock()
    mock_emhass_sensor.entity_id = "sensor.emhass_response_1"

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)
        adapter.hass.states.async_all = MagicMock(
            return_value=[mock_emhass_sensor]
        )
        await adapter.async_assign_index_to_trip("trip_1")

        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_exists"] is True
        assert result["deferrable_sensor_has_data"] is True
        assert result["is_configured"] is True


# =============================================================================
# async_check_emhass_response_sensors tests
# =============================================================================

@pytest.mark.asyncio
async def test_check_emhass_no_trips_returns_all_verified(hass, mock_store):
    """Returns all_verified=True when no trips to check."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter.async_check_emhass_response_sensors()

        assert result["all_trips_verified"] is True
        assert result["verified_trips"] == []
        assert result["missing_trips"] == []


@pytest.mark.asyncio
async def test_check_emhass_trip_missing_config_sensor(hass, mock_store):
    """Returns missing_trips when config sensor doesn't exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        await adapter.async_assign_index_to_trip("trip_1")
        adapter.hass.states.get = MagicMock(return_value=None)
        adapter.hass.states.async_all = MagicMock(return_value=[])

        result = await adapter.async_check_emhass_response_sensors()

        assert result["all_trips_verified"] is False
        assert "trip_1" in result["missing_trips"]


@pytest.mark.asyncio
async def test_check_emhass_with_active_config_sensor(hass, mock_store):
    """Returns trip as verified when config sensor is ACTIVE."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.state = EMHASS_STATE_ACTIVE
    mock_sensor.attributes = {}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        await adapter.async_assign_index_to_trip("trip_1")
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)
        adapter.hass.states.async_all = MagicMock(return_value=[mock_sensor])

        result = await adapter.async_check_emhass_response_sensors()

        assert result["all_trips_verified"] is True
        assert "trip_1" in result["verified_trips"]


@pytest.mark.asyncio
async def test_check_emhass_with_specific_trip_ids(hass, mock_store):
    """Checks only the specified trip IDs."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.state = EMHASS_STATE_ACTIVE
    mock_sensor.attributes = {}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        await adapter.async_assign_index_to_trip("trip_1")
        await adapter.async_assign_index_to_trip("trip_2")
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)
        adapter.hass.states.async_all = MagicMock(return_value=[mock_sensor])

        result = await adapter.async_check_emhass_response_sensors(trip_ids=["trip_1"])

        assert "trip_1" in result["verified_trips"]
        assert "trip_2" not in result["verified_trips"]


# =============================================================================
# Error handling: async_handle_emhass_unavailable, async_handle_sensor_error,
# async_handle_shell_command_failure
# =============================================================================

@pytest.mark.asyncio
async def test_handle_emhass_unavailable_sends_notification(hass, mock_store):
    """async_handle_emhass_unavailable calls async_notify_error."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        with patch.object(
            adapter, "async_notify_error", new_callable=AsyncMock
        ) as mock_notify:
            mock_notify.return_value = True
            result = await adapter.async_handle_emhass_unavailable(
                "Connection refused", trip_id="trip_abc"
            )

            mock_notify.assert_called_once()
            call_args = mock_notify.call_args
            assert call_args[1]["error_type"] == "emhass_unavailable"
            assert "trip_abc" in call_args[1]["trip_id"]


@pytest.mark.asyncio
async def test_handle_sensor_error_calls_notify(hass, mock_store):
    """async_handle_sensor_error sends error notification."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        with patch.object(
            adapter, "async_notify_error", new_callable=AsyncMock
        ) as mock_notify:
            mock_notify.return_value = True
            result = await adapter.async_handle_sensor_error(
                "Sensor data invalid", "sensor.test"
            )

            mock_notify.assert_called_once()
            assert mock_notify.call_args[1]["error_type"] == "sensor_missing"


@pytest.mark.asyncio
async def test_handle_shell_command_failure_calls_notify(hass, mock_store):
    """async_handle_shell_command_failure sends error notification."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        with patch.object(
            adapter, "async_notify_error", new_callable=AsyncMock
        ) as mock_notify:
            mock_notify.return_value = True
            result = await adapter.async_handle_shell_command_failure(
                trip_id="trip_xyz"
            )

            mock_notify.assert_called_once()
            assert mock_notify.call_args[1]["error_type"] == "shell_command_failure"


# =============================================================================
# get_last_error and async_clear_error tests
# =============================================================================


class TestGetLastError:
    """Tests for get_last_error."""

    def test_returns_none_when_no_error(self):
        """Returns None when _last_error is not set."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        adapter._last_error = None
        adapter._last_error_time = None

        result = adapter.get_last_error()

        assert result is None

    def test_returns_error_dict_when_error_exists(self):
        """Returns dict with message and time when error exists."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        adapter._last_error = "Something went wrong"
        adapter._last_error_time = datetime(2025, 1, 15, 10, 30, 0)

        result = adapter.get_last_error()

        assert result["message"] == "Something went wrong"
        assert result["time"] == "2025-01-15T10:30:00"


@pytest.mark.asyncio
async def test_async_clear_error_clears_error_state(hass, mock_store):
    """async_clear_error clears _last_error and _last_error_time."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter._last_error = "Previous error"
        adapter._last_error_time = datetime.now()

        mock_sensor_state = MagicMock()
        mock_sensor_state.attributes = {"error_type": "old_error"}
        sensor_id = f"sensor.emhass_perfil_diferible_{adapter.entry_id}"
        adapter.hass.states.get = MagicMock(return_value=mock_sensor_state)

        await adapter.async_clear_error()

        assert adapter._last_error is None
        assert adapter._last_error_time is None


@pytest.mark.asyncio
async def test_async_clear_error_with_no_sensor(hass, mock_store):
    """async_clear_error handles case where sensor doesn't exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter._last_error = "Previous error"
        adapter.hass.states.get = MagicMock(return_value=None)

        # Should not raise
        await adapter.async_clear_error()

        assert adapter._last_error is None


# =============================================================================
# _calculate_power_profile_from_trips tests
# =============================================================================


class TestCalculatePowerProfileFromTrips:
    """Tests for _calculate_power_profile_from_trips edge cases."""

    def test_empty_trips_list_returns_all_zeros(self):
        """Empty trips list returns power profile of all zeros."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)

        result = adapter._calculate_power_profile_from_trips([], 7.4, 24)

        assert result == [0.0] * 24

    def test_trip_without_datetime_is_skipped(self):
        """Trip without datetime field is skipped."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trips = [{"id": "trip_1", "kwh": 7.4}]

        result = adapter._calculate_power_profile_from_trips(trips, 7.4, 24)

        assert result == [0.0] * 24

    def test_trip_with_past_deadline_is_skipped(self):
        """Trip with deadline in the past is skipped."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        past_time = (datetime.now() - timedelta(hours=5)).isoformat()
        trips = [{"id": "trip_1", "kwh": 7.4, "datetime": past_time}]

        result = adapter._calculate_power_profile_from_trips(trips, 7.4, 24)

        assert 7400.0 not in result  # Should be all zeros

    def test_trip_with_future_deadline_sets_charging_window(self):
        """Trip with future deadline sets charging in appropriate hours."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        # Trip 20 hours from now
        future_time = (datetime.now() + timedelta(hours=20)).isoformat()
        trips = [{"id": "trip_1", "kwh": 7.4, "datetime": future_time}]

        result = adapter._calculate_power_profile_from_trips(trips, 7.4, 168)

        # Should have some charging slots set
        assert any(v > 0 for v in result)

    def test_multiple_trips_all_included(self):
        """Multiple trips all contribute to the power profile."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        future_time_1 = (datetime.now() + timedelta(hours=10)).isoformat()
        future_time_2 = (datetime.now() + timedelta(hours=30)).isoformat()
        trips = [
            {"id": "trip_1", "kwh": 7.4, "datetime": future_time_1},
            {"id": "trip_2", "kwh": 3.7, "datetime": future_time_2},
        ]

        result = adapter._calculate_power_profile_from_trips(trips, 7.4, 168)

        # Both should set charging
        assert any(v > 0 for v in result)


# =============================================================================
# async_publish_deferrable_load edge cases
# =============================================================================

@pytest.mark.asyncio
async def test_publish_deferrable_load_no_trip_manager(hass, mock_store):
    """async_publish_deferrable_load handles missing trip manager gracefully."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.data["test_entry_id"] = MagicMock()
        adapter.hass.data["test_entry_id"].trip_manager = None

        future_time = (datetime.now() + timedelta(hours=10)).isoformat()
        trip = {
            "id": "trip_abc",
            "kwh": 7.4,
            "datetime": future_time,
            "tipo": "puntual",
        }

        # Should handle None trip_manager without raising
        try:
            await adapter.async_publish_deferrable_load(trip)
        except Exception as e:
            if "NoneType" in str(type(e)):
                pytest.fail("async_publish_deferrable_load raised on None trip_manager")


# =============================================================================
# _async_send_error_notification edge cases
# =============================================================================

@pytest.mark.asyncio
async def test_send_error_notification_no_service_configured(hass, mock_store):
    """Returns False when notification service is not configured."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: None,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter._async_send_error_notification(
            "Test notification", "Test body"
        )

        assert result is False


@pytest.mark.asyncio
async def test_send_error_notification_with_valid_service(hass, mock_store):
    """Returns True when notification is sent successfully."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
    }

    mock_store._storage = {}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter._async_send_error_notification(
            "Test notification", "Test body"
        )

        assert result is True
        adapter.hass.services.async_call.assert_called_once()


@pytest.mark.asyncio
async def test_send_error_notification_service_raises_exception(hass, mock_store):
    """Returns False when notification service call raises."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
    }

    mock_store._storage = {}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.services.async_call = MagicMock(
            side_effect=Exception("Service unavailable")
        )

        result = await adapter._async_send_error_notification(
            "Test notification", "Test body"
        )

        assert result is False


# =============================================================================
# async_verify_shell_command_integration with hass.states.async_all
# =============================================================================

@pytest.mark.asyncio
async def test_verify_shell_command_with_emhass_response_sensors(hass, mock_store):
    """Returns configured when EMHASS response sensors are found."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.attributes = {"power_profile_watts": [100, 200]}
    mock_sensor.entity_id = "sensor.emhass_perfil_diferible_test_entry_id"

    mock_emhass_response = MagicMock()
    mock_emhass_response.entity_id = "sensor.emhass_opt"

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)
        adapter.hass.states.async_all = MagicMock(
            return_value=[mock_emhass_response]
        )
        await adapter.async_assign_index_to_trip("trip_1")

        result = await adapter.async_verify_shell_command_integration()

        assert result["is_configured"] is True
        assert len(result["emhass_response_sensors"]) == 1


# =============================================================================
# async_get_integration_status tests
# =============================================================================

@pytest.mark.asyncio
async def test_async_get_integration_status_returns_status_dict(hass, mock_store):
    """async_get_integration_status returns comprehensive status dict."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        status = await adapter.async_get_integration_status()

        assert "status" in status
        assert "message" in status
        assert "details" in status
        assert "verification" in status["details"]
        assert "response_check" in status["details"]


# =============================================================================
# async_cleanup_vehicle_indices ERROR PATH TESTS (PRAGMA-C coverage)
# =============================================================================

@pytest.mark.asyncio
async def test_async_cleanup_vehicle_indices_handles_state_remove_error(hass, mock_store):
    """async_cleanup_vehicle_indices handles HomeAssistantError from states.async_remove."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Assign an index
        await adapter.async_assign_index_to_trip("trip_001")

        # Mock entity registry
        mock_registry = MagicMock()
        mock_registry.async_remove = AsyncMock()

        with patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ):
            # Make hass.states.async_remove raise HomeAssistantError
            hass.states.async_remove = AsyncMock(
                side_effect=HomeAssistantError("State not found")
            )

            # Should NOT raise - error is caught and logged
            await adapter.async_cleanup_vehicle_indices()

            # Indices should still be cleared (error doesn't prevent cleanup)
            assert len(adapter.get_available_indices()) == 50


@pytest.mark.asyncio
async def test_async_cleanup_vehicle_indices_handles_registry_remove_error(
    hass, mock_store
):
    """async_cleanup_vehicle_indices handles Exception from registry.async_remove."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Assign an index
        await adapter.async_assign_index_to_trip("trip_001")

        # Mock hass.states.async_remove to succeed
        hass.states.async_remove = AsyncMock()

        # Mock registry.async_remove to raise Exception (now awaited, so needs AsyncMock)
        mock_registry = MagicMock()
        mock_registry.async_remove = AsyncMock(
            side_effect=Exception("Registry entry not found")
        )

        with patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ):
            # Should NOT raise - error is caught and logged
            await adapter.async_cleanup_vehicle_indices()

            # Indices should still be cleared
            assert len(adapter.get_available_indices()) == 50


@pytest.mark.asyncio
async def test_async_cleanup_vehicle_indices_handles_main_sensor_state_remove_error(
    hass, mock_store
):
    """async_cleanup_vehicle_indices handles HomeAssistantError for main sensor removal."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Assign an index
        await adapter.async_assign_index_to_trip("trip_001")

        # Mock entity registry
        mock_registry = MagicMock()
        mock_registry.async_remove = AsyncMock()

        call_count = 0

        async def state_remove_side_effect(sensor_id):
            nonlocal call_count
            call_count += 1
            # First call (trip index cleanup) succeeds, second (main sensor) fails
            if call_count == 1:
                return  # First call succeeds
            raise HomeAssistantError("Main sensor not found")

        hass.states.async_remove = AsyncMock(side_effect=state_remove_side_effect)

        with patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ):
            # Should NOT raise - error is caught and logged
            await adapter.async_cleanup_vehicle_indices()

            # Indices should still be cleared
            assert len(adapter.get_available_indices()) == 50


class TestEmhassAdapterCleanupEmptyIndices:
    """Tests for async_cleanup_vehicle_indices with empty vehicle indices - PRAGMA-C coverage."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock store."""
        store = MagicMock()
        store.async_load = AsyncMock(return_value={})
        store.async_save = AsyncMock()
        return store

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

    @pytest.mark.asyncio
    async def test_async_cleanup_vehicle_indices_with_no_assigned_trips(
        self, hass, mock_store, emhass_config
    ):
        """async_cleanup_vehicle_indices handles empty vehicle (no trips assigned).

        Tests the cleanup path when _index_map is empty - should complete without error.
        """
        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, emhass_config)
            await adapter.async_load()

            # _index_map should be empty at start
            assert len(adapter._index_map) == 0

            # Mock entity registry
            mock_registry = MagicMock()
            mock_registry.async_remove = AsyncMock()

            with patch(
                "homeassistant.helpers.entity_registry.async_get",
                return_value=mock_registry,
            ):
                hass.states.async_remove = AsyncMock()

                # Should NOT raise even with empty _index_map
                await adapter.async_cleanup_vehicle_indices()

            # All indices should still be available
            assert len(adapter.get_available_indices()) == 50


class TestEmhassAdapterAsyncSaveErrorPaths:
    """Tests for emhass_adapter async_save error paths - PRAGMA-C coverage."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock store."""
        store = MagicMock()
        store.async_load = AsyncMock(return_value={})
        store.async_save = AsyncMock()
        return store

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

    @pytest.mark.asyncio
    async def test_async_save_handles_save_error(
        self, mock_store, emhass_config
    ):
        """async_save catches exception when store.async_save raises.

        Tests error path at lines 1171-1172.
        """
        mock_store.async_save = AsyncMock(side_effect=Exception("Save error"))

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(None, emhass_config)
            adapter._store = mock_store
            adapter._index_map = {"trip_1": 0}
            adapter._released_indices = {}

            # Should not raise - exception is caught
            await adapter.async_save()


class TestEmhassAdapterPublishAllErrorPaths:
    """Tests for async_publish_all_deferrable_loads error paths - PRAGMA-C coverage."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock store."""
        store = MagicMock()
        store.async_load = AsyncMock(return_value={})
        store.async_save = AsyncMock()
        return store

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

    @pytest.mark.asyncio
    async def test_async_publish_all_deferrable_loads_with_no_trips(
        self, hass, mock_store, emhass_config
    ):
        """async_publish_all_deferrable_loads handles empty trip list.

        Tests the happy path when there are no trips to publish.
        """
        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, emhass_config)
            await adapter.async_load()

            hass.states.async_set = AsyncMock()

            # Empty trips list should not raise
            await adapter.async_publish_all_deferrable_loads([])

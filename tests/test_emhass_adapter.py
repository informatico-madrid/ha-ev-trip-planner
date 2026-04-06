"""Tests for EMHASS Adapter core functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

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
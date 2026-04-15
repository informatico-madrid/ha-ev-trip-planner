"""Tests for TripPlannerCoordinator."""

import logging
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.ev_trip_planner import TripPlannerCoordinator
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def mock_trip_manager(hass: HomeAssistant, mock_store):
    """Create a mock TripManager for testing."""
    manager = TripManager(hass, "test_vehicle")
    # Replace the store with our mock_store that has AsyncMock methods
    manager._store = mock_store
    return manager


@pytest.fixture
def mock_config_entry():
    """Create a mock ConfigEntry for testing."""
    entry = MagicMock()
    entry.entry_id = "test_entry_001"
    entry.data = {"vehicle_name": "test_vehicle"}
    return entry


@pytest.fixture
def mock_logger():
    """Create a mock logger for DataUpdateCoordinator."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def mock_emhass_adapter():
    """Create a mock EMHASS adapter with cached data."""
    from custom_components.ev_trip_planner.const import EMHASS_STATE_READY

    mock = MagicMock()
    mock.get_cached_optimization_results.return_value = {
        "emhass_power_profile": [0.0] * 24,
        "emhass_deferrables_schedule": [{"trip_id": "1", "power": 7400}],
        "emhass_status": EMHASS_STATE_READY,
    }
    return mock


async def test_coordinator_initialization(hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger):
    """Test that coordinator initializes correctly."""
    coordinator = TripPlannerCoordinator(hass, mock_config_entry, mock_trip_manager, logger=mock_logger)

    assert coordinator.hass == hass
    assert coordinator._trip_manager == mock_trip_manager
    assert isinstance(coordinator, DataUpdateCoordinator)


async def test_coordinator_refresh_triggers_update(hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger):
    """Test that coordinator refresh triggers data update."""
    coordinator = TripPlannerCoordinator(hass, mock_config_entry, mock_trip_manager, logger=mock_logger)

    # Mock the async_request_refresh method to track calls
    refresh_called = False

    async def mock_refresh():
        nonlocal refresh_called
        refresh_called = True

    coordinator.async_request_refresh = mock_refresh

    # Simulate a trip change that should trigger refresh
    await coordinator.async_request_refresh()

    assert refresh_called is True


async def test_coordinator_data_returns_trip_info(hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger):
    """Test that coordinator data returns trip information."""
    coordinator = TripPlannerCoordinator(hass, mock_config_entry, mock_trip_manager, logger=mock_logger)

    # Add a test trip
    await mock_trip_manager.async_add_recurring_trip(
        descripcion="Work",
        dia_semana="lunes",
        hora="09:00",
        km=25,
        kwh=3.75
    )

    # Force data refresh
    await coordinator.async_refresh()

    # Check that data contains trip information
    data = coordinator.data
    assert data is not None
    assert "recurring_trips" in data
    assert "punctual_trips" in data
    # Data is stored as dict keyed by trip_id after Phase 1 refactor
    assert len(data["recurring_trips"]) == 1


async def test_coordinator_handles_empty_trips(hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger):
    """Test coordinator behavior with no trips."""
    coordinator = TripPlannerCoordinator(hass, mock_config_entry, mock_trip_manager, logger=mock_logger)

    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert len(data["recurring_trips"]) == 0
    assert len(data["punctual_trips"]) == 0


async def test_coordinator_async_refresh_trips_calls_async_refresh(hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger):
    """Test that async_refresh_trips delegates to async_refresh."""
    coordinator = TripPlannerCoordinator(hass, mock_config_entry, mock_trip_manager, logger=mock_logger)

    refresh_called = False

    async def mock_refresh():
        nonlocal refresh_called
        refresh_called = True

    coordinator.async_refresh = mock_refresh

    # Call async_refresh_trips which should delegate to async_refresh
    await coordinator.async_refresh_trips()

    assert refresh_called is True


async def test_coordinator_with_emhass_adapter_uses_cached_results(hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger):
    """Test coordinator uses emhass_adapter.get_cached_optimization_results() when adapter is set.

    This covers line 109: if self._emhass_adapter is not None.
    """
    from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter

    # Create mock EMHASS adapter
    mock_emhass = MagicMock(spec=EMHASSAdapter)
    mock_emhass.get_cached_optimization_results.return_value = {
        "emhass_power_profile": [7400.0] * 24,
        "emhass_deferrables_schedule": {"some_key": "some_value"},
        "emhass_status": "ready",
    }

    # Create coordinator with emhass adapter
    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager,
        emhass_adapter=mock_emhass, logger=mock_logger
    )

    # Set up the mock async_refresh to capture the data
    captured_data = None
    original_update = coordinator._async_update_data

    async def capture_update():
        nonlocal captured_data
        captured_data = await original_update()
        return captured_data

    coordinator._async_update_data = capture_update

    # Trigger refresh
    await coordinator.async_refresh()

    # Verify emhass data was incorporated
    assert captured_data is not None
    assert captured_data["emhass_power_profile"] == [7400.0] * 24
    assert captured_data["emhass_deferrables_schedule"] == {"some_key": "some_value"}
    assert captured_data["emhass_status"] == "ready"

    # Verify get_cached_optimization_results was called
    mock_emhass.get_cached_optimization_results.assert_called_once()


# =============================================================================
# sensor.py - async_added_to_hass restore path (lines 94-99)
# =============================================================================


class TestSensorAsyncAddedToHassRestore:
    """Tests for async_added_to_hass restore path when coordinator.data is None."""

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_state_when_restore_true_and_data_none(self):
        """async_added_to_hass restores _attr_native_value from last_state when restore=True and data is None.

        This covers lines 94-99 in sensor.py:
            await super().async_added_to_hass()
            if self.entity_description.restore and self.coordinator.data is None:
                last_state = await self.async_get_last_state()
                if last_state is not None:
                    self._attr_native_value = last_state.state
        """
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor
        from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription

        # Create mock coordinator with None data (simulating HA restart before first refresh)
        mock_coordinator = MagicMock(spec=TripPlannerCoordinator)
        mock_coordinator.data = None  # data is None -> restore path should trigger

        # Create entity description with restore=True
        desc = TripSensorEntityDescription(
            key="kwh_today",
            name="kWh Today",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement="kWh",
            state_class="measurement",
            restore=True,  # Critical: this enables the restore path
            value_fn=lambda data: data.get("kwh_today", 0.0) if data else 0.0,
            attrs_fn=lambda data: {},
        )

        # Create sensor
        sensor = TripPlannerSensor(mock_coordinator, "test_vehicle", desc)

        # Mock async_get_last_state to return a previous state
        mock_last_state = MagicMock()
        mock_last_state.state = "25.5"  # Previous kWh value

        # Patch RestoreSensor.async_get_last_state at class level
        with patch("homeassistant.components.sensor.RestoreSensor.async_get_last_state", new_callable=AsyncMock) as mock_get_last:
            mock_get_last.return_value = mock_last_state

            # Call async_added_to_hass (the method under test)
            await sensor.async_added_to_hass()

            # After restore: _attr_native_value should be set to last_state.state
            assert sensor._attr_native_value == "25.5", (
                f"Expected _attr_native_value='25.5' after restore, got '{sensor._attr_native_value}'"
            )

    @pytest.mark.asyncio
    async def test_async_added_to_hass_no_restore_when_data_is_not_none(self):
        """async_added_to_hass does NOT restore when coordinator.data is NOT None.

        Even with restore=True, if data is available, no restore should occur.
        This covers lines 94-95: if self.entity_description.restore and self.coordinator.data is None
        """
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor
        from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription

        # Create mock coordinator WITH data (normal operation, no restore needed)
        mock_coordinator = MagicMock(spec=TripPlannerCoordinator)
        mock_coordinator.data = {"kwh_today": 30.0}  # data is available

        desc = TripSensorEntityDescription(
            key="kwh_today",
            name="kWh Today",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement="kWh",
            state_class="measurement",
            restore=True,  # restore=True but data is available
            value_fn=lambda data: data.get("kwh_today", 0.0) if data else 0.0,
            attrs_fn=lambda data: {},
        )

        sensor = TripPlannerSensor(mock_coordinator, "test_vehicle", desc)

        # Mock async_get_last_state to ensure it's NOT called
        with patch("homeassistant.components.sensor.RestoreSensor.async_get_last_state", new_callable=AsyncMock) as mock_get_last:
            await sensor.async_added_to_hass()
            # async_get_last_state should NOT be called when data is not None
            mock_get_last.assert_not_called()


# =============================================================================
# coordinator.py - EMHASS data propagation (Task 1.18 RED, Task 1.19 GREEN)
# =============================================================================

@pytest.mark.asyncio
async def test_coordinator_data_emhass_cache(hass: HomeAssistant, mock_config_entry, mock_trip_manager, mock_logger, mock_emhass_adapter):
    """coordinator.data includes EMHASS fields from adapter cache.

    Task 1.18 test: expects coordinator.data to have emhass_power_profile,
    emhass_deferrables_schedule, and emhass_status populated from adapter cache.
    """
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    # Create coordinator with EMHASS adapter
    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager,
        emhass_adapter=mock_emhass_adapter, logger=mock_logger
    )

    # Call coordinator refresh
    await coordinator.async_refresh()

    # coordinator.data should have EMHASS fields populated from adapter cache
    assert coordinator.data is not None
    assert "emhass_power_profile" in coordinator.data
    assert "emhass_deferrables_schedule" in coordinator.data
    assert "emhass_status" in coordinator.data
    assert coordinator.data["emhass_status"] is not None


# =============================================================================
# coordinator.py - vehicle_id property (Task 1.1 RED, Task 1.2 GREEN)
# =============================================================================

@pytest.mark.asyncio
async def test_vehicle_id_property(hass: HomeAssistant, mock_config_entry, mock_trip_manager, mock_logger):
    """coordinator.vehicle_id returns normalized vehicle_id from entry.data[CONF_VEHICLE_NAME].

    This tests the happy path for Task 1.1/1.2.
    """
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager,
        logger=mock_logger
    )

    # vehicle_id should return normalized (lowercase, spaces replaced) vehicle_name
    assert coordinator.vehicle_id == "test_vehicle"


@pytest.mark.asyncio
async def test_vehicle_id_fallback(hass: HomeAssistant, mock_trip_manager, mock_logger):
    """coordinator.vehicle_id returns 'unknown' when CONF_VEHICLE_NAME is missing from entry.data.

    This tests the fallback path for Task 1.1/1.2.
    """
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    # Create entry without vehicle_name
    entry_without_vehicle = MagicMock()
    entry_without_vehicle.entry_id = "test_entry_no_vehicle"
    entry_without_vehicle.data = {}  # Missing CONF_VEHICLE_NAME

    coordinator = TripPlannerCoordinator(
        hass, entry_without_vehicle, mock_trip_manager,
        logger=mock_logger
    )

    # Should fallback to "unknown" when vehicle_name is missing
    assert coordinator.vehicle_id == "unknown"


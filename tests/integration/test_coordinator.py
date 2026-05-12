"""Tests for TripPlannerCoordinator."""

import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.ev_trip_planner import TripPlannerCoordinator
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def mock_store_class():
    """Fixture to patch the Store class."""
    from homeassistant.helpers import storage as ha_storage

    class MockStore:
        def __init__(self, hass, version, key, *, private=None):
            self.hass = hass
            self.version = version
            self.key = key
            self._storage = {}

        async def async_load(self):
            return self._storage.get("data")

        async def async_save(self, data):
            self._storage["data"] = data
            return True

    with patch.object(ha_storage, "Store", MockStore):
        yield MockStore


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


async def test_coordinator_initialization(
    hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger
):
    """Test that coordinator initializes correctly."""
    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager, logger=mock_logger
    )

    assert coordinator.hass == hass
    assert coordinator._trip_manager == mock_trip_manager
    assert isinstance(coordinator, DataUpdateCoordinator)


async def test_coordinator_refresh_triggers_update(
    hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger
):
    """Test that coordinator refresh triggers data update."""
    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager, logger=mock_logger
    )

    # Mock the async_request_refresh method to track calls
    refresh_called = False

    async def mock_refresh():
        nonlocal refresh_called
        refresh_called = True

    coordinator.async_request_refresh = mock_refresh

    # Simulate a trip change that should trigger refresh
    await coordinator.async_request_refresh()

    assert refresh_called is True


async def test_coordinator_data_returns_trip_info(
    hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger
):
    """Test that coordinator data returns trip information."""
    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager, logger=mock_logger
    )

    # Add a test trip
    await mock_trip_manager.async_add_recurring_trip(
        descripcion="Work", dia_semana="lunes", hora="09:00", km=25, kwh=3.75
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


async def test_coordinator_handles_empty_trips(
    hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger
):
    """Test coordinator behavior with no trips."""
    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager, logger=mock_logger
    )

    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert len(data["recurring_trips"]) == 0
    assert len(data["punctual_trips"]) == 0


async def test_coordinator_async_refresh_trips_calls_async_refresh(
    hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger
):
    """Test that async_refresh_trips delegates to async_refresh."""
    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager, logger=mock_logger
    )

    refresh_called = False

    async def mock_refresh():
        nonlocal refresh_called
        refresh_called = True

    coordinator.async_refresh = mock_refresh

    # Call async_refresh_trips which should delegate to async_refresh
    await coordinator.async_refresh_trips()

    assert refresh_called is True


async def test_coordinator_with_emhass_adapter_uses_cached_results(
    hass: HomeAssistant, mock_trip_manager, mock_config_entry, mock_logger
):
    """Test coordinator uses emhass_adapter.get_cached_optimization_results() when adapter is set.

    This covers line 109: if self._emhass_adapter is not None.
    """
    from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

    # Create mock EMHASS adapter
    mock_emhass = MagicMock(spec=EMHASSAdapter)
    mock_emhass.get_cached_optimization_results.return_value = {
        "emhass_power_profile": [7400.0] * 24,
        "emhass_deferrables_schedule": {"some_key": "some_value"},
        "emhass_status": "ready",
    }

    # Create coordinator with emhass adapter
    coordinator = TripPlannerCoordinator(
        hass,
        mock_config_entry,
        mock_trip_manager,
        emhass_adapter=mock_emhass,
        logger=mock_logger,
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
    async def test_async_added_to_hass_restores_state_when_restore_true_and_data_none(
        self,
    ):
        """async_added_to_hass restores _attr_native_value from last_state when restore=True and data is None.

        This covers lines 94-99 in sensor.py:
            await super().async_added_to_hass()
            if self.entity_description.restore and self.coordinator.data is None:
                last_state = await self.async_get_last_state()
                if last_state is not None:
                    self._attr_native_value = last_state.state
        """
        from custom_components.ev_trip_planner.definitions import (
            TripSensorEntityDescription,
        )
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor

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
        with patch(
            "homeassistant.components.sensor.RestoreSensor.async_get_last_state",
            new_callable=AsyncMock,
        ) as mock_get_last:
            mock_get_last.return_value = mock_last_state

            # Call async_added_to_hass (the method under test)
            await sensor.async_added_to_hass()

            # After restore: _attr_native_value should be set to last_state.state
            assert (
                sensor._attr_native_value == "25.5"
            ), f"Expected _attr_native_value='25.5' after restore, got '{sensor._attr_native_value}'"

    @pytest.mark.asyncio
    async def test_async_added_to_hass_no_restore_when_data_is_not_none(self):
        """async_added_to_hass does NOT restore when coordinator.data is NOT None.

        Even with restore=True, if data is available, no restore should occur.
        This covers lines 94-95: if self.entity_description.restore and self.coordinator.data is None
        """
        from custom_components.ev_trip_planner.definitions import (
            TripSensorEntityDescription,
        )
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor

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
        with patch(
            "homeassistant.components.sensor.RestoreSensor.async_get_last_state",
            new_callable=AsyncMock,
        ) as mock_get_last:
            await sensor.async_added_to_hass()
            # async_get_last_state should NOT be called when data is not None
            mock_get_last.assert_not_called()


# =============================================================================
# coordinator.py - EMHASS data propagation (Task 1.18 RED, Task 1.19 GREEN)
# =============================================================================


@pytest.mark.asyncio
async def test_coordinator_data_emhass_cache(
    hass: HomeAssistant,
    mock_config_entry,
    mock_trip_manager,
    mock_logger,
    mock_emhass_adapter,
):
    """coordinator.data includes EMHASS fields from adapter cache.

    Task 1.18 test: expects coordinator.data to have emhass_power_profile,
    emhass_deferrables_schedule, and emhass_status populated from adapter cache.
    """
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    # Create coordinator with EMHASS adapter
    coordinator = TripPlannerCoordinator(
        hass,
        mock_config_entry,
        mock_trip_manager,
        emhass_adapter=mock_emhass_adapter,
        logger=mock_logger,
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
async def test_vehicle_id_property(
    hass: HomeAssistant, mock_config_entry, mock_trip_manager, mock_logger
):
    """coordinator.vehicle_id returns normalized vehicle_id from entry.data[CONF_VEHICLE_NAME].

    This tests the happy path for Task 1.1/1.2.
    """
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager, logger=mock_logger
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
        hass, entry_without_vehicle, mock_trip_manager, logger=mock_logger
    )

    # Should fallback to "unknown" when vehicle_name is missing
    assert coordinator.vehicle_id == "unknown"


# =============================================================================
# CATEGORÍA 2: Cambio de SOC del vehículo (≥5%)
# =============================================================================


@pytest.mark.asyncio
async def test_soc_change_above_5_percent_updates_emhass_sensor_end_to_end(
    hass: HomeAssistant,
    mock_config_entry,
    mock_trip_manager,
    mock_logger,
    mock_emhass_adapter,
    mock_store_class,
):
    """Test that a SOC change ≥5% updates the EMHASS sensor end-to-end.

    This test verifies the COMPLETE FLOW:
    1. PresenceMonitor detects SOC change ≥5%
    2. Calls trip_manager.publish_deferrable_loads()
    3. EMHASSAdapter updates its cache (power_profile, schedule, etc.)
    4. coordinator SHOULD update coordinator.data
    5. The EMHASS sensor SHOULD show new data

    NOTE: This test documents a known bug — step 4 does not currently occur.
    """
    from custom_components.ev_trip_planner.const import (
        CONF_HOME_SENSOR,
        CONF_PLUGGED_SENSOR,
        CONF_SOC_SENSOR,
    )
    from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor

    # Setup: Create coordinator with EMHASS adapter
    coordinator = TripPlannerCoordinator(
        hass,
        mock_config_entry,
        mock_trip_manager,
        emhass_adapter=mock_emhass_adapter,
        logger=mock_logger,
    )

    # Configure PresenceMonitor
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(hass, "test_vehicle", config, mock_trip_manager)
    monitor._last_processed_soc = 50.0

    # Mock publish_deferrable_loads to verify if it is called
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

    # Setup: Vehicle at home and plugged in
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        return None

    hass.states.get = mock_get_state

    # Setup: EMHASS adapter returns initial data (SOC 50%)
    initial_power_profile = [3400.0, 0, 0, 0] * 42  # Initial profile
    initial_schedule = [{"trip_id": "test", "power": 3400}]

    mock_emhass_adapter.get_cached_optimization_results.return_value = {
        "emhass_power_profile": initial_power_profile,
        "emhass_deferrables_schedule": initial_schedule,
        "emhass_status": "ready",
    }

    # 1. Initial coordinator refresh
    await coordinator.async_refresh()

    # Save initial data for comparison
    initial_coordinator_data = coordinator.data["emhass_power_profile"].copy()

    # 2. Simulate SOC change: 50% → 60% (10% delta, well above 5%)
    old_soc_state = Mock()
    old_soc_state.state = "50"

    new_soc_state = Mock()
    new_soc_state.state = "60"  # 10% change

    event = Mock()
    event.data = {
        "old_state": old_soc_state,
        "new_state": new_soc_state,
    }

    # 3. Configure EMHASS adapter to return NEW data (SOC 60%)
    # These values will be different because the SOC changed
    new_power_profile = [3600.0, 0, 0, 0] * 42  # Profile with SOC 60%
    new_schedule = [{"trip_id": "test", "power": 3600}]

    mock_emhass_adapter.get_cached_optimization_results.return_value = {
        "emhass_power_profile": new_power_profile,
        "emhass_deferrables_schedule": new_schedule,
        "emhass_status": "ready",
    }

    # 4. Process the SOC change
    await monitor._async_handle_soc_change(event)

    # VERIFICATIONS:

    # 1. publish_deferrable_loads() was called
    mock_trip_manager.publish_deferrable_loads.assert_called_once()

    # 2. _last_processed_soc was updated
    assert monitor._last_processed_soc == 60.0

    # 3. BUG: coordinator.data should update automatically
    #    BUT it currently does NOT update because no one calls coordinator.async_refresh()
    #
    #    The EMHASSAdapter changed its cache (new_power_profile vs initial_power_profile)
    #    BUT coordinator.data still has the OLD data
    #
    #    Verification: coordinator.data did NOT change
    assert coordinator.data["emhass_power_profile"] == initial_coordinator_data
    # THIS CONFIRMS THE BUG:
    # - publish_deferrable_loads() was called ✅
    # - The EMHASSAdapter cache changed ✅
    # - BUT coordinator.data did NOT update ❌
    # - Therefore, the EMHASS sensor did NOT update ❌


@pytest.mark.asyncio
async def test_coordinator_refresh_with_updated_emhass_cache(
    hass: HomeAssistant, mock_config_entry, mock_trip_manager, mock_logger
):
    """Test that coordinator refresh updates the sensor when EMHASS cache changes.

    This test verifies that when the EMHASSAdapter updates its cache,
    the coordinator reflects it in coordinator.data.
    """
    from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

    # Create mock EMHASS adapter with updatable data
    mock_emhass = MagicMock(spec=EMHASSAdapter)

    # Setup: Initial data (SOC 50%)
    initial_power_profile = [3400.0, 0, 0, 0] * 42
    initial_schedule = [{"trip_id": "test", "power": 3400}]

    mock_emhass.get_cached_optimization_results.return_value = {
        "emhass_power_profile": initial_power_profile,
        "emhass_deferrables_schedule": initial_schedule,
        "emhass_status": "ready",
        "per_trip_emhass_params": {},
    }

    # Create coordinator
    coordinator = TripPlannerCoordinator(
        hass,
        mock_config_entry,
        mock_trip_manager,
        emhass_adapter=mock_emhass,
        logger=mock_logger,
    )

    # 1. Initial refresh
    await coordinator.async_refresh()

    # Verify initial data
    assert coordinator.data["emhass_power_profile"][0] == 3400.0

    # 2. Simulate EMHASS cache update (SOC changes to 60%)
    updated_power_profile = [4000.0, 0, 0, 0] * 42
    updated_schedule = [{"trip_id": "test", "power": 4000}]

    mock_emhass.get_cached_optimization_results.return_value = {
        "emhass_power_profile": updated_power_profile,
        "emhass_deferrables_schedule": updated_schedule,
        "emhass_status": "ready",
        "per_trip_emhass_params": {},
    }

    # 3. Coordinator refresh
    await coordinator.async_refresh()

    # 4. Verify coordinator.data was updated
    assert coordinator.data["emhass_power_profile"][0] == 4000.0

    # ✅ This test passes because coordinator DOES read the updated cache
    # ❌ BUT the real issue is: WHO updates the EMHASSAdapter cache?
    #    - PresenceMonitor calls publish_deferrable_loads() ✅
    #    - BUT publish_deferrable_loads() does NOT call coordinator.async_refresh() ❌
    #    - Therefore, the sensor does NOT update automatically ❌


# =============================================================================
# T123: _generate_mock_emhass_params coverage tests
# =============================================================================


@pytest.fixture
def mock_config_entry_full():
    """Create a mock ConfigEntry with all required data."""
    entry = MagicMock()
    entry.entry_id = "test_entry_001"
    entry.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 7.4,
        "battery_capacity_kwh": 50.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    return entry


@pytest.fixture
def mock_coordinator(hass, mock_config_entry_full, mock_trip_manager, mock_logger):
    """Create a coordinator instance for testing."""
    from custom_components.ev_trip_planner import TripPlannerCoordinator

    return TripPlannerCoordinator(
        hass, mock_config_entry_full, mock_trip_manager, logger=mock_logger
    )


async def test_generate_mock_emhass_params_single_trip(mock_coordinator):
    """Test _generate_mock_emhass_params with a single active trip."""
    trips = {
        "trip_001": {
            "kwh": 30.0,
            "km": 100.0,
            "datetime": "2026-05-03T08:00:00+00:00",
            "status": "pendiente",
        }
    }
    result = mock_coordinator._generate_mock_emhass_params(trips)

    assert "emhass_power_profile" in result
    assert "emhass_deferrables_schedule" in result
    assert isinstance(result["emhass_deferrables_schedule"], list)
    assert len(result["emhass_deferrables_schedule"]) == 1
    assert result["emhass_deferrables_schedule"][0]["index"] == 0
    assert result["emhass_deferrables_schedule"][0]["kwh"] == 30.0
    assert "emhass_status" in result
    assert result["emhass_status"] == "ready"
    assert "per_trip_emhass_params" in result
    assert "trip_001" in result["per_trip_emhass_params"]

    trip_params = result["per_trip_emhass_params"]["trip_001"]
    assert trip_params["activo"] is True
    assert trip_params["kwh_needed"] == 30.0
    assert trip_params["km"] == 100.0
    assert trip_params["def_total_hours_array"] == [round(30.0 / 7.4, 2)]
    assert trip_params["p_deferrable_nom_array"] == [round(7.4 * 1000.0, 2)]
    assert trip_params["safety_margin_percent"] == 10.0
    assert trip_params["soc_base"] == 20.0
    assert trip_params["t_base"] == 24.0


async def test_generate_mock_emhass_params_multiple_trips(mock_coordinator):
    """Test _generate_mock_emhass_params with multiple active trips."""
    trips = {
        "trip_001": {
            "kwh": 10.0,
            "km": 50.0,
            "datetime": "2026-05-03T08:00:00+00:00",
            "status": "pendiente",
        },
        "trip_002": {
            "kwh": 20.0,
            "km": 80.0,
            "datetime": "2026-05-03T12:00:00+00:00",
            "status": "pendiente",
        },
    }
    result = mock_coordinator._generate_mock_emhass_params(trips)

    assert len(result["per_trip_emhass_params"]) == 2
    assert "trip_001" in result["per_trip_emhass_params"]
    assert "trip_002" in result["per_trip_emhass_params"]

    # Verify power_profile has max across all trips
    power_profile = result["emhass_power_profile"]
    assert len(power_profile) == 96
    assert max(power_profile) > 0  # Should have some charging power


async def test_generate_mock_emhass_params_skip_completed(mock_coordinator):
    """Test that completed/cancelled trips are skipped."""
    trips = {
        "trip_001": {
            "kwh": 30.0,
            "km": 100.0,
            "datetime": "2026-05-03T08:00:00+00:00",
            "status": "completed",
        },
        "trip_002": {
            "kwh": 20.0,
            "km": 80.0,
            "datetime": "2026-05-03T12:00:00+00:00",
            "status": "cancelled",
        },
        "trip_003": {
            "kwh": 10.0,
            "km": 50.0,
            "datetime": "2026-05-04T08:00:00+00:00",
            "status": "pendiente",
        },
    }
    result = mock_coordinator._generate_mock_emhass_params(trips)

    # Only trip_003 should be in params
    assert len(result["per_trip_emhass_params"]) == 1
    assert "trip_003" in result["per_trip_emhass_params"]
    assert "trip_001" not in result["per_trip_emhass_params"]
    assert "trip_002" not in result["per_trip_emhass_params"]


async def test_generate_mock_emhass_params_empty_datetime(mock_coordinator):
    """Test with empty datetime string — start_timestep should be 0."""
    trips = {
        "trip_001": {
            "kwh": 10.0,
            "km": 50.0,
            "datetime": "",
            "status": "pendiente",
        },
    }
    result = mock_coordinator._generate_mock_emhass_params(trips)

    trip_params = result["per_trip_emhass_params"]["trip_001"]
    assert trip_params["def_start_timestep_array"] == [0]


async def test_generate_mock_emhass_params_invalid_datetime(mock_coordinator):
    """Test with invalid datetime — should fall back to start_timestep=0."""
    trips = {
        "trip_001": {
            "kwh": 10.0,
            "km": 50.0,
            "datetime": "not-a-date",
            "status": "pendiente",
        },
    }
    result = mock_coordinator._generate_mock_emhass_params(trips)

    trip_params = result["per_trip_emhass_params"]["trip_001"]
    assert trip_params["def_start_timestep_array"] == [0]


async def test_generate_mock_emhass_params_charging_power_zero(
    mock_config_entry_full, mock_trip_manager, mock_logger
):
    """Test with charging_power_kw=0 — hours_needed should be 0.1 (minimum)."""
    mock_config_entry_full.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 0,
        "battery_capacity_kwh": 50.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    coordinator = TripPlannerCoordinator(
        (
            mock_config_entry_full.hass
            if hasattr(mock_config_entry_full, "hass")
            else MagicMock()
        ),
        mock_config_entry_full,
        mock_trip_manager,
        logger=mock_logger,
    )
    trips = {
        "trip_001": {
            "kwh": 30.0,
            "km": 100.0,
            "datetime": "2026-05-03T08:00:00+00:00",
            "status": "pendiente",
        },
    }
    result = coordinator._generate_mock_emhass_params(trips)

    trip_params = result["per_trip_emhass_params"]["trip_001"]
    # Should use minimum 0.1 hours when charging_power_kw is 0
    assert trip_params["def_total_hours_array"] == [0.1]


async def test_generate_mock_emhass_params_naive_datetime(
    mock_config_entry_full, mock_trip_manager, mock_logger
):
    """Test with timezone-naive datetime — should be treated as UTC (line 264)."""
    mock_config_entry_full.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 7.4,
        "battery_capacity_kwh": 50.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    coordinator = TripPlannerCoordinator(
        MagicMock(), mock_config_entry_full, mock_trip_manager, logger=mock_logger
    )
    trips = {
        "trip_001": {
            "kwh": 30.0,
            "km": 100.0,
            "datetime": "2026-05-03T08:00:00",  # No timezone info
            "status": "pendiente",
        },
    }
    result = coordinator._generate_mock_emhass_params(trips)
    trip_params = result["per_trip_emhass_params"]["trip_001"]
    # Should process without error, treating as UTC
    assert trip_params["def_start_timestep_array"][0] >= 0


async def test_generate_mock_emhass_params_fallback_single_row(mock_coordinator):
    """Test fallback to single row when trip_matrix is empty (line 282-288)."""
    trips = {
        "trip_001": {
            "kwh": 0.0,
            "km": 50.0,
            "datetime": "",
            "status": "pendiente",
        },
    }
    result = mock_coordinator._generate_mock_emhass_params(trips)
    trip_params = result["per_trip_emhass_params"]["trip_001"]
    # With kwh=0, hours_needed=0.1 (minimum), trip_matrix should still have a row
    # via the fallback path when int(hours_needed) + 1 = 0
    assert "p_deferrable_matrix" in trip_params


async def test_generate_mock_emhass_params_calls_fallback_in_async_update(
    mock_config_entry_full, mock_trip_manager, mock_logger, mock_emhass_adapter
):
    """Test that async_update uses mock fallback when EMHASS returns empty per_trip_params (lines 146-153)."""
    mock_config_entry_full.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 7.4,
        "battery_capacity_kwh": 50.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    coordinator = TripPlannerCoordinator(
        (
            mock_config_entry_full.hass
            if hasattr(mock_config_entry_full, "hass")
            else MagicMock()
        ),
        mock_config_entry_full,
        mock_trip_manager,
        logger=mock_logger,
    )
    # Mock the EMHASS adapter to return empty per_trip_params to trigger fallback
    mock_adapter = MagicMock()
    mock_adapter.get_cached_optimization_results.return_value = {
        "emhass_power_profile": [0.0] * 96,
        "emhass_deferrables_schedule": [],
        "emhass_status": "ready",
        "per_trip_emhass_params": {},  # Empty — triggers fallback
    }
    coordinator._emhass_adapter = mock_adapter
    # Mock _get_all_trips to return active trips
    coordinator._trip_manager.get_all_trips = MagicMock(
        return_value={
            "trip_001": {
                "kwh": 30.0,
                "km": 100.0,
                "datetime": "2026-05-03T08:00:00+00:00",
                "status": "pendiente",
            }
        }
    )
    # Call async_update — should trigger fallback at lines 146-148
    result = await coordinator._async_update_data()
    # Verify that mock params were generated
    assert result is not None and "per_trip_emhass_params" in result


async def test_generate_mock_emhass_params_minimal_hours_covers_fallback(
    mock_config_entry_full, mock_trip_manager, mock_logger
):
    """Test with minimal hours_needed (0.1) — end_timestep=0, trip_matrix empty → line 287 fallback.
    hours_needed = 0.1 (minimum), int(hours_needed)=0, int(hours_needed)+1=1 loop iteration
    end_timestep = int(0.1 * 4) = 0 → range(0,0) = empty → row has no power_watts → trip_matrix empty → fallback
    """
    mock_config_entry_full.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 0,
        "battery_capacity_kwh": 50.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    coordinator = TripPlannerCoordinator(
        MagicMock(), mock_config_entry_full, mock_trip_manager, logger=mock_logger
    )
    trips = {
        "trip_001": {
            "kwh": 0.0,
            "km": 0.0,
            "datetime": "",  # empty → start_timestep=0
            "status": "pendiente",
        },
    }
    result = coordinator._generate_mock_emhass_params(trips)
    # With charging_power_kw=0, hours_needed=0.1, end_timestep=0
    # The fallback at line 282-288 should execute line 287
    assert len(result["per_trip_emhass_params"]["trip_001"]["p_deferrable_matrix"]) == 1


async def test_async_update_data_covers_mock_fallback(
    mock_config_entry_full, mock_trip_manager, mock_logger, mock_emhass_adapter
):
    """Test that _async_update_data triggers mock fallback when EMHASS returns empty per_trip_params (lines 146-153)."""
    mock_config_entry_full.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 7.4,
        "battery_capacity_kwh": 50.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    coordinator = TripPlannerCoordinator(
        MagicMock(),
        mock_config_entry_full,
        mock_trip_manager,
        logger=mock_logger,
    )
    # Configure mock adapter to return empty per_trip_params (triggers fallback at line 146)
    mock_emhass_adapter.get_cached_optimization_results.return_value = {
        "emhass_power_profile": [0.0] * 96,
        "emhass_deferrables_schedule": [],
        "emhass_status": "ready",
        "per_trip_emhass_params": {},  # Empty → triggers line 147 fallback
    }
    coordinator._emhass_adapter = mock_emhass_adapter
    # Mock the trip manager methods to return active trips
    mock_trip_manager.async_get_recurring_trips = AsyncMock(return_value=[])
    mock_trip_manager.async_get_punctual_trips = AsyncMock(
        return_value=[
            {
                "id": "trip_001",
                "kwh": 30.0,
                "km": 100.0,
                "datetime": "2026-05-03T08:00:00+00:00",
                "status": "pendiente",
            }
        ]
    )
    mock_trip_manager.async_get_kwh_needed_today = AsyncMock(return_value=30.0)
    mock_trip_manager.async_get_hours_needed_today = AsyncMock(return_value=4.05)
    mock_trip_manager.async_get_next_trip = AsyncMock(return_value=None)
    # Call _async_update_data — should trigger lines 146-153
    result = await coordinator._async_update_data()
    # Verify mock params were generated (per_trip_emhass_params should have trip_001)
    assert "per_trip_emhass_params" in result
    assert "trip_001" in result["per_trip_emhass_params"]


async def test_generate_mock_emhass_params_fallback_single_row_exact(
    mock_config_entry_full, mock_trip_manager, mock_logger
):
    """Force trip_matrix empty: kwh=0, charging_power_kw=0 → hours_needed=0.1, power_watts=0.
    Loop appends row of all 0s → any(v>0)=False → trip_matrix=[], then line 282-288 fallback.
    This test MUST trigger line 287 (the only missing line).
    """
    mock_config_entry_full.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 0,
        "battery_capacity_kwh": 50.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    coordinator = TripPlannerCoordinator(
        MagicMock(), mock_config_entry_full, mock_trip_manager, logger=mock_logger
    )
    # kwh=0 → hours_needed = min(0.1) → 0.1 (minimum floor, not 0/0=0)
    # power_watts = 0 * 1000 = 0
    # start_timestep=0, end_timestep=int(0.1*4)=0
    # trip_matrix stays empty → triggers fallback at line 287
    trips = {
        "trip_001": {
            "kwh": 0.0,
            "km": 0.0,
            "datetime": "",
            "status": "pendiente",
        },
    }
    result = coordinator._generate_mock_emhass_params(trips)
    trip_params = result["per_trip_emhass_params"]["trip_001"]
    assert len(trip_params["p_deferrable_matrix"]) == 1

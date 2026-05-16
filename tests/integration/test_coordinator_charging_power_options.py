"""Integration test to verify coordinator reads charging_power_kw from options.

BUG: coordinator._generate_mock_emhass_params() reads charging_power_kw ONLY from
entry.data, but users configure it via entry.options (Options Flow). This means
when user sets charging_power_kw=3.4 via options, coordinator falls back to
DEFAULT_CHARGING_POWER=11.0 from data.

EXPECTED: coordinator should read from options first, then data as fallback
ACTUAL: coordinator only reads from data, ignoring options

FLOW:
1. User sets charging_power_kw=3.4 via Options flow -> stored in entry.options
2. Coordinator._generate_mock_emhass_params() is called (e.g., when EMHASS unavailable)
3. Line 244-245: charging_power_kw = self._entry.data.get("charging_power_kw", DEFAULT_CHARGING_POWER)
4. Since data doesn't have charging_power_kw (it's in options), uses DEFAULT=11.0
5. Sensor shows 11000W instead of 3400W

FIX NEEDED:
charging_power_kw = self._entry.options.get("charging_power_kw", 
                                           self._entry.data.get("charging_power_kw"))
# If still None, return empty/incomplete data instead of DEFAULT power
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator


class MockConfigEntry:
    """Mock ConfigEntry with options support."""
    
    def __init__(self, entry_id="test_vehicle"):
        self.entry_id = entry_id
        self.data = {"vehicle_name": "test_vehicle", "battery_capacity_kwh": 50.0}
        self.options = {}  # User sets charging_power_kw via options flow


class MockHass:
    """Mock HomeAssistant."""
    
    def __init__(self):
        self.states = MagicMock()
        self.config_entries = MagicMock()
        self.services = MagicMock()
        self.logger = logging.getLogger("test")


@pytest.fixture
def mock_hass():
    """Create mock hass."""
    return MockHass()


@pytest.fixture
def mock_config_entry():
    """Create mock config entry."""
    return MockConfigEntry()


@pytest.fixture
def mock_trip_manager():
    """Create mock trip_manager."""
    manager = MagicMock()
    manager._schedule = MagicMock()
    manager._schedule.publish_deferrable_loads = AsyncMock()
    return manager


class TestCoordinatorChargingPowerFromOptions:
    """Test coordinator reads charging_power_kw from options, not just data."""

    def test_options_charging_power_not_used_by_coordinator(self, mock_hass, mock_config_entry, mock_trip_manager):
        """BUG: coordinator ignores charging_power_kw in options, uses DEFAULT.
        
        This test should FAIL until the bug is fixed.
        """
        # User configures 3.4kW via Options flow (stored in options, not data)
        mock_config_entry.options = {"charging_power_kw": 3.4}
        # data has NO charging_power_kw - it's in options
        
        # Create coordinator
        coordinator = TripPlannerCoordinator(
            hass=mock_hass,
            entry=mock_config_entry,
            trip_manager=mock_trip_manager,
        )
        
        # Create mock trips
        mock_trips = {
            "trip1": {
                "id": "trip1",
                "kwh": 5.0,  # 5kWh needed
                "datetime": "2026-05-20T08:00:00",
                "activo": True,
            }
        }
        
        # Generate mock EMHASS params
        result = coordinator._generate_mock_emhass_params(mock_trips)
        
        # Get the per_trip_params
        per_trip = result.get("per_trip_emhass_params", {})
        trip1_data = per_trip.get("trip1", {})
        
        # Get power_watts - this is power in WATTS (scalar, not array)
        p_deferrable_nom = trip1_data.get("power_watts", 0)

        # BUG: power_watts shows 11000W (11kW DEFAULT) instead of 3400W (3.4kW user configured)
        # This assertion should FAIL when bug exists
        assert p_deferrable_nom == 3400.0, \
            f"Expected 3400W (3.4kW from options), got {p_deferrable_nom}W. " \
            f"Coordinator is using DEFAULT_CHARGING_POWER=11.0 instead of options value!"

    def test_data_charging_power_used_as_fallback(self, mock_hass, mock_config_entry, mock_trip_manager):
        """When charging_power_kw is in data (not options), coordinator should use it."""
        # User configured charging_power_kw=6.6 via data (initial config)
        mock_config_entry.data["charging_power_kw"] = 6.6
        mock_config_entry.options = {}  # No options set
        
        coordinator = TripPlannerCoordinator(
            hass=mock_hass,
            entry=mock_config_entry,
            trip_manager=mock_trip_manager,
        )
        
        mock_trips = {
            "trip1": {
                "id": "trip1",
                "kwh": 5.0,
                "datetime": "2026-05-20T08:00:00",
                "activo": True,
            }
        }
        
        result = coordinator._generate_mock_emhass_params(mock_trips)
        per_trip = result.get("per_trip_emhass_params", {})
        trip1_data = per_trip.get("trip1", {})
        p_deferrable_nom = trip1_data.get("power_watts", 0)
        
        # Should use 6.6kW from data = 6600W
        assert p_deferrable_nom == 6600.0, \
            f"Expected 6600W (6.6kW from data), got {p_deferrable_nom}W"

    def test_options_takes_precedence_over_data(self, mock_hass, mock_config_entry, mock_trip_manager):
        """When charging_power_kw is in BOTH options and data, options should win."""
        # User initially configured 6.6kW via data, then changed to 3.4kW via options
        mock_config_entry.data["charging_power_kw"] = 6.6
        mock_config_entry.options = {"charging_power_kw": 3.4}
        
        coordinator = TripPlannerCoordinator(
            hass=mock_hass,
            entry=mock_config_entry,
            trip_manager=mock_trip_manager,
        )
        
        mock_trips = {
            "trip1": {
                "id": "trip1",
                "kwh": 5.0,
                "datetime": "2026-05-20T08:00:00",
                "activo": True,
            }
        }
        
        result = coordinator._generate_mock_emhass_params(mock_trips)
        per_trip = result.get("per_trip_emhass_params", {})
        trip1_data = per_trip.get("trip1", {})
        p_deferrable_nom = trip1_data.get("power_watts", 0)
        
        # Should use 3.4kW from options (not 6.6kW from data)
        assert p_deferrable_nom == 3400.0, \
            f"Expected 3400W (options), got {p_deferrable_nom}W"


class TestCoordinatorNoDefaultPower:
    """Test that coordinator does NOT use DEFAULT_CHARGING_POWER as fallback.
    
    When charging_power_kw is not configured (None), coordinator should return
    empty/incomplete data instead of using a default value that could mislead users.
    """

    def test_no_charging_power_returns_empty_attributes(self, mock_hass, mock_config_entry, mock_trip_manager):
        """When charging_power_kw is None (not in options or data), return empty.
        
        BUG: Currently returns DEFAULT_CHARGING_POWER=11.0 which misleads users.
        FIX: Should return empty or skip the trip entirely.
        """
        # Explicitly NO charging_power_kw in data or options
        mock_config_entry.data = {"vehicle_name": "test_vehicle"}  # No charging_power_kw
        mock_config_entry.options = {}  # No options
        
        coordinator = TripPlannerCoordinator(
            hass=mock_hass,
            entry=mock_config_entry,
            trip_manager=mock_trip_manager,
        )
        
        mock_trips = {
            "trip1": {
                "id": "trip1",
                "kwh": 5.0,
                "datetime": "2026-05-20T08:00:00",
                "activo": True,
            }
        }
        
        result = coordinator._generate_mock_emhass_params(mock_trips)
        per_trip = result.get("per_trip_emhass_params", {})
        
        # BUG: Returns data with DEFAULT power instead of empty
        # FIXED: Should return empty per_trip_emhass_params when no charging_power_kw configured
        # This assertion should FAIL when bug exists
        assert per_trip == {} or per_trip.get("trip1", {}).get("power_watts") is None or per_trip.get("trip1", {}).get("power_watts", 0) == 0, \
            f"Expected empty or 0 when no charging_power_kw configured, got per_trip={per_trip}"


if __name__ == "__main__":
    print("Running integration test for coordinator charging_power_kw from options...")
    pytest.main([__file__, "-v", "-s"])
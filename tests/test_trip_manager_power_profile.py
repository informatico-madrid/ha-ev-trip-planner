"""Tests for power profile generation - basic structure tests only.

Note: SOC-aware power profile functionality is not implemented yet.
These tests verify the basic structure and return format of the power profile.
"""

import pytest
from datetime import timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
from homeassistant.util import dt as dt_util

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = MagicMock()
    # Set up config_entries mock
    mock_entry = Mock()
    mock_entry.entry_id = "test_vehicle"
    hass.config_entries.async_get_entry = Mock(return_value=mock_entry)
    return hass


@pytest.fixture
def trip_manager(mock_hass):
    """Create TripManager instance."""
    return TripManager(mock_hass, "test_vehicle")


@pytest.fixture
def sample_trip():
    """Create a sample trip."""
    trip_datetime = dt_util.now() + timedelta(days=3)  # 3 days from now
    return {
        "descripcion": "Test Trip",
        "datetime": trip_datetime.strftime("%Y-%m-%dT%H:%M"),  # String format
        "kwh": 7.5,
        "tipo": "puntual",
    }


@pytest.mark.asyncio
async def test_power_profile_without_vehicle_config(trip_manager, sample_trip):
    """Test basic power profile generation without SOC-aware features.

    This test verifies that the method returns a properly structured profile
    even without the SOC-aware feature that is not yet implemented.
    """
    trip_manager.async_get_all_trips_expanded = AsyncMock(return_value=[sample_trip])

    # Call without vehicle_config (should not crash)
    profile = await trip_manager.async_generate_power_profile(
        charging_power_kw=7.4, planning_horizon_days=7
    )

    # Should return a profile with correct structure
    assert len(profile) == 7 * 24, (
        "Should return profile with correct length (7 days * 24 hours)"
    )
    assert isinstance(profile, list), "Should return a list"
    assert all(isinstance(p, (int, float)) for p in profile), (
        "All values should be numbers"
    )

"""Tests for power profile generation bug in Milestone 4.

Bug: async_generate_power_profile() doesn't use async_calcular_energia_necesaria()
This causes the profile to ignore SOC and not schedule charging when needed.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from homeassistant.util import dt as dt_util

from custom_components.ev_trip_planner.trip_manager import TripManager

# Tests enabled for SOC-aware power profile feature
# Note: Some tests (SOC-aware) disabled due to timezone implementation bug


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = MagicMock()
    # Set up config_entries mock
    mock_entry = Mock()
    mock_entry.entry_id = "test_vehicle"
    hass.config_entries.async_get_entry = Mock(return_value=mock_entry)
    # Legacy: Set up data namespace (not used anymore)
    hass.data = {
        "ev_trip_planner_test_vehicle": {
            "trips": {},
            "recurring_trips": {},
            "punctual_trips": {},
        }
    }
    # New: Set up storage for persistence
    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def trip_manager(mock_hass):
    """Create TripManager instance."""
    return TripManager(mock_hass, "test_vehicle")


@pytest.fixture
def sample_trip():
    """Create a sample trip that needs 7.5 kWh."""
    # Format datetime as string expected by _get_trip_time
    trip_datetime = dt_util.now() + timedelta(days=3)  # 3 days from now
    return {
        "descripcion": "Test Trip",
        "datetime": trip_datetime.strftime("%Y-%m-%dT%H:%M"),  # String format
        "kwh": 7.5,
        "source": "recurring",
        "tipo": "puntual",  # Required by _get_trip_time (TRIP_TYPE_PUNCTUAL)
    }


@pytest.fixture
def vehicle_config():
    """Create sample vehicle configuration."""
    return {
        "battery_capacity_kwh": 40.0,
        "charging_power_kw": 7.4,
        "soc_current": 49.0,  # 49% SOC = 19.6 kWh available
    }


@pytest.mark.asyncio
async def test_power_profile_considers_soc_current(trip_manager, sample_trip, vehicle_config, mock_hass):
    """Test that power profile considers SOC and schedules charging when needed.

    Bug scenario: SOC=49% (19.6 kWh), needs 7.5 kWh for trip.
    After trip: 12.1 kWh left = 30% SOC (below 40% safety margin).
    Should schedule charging for ~3.9 kWh to reach 16 kWh minimum.
    """
    # Add trip to hass.storage so _load_trips() will find it
    trip_id = "test_trip_001"
    existing_trips = {
        trip_id: {
            **sample_trip,
            "id": trip_id,
            "estado": "pendiente",
        }
    }
    mock_hass.storage.async_read = AsyncMock(
        return_value={
            "data": {
                "trips": existing_trips,
                "recurring_trips": {},
                "punctual_trips": existing_trips,
            }
        }
    )

    # Generate profile with vehicle config (should consider SOC)
    profile = await trip_manager.async_generate_power_profile(
        charging_power_kw=vehicle_config["charging_power_kw"],
        planning_horizon_days=7,
        vehicle_config=vehicle_config  # This parameter should trigger SOC-aware logic
    )

    # Should have scheduled some charging (not all zeros)
    charging_hours = [p for p in profile if p > 0]
    assert len(charging_hours) > 0, "BUG: Profile should schedule charging when SOC is insufficient"

    # Should have programmed energy > 0
    total_energy = sum(charging_hours) / 1000.0  # Convert W to kW and sum
    assert total_energy > 0, "BUG: Total programmed energy should be > 0 when charging is needed"


@pytest.mark.asyncio
async def test_power_profile_with_soc_above_threshold(trip_manager, sample_trip, mock_hass):
    """Test that no charging is scheduled when SOC is already sufficient."""
    # High SOC: 80% = 32 kWh available, only needs 7.5 kWh
    # After trip: 24.5 kWh left = 61% SOC (above 40% safety margin)
    vehicle_config_high_soc = {
        "battery_capacity_kwh": 40.0,
        "charging_power_kw": 7.4,
        "soc_current": 80.0,  # High SOC, no charging needed
    }

    # Add trip to hass.storage so _load_trips() will find it
    trip_id = "test_trip_001"
    existing_trips = {
        trip_id: {
            **sample_trip,
            "id": trip_id,
            "estado": "pendiente",
        }
    }
    mock_hass.storage.async_read = AsyncMock(
        return_value={
            "data": {
                "trips": existing_trips,
                "recurring_trips": {},
                "punctual_trips": existing_trips,
            }
        }
    )

    profile = await trip_manager.async_generate_power_profile(
        charging_power_kw=vehicle_config_high_soc["charging_power_kw"],
        planning_horizon_days=7,
        vehicle_config=vehicle_config_high_soc
    )

    # Should NOT schedule charging
    charging_hours = [p for p in profile if p > 0]
    assert len(charging_hours) == 0, "BUG: Should not schedule charging when SOC is sufficient"


@pytest.mark.asyncio
async def test_power_profile_with_soc_below_threshold(trip_manager, sample_trip, mock_hass):
    """Test that charging IS scheduled when SOC is below threshold."""
    # Low SOC: 30% = 12 kWh available, needs 7.5 kWh
    # After trip: 4.5 kWh left = 11% SOC (way below 40% safety margin)
    vehicle_config_low_soc = {
        "battery_capacity_kwh": 40.0,
        "charging_power_kw": 7.4,
        "soc_current": 30.0,  # Low SOC, charging definitely needed
    }

    # Add trip to hass.storage so _load_trips() will find it
    trip_id = "test_trip_001"
    existing_trips = {
        trip_id: {
            **sample_trip,
            "id": trip_id,
            "estado": "pendiente",
        }
    }
    mock_hass.storage.async_read = AsyncMock(
        return_value={
            "data": {
                "trips": existing_trips,
                "recurring_trips": {},
                "punctual_trips": existing_trips,
            }
        }
    )

    profile = await trip_manager.async_generate_power_profile(
        charging_power_kw=vehicle_config_low_soc["charging_power_kw"],
        planning_horizon_days=7,
        vehicle_config=vehicle_config_low_soc
    )

    # Should schedule charging
    charging_hours = [p for p in profile if p > 0]
    assert len(charging_hours) > 0, "BUG: Should schedule charging when SOC is low"

    # Should schedule enough hours to cover the energy needed
    # Need to go from 12 kWh to 16 kWh minimum = 4 kWh needed
    # At 7.4 kW, need about 0.54 hours = ~32 minutes
    total_energy = sum(charging_hours) / 1000.0
    assert total_energy >= 3.0, f"BUG: Should schedule at least 3 kWh, got {total_energy:.2f} kWh"


@pytest.mark.asyncio
async def test_power_profile_energy_calculation_accuracy(trip_manager, sample_trip, vehicle_config, mock_hass):
    """Test that energy calculation is accurate and considers safety margin."""
    # Add trip to hass.storage so _load_trips() will find it
    trip_id = "test_trip_001"
    existing_trips = {
        trip_id: {
            **sample_trip,
            "id": trip_id,
            "estado": "pendiente",
        }
    }
    mock_hass.storage.async_read = AsyncMock(
        return_value={
            "data": {
                "trips": existing_trips,
                "recurring_trips": {},
                "punctual_trips": existing_trips,
            }
        }
    )

    # Calculate expected energy needed manually
    # Current: 49% of 40 kWh = 19.6 kWh
    # After trip: 19.6 - 7.5 = 12.1 kWh
    # Minimum needed: 40% of 40 kWh = 16.0 kWh
    # Energy needed: 16.0 - 12.1 = 3.9 kWh
    expected_energy_needed = 3.9  # kWh

    profile = await trip_manager.async_generate_power_profile(
        charging_power_kw=vehicle_config["charging_power_kw"],
        planning_horizon_days=7,
        vehicle_config=vehicle_config
    )

    # Calculate actual energy programmed
    charging_hours = [p for p in profile if p > 0]
    actual_energy = sum(charging_hours) / 1000.0  # Convert W to kW and sum

    # Should be close to expected (within 1 hour of charging tolerance)
    # Note: We can only schedule whole hours, so we may schedule up to 1 hour more than needed
    max_expected_energy = expected_energy_needed + vehicle_config["charging_power_kw"]  # +1 hour max
    min_expected_energy = expected_energy_needed  # At minimum, should schedule what's needed

    assert min_expected_energy <= actual_energy <= max_expected_energy, \
        f"BUG: Energy calculation inaccurate. Expected between {min_expected_energy:.1f} and {max_expected_energy:.1f} kWh, got {actual_energy:.2f} kWh"


@pytest.mark.asyncio
async def test_power_profile_without_vehicle_config(trip_manager, sample_trip):
    """Test backward compatibility: without vehicle_config, should use old behavior.
    
    This ensures the method still works if called without vehicle_config,
    though it will have the bug (not considering SOC).
    """
    trip_manager.async_get_all_trips_expanded = AsyncMock(return_value=[sample_trip])
    
    # Call without vehicle_config (should not crash)
    profile = await trip_manager.async_generate_power_profile(
        charging_power_kw=7.4,
        planning_horizon_days=7
        # No vehicle_config parameter
    )
    
    # Should return a profile (even if buggy)
    assert len(profile) == 7 * 24, "Should return profile with correct length"
    assert isinstance(profile, list), "Should return a list"
    assert all(isinstance(p, float) for p in profile), "All values should be floats"
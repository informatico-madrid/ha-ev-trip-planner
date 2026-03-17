"""Tests for deferrables schedule generation.

Tests the schedule generation format according to EMHASS requirements:
- Format: [{"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]
- Timestamps: ISO 8601 format with timezone
- Power values: String format (e.g., "3600.0")
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.trip_manager import TripManager
from custom_components.ev_trip_planner.const import DOMAIN


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance with config entry."""
    hass = Mock()
    hass.data = {}

    # Mock config entry
    mock_entry = Mock()
    mock_entry.data = {
        "vehicle_name": "test_vehicle",
        "battery_capacity_kwh": 50.0,
        "planning_horizon_days": 7,
    }
    mock_entry.config_entry_id = "test_entry_id"

    hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

    return hass


@pytest.fixture
def trip_manager(mock_hass):
    """Create TripManager instance."""
    return TripManager(mock_hass, "test_vehicle")


class TestDeferrablesScheduleGeneration:
    """Tests for async_generate_deferrables_schedule method."""

    async def test_schedule_generation_format(self, trip_manager, hass):
        """Test schedule has correct format with ISO 8601 timestamps and string power values."""
        # Mock dependencies
        trip_manager._load_trips = AsyncMock()
        trip_manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
        trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0] * 168  # 7 days * 24 hours
        )

        # Generate schedule
        schedule = await trip_manager.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=7,
        )

        # Verify structure
        assert len(schedule) == 168, "Should have 168 entries (7 days * 24 hours)"

        # Verify first entry format
        first_entry = schedule[0]
        assert "date" in first_entry, "Entry should have 'date' key"
        assert "p_deferrable0" in first_entry, "Entry should have 'p_deferrable0' key"

        # Verify date is ISO 8601 with timezone
        date_str = first_entry["date"]
        assert "+" in date_str or "Z" in date_str.upper(), \
            f"Date should include timezone info: {date_str}"

        # Verify power value is string
        power_value = first_entry["p_deferrable0"]
        assert isinstance(power_value, str), "Power value should be string"
        assert "." in power_value, "Power value should have decimal point"

    async def test_schedule_length_equals_planning_horizon(self, trip_manager):
        """Test schedule has correct number of entries for different planning horizons."""
        trip_manager._load_trips = AsyncMock()
        trip_manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
        trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0] * 24
        )

        # Test with 1 day
        schedule = await trip_manager.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )
        assert len(schedule) == 24, "Should have 24 entries for 1 day"

        # Test with 3 days
        trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0] * 72
        )
        schedule = await trip_manager.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=3,
        )
        assert len(schedule) == 72, "Should have 72 entries for 3 days"

        # Test with 14 days
        trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0] * 336
        )
        schedule = await trip_manager.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=14,
        )
        assert len(schedule) == 336, "Should have 336 entries for 14 days"

    async def test_schedule_power_values_are_strings(self, trip_manager):
        """Test power values are always strings with decimal point."""
        trip_manager._load_trips = AsyncMock()
        trip_manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
        trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0, 3600.0, 7200.0, 0.0]
        )

        schedule = await trip_manager.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        # Check all power values are strings
        for entry in schedule:
            power_value = entry["p_deferrable0"]
            assert isinstance(power_value, str), \
                f"Power value should be string, got {type(power_value)}"
            # Verify it can be converted to float
            float(power_value)

    async def test_schedule_timestamps_are_sequential(self, trip_manager):
        """Test schedule timestamps are in sequential order."""
        trip_manager._load_trips = AsyncMock()
        trip_manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
        trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0] * 48
        )

        schedule = await trip_manager.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=2,
        )

        # Parse timestamps and verify they're 1 hour apart
        timestamps = [datetime.fromisoformat(entry["date"]) for entry in schedule]

        for i in range(1, len(timestamps)):
            diff = timestamps[i] - timestamps[i - 1]
            assert diff == timedelta(hours=1), \
                f"Timestamps should be 1 hour apart, got {diff}"

    async def test_schedule_with_charging_power(self, trip_manager):
        """Test schedule includes charging power values correctly."""
        trip_manager._load_trips = AsyncMock()
        trip_manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
        # Return profile with some charging periods
        trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0, 0.0, 3600.0, 3600.0, 0.0]
        )

        schedule = await trip_manager.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        # Verify charging power is included correctly
        assert schedule[2]["p_deferrable0"] == "3600.0", \
            "Should have 3600W charging at hour 2"
        assert schedule[3]["p_deferrable0"] == "3600.0", \
            "Should have 3600W charging at hour 3"

    async def test_schedule_iso_format_with_timezone(self, trip_manager):
        """Test that timestamps include timezone offset in ISO format."""
        trip_manager._load_trips = AsyncMock()
        trip_manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
        trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0]
        )

        schedule = await trip_manager.async_generate_deferrables_schedule(
            charging_power_kw=3.6,
            planning_horizon_days=1,
        )

        date_str = schedule[0]["date"]

        # ISO 8601 with timezone should match pattern like:
        # 2026-03-17T14:00:00+01:00 or 2026-03-17T14:00:00+01:00:00
        # The key is it should have 'T' and timezone offset (+ or -)
        assert "T" in date_str, "ISO format should contain 'T' separator"
        assert ("+" in date_str) or (date_str.endswith("Z")) or ("-" in date_str and date_str.index("-") > date_str.index("T")), \
            f"ISO format should include timezone: {date_str}"

"""Tests for uncovered services/_utils.py paths."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.services._utils import (
    _ensure_setup,
    _find_entry_by_vehicle,
    _get_coordinator,
    _get_manager,
    build_presence_config,
)


def _make_entry(entry_id: str, vehicle_name: str, data: dict[str, Any] | None = None):
    """Create a mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = data or {"vehicle_name": vehicle_name}
    entry.runtime_data = MagicMock()
    entry.runtime_data.coordinator = MagicMock()
    return entry


class TestFindEntryByVehicle:
    """Test _find_entry_by_vehicle branches."""

    def test_entry_with_none_data_skipped(self):
        """Lines 36-38: Entry with None data logs warning and continues."""
        hass = MagicMock()
        entry_none_data = MagicMock()
        entry_none_data.entry_id = "entry_1"
        entry_none_data.data = None

        entry_valid = _make_entry("entry_2", "test_vehicle", {"vehicle_name": "Test Vehicle"})
        hass.config_entries.async_entries.return_value = [entry_none_data, entry_valid]

        result = _find_entry_by_vehicle(hass, "test_vehicle")

        assert result == entry_valid

    def test_no_matching_vehicle_returns_none(self):
        """Line 43: Returns None when no vehicle matches."""
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = [
            _make_entry("entry_1", "other_vehicle")
        ]

        result = _find_entry_by_vehicle(hass, "nonexistent_vehicle")

        assert result is None


class TestGetCoordinator:
    """Test _get_coordinator branches."""

    def test_returns_none_when_no_entry(self):
        """Line 54: Returns None when no entry found for vehicle."""
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = []

        result = _get_coordinator(hass, "unknown_vehicle")

        assert result is None


class TestGetManager:
    """Test _get_manager error branches."""

    @pytest.mark.asyncio
    async def test_raises_when_vehicle_not_found(self):
        """Lines 62-67: Raises ValueError when no entry found."""
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = []

        with pytest.raises(ValueError) as exc_info:
            await _get_manager(hass, "unknown_vehicle")
        assert "unknown_vehicle" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ensure_setup_is_noop(self):
        """Line 142: _ensure_setup is a no-op pass."""
        mgr = MagicMock()
        await _ensure_setup(mgr)  # Should not raise

    @pytest.mark.asyncio
    async def test_get_manager_creates_new_manager_when_not_in_runtime_data(self):
        """Lines 84-122: Creates new TripManager when runtime_data.trip_manager is None."""
        hass = MagicMock()
        entry = _make_entry("entry_1", "test_vehicle", {"vehicle_name": "Test Vehicle"})
        entry.runtime_data.trip_manager = None  # Not in runtime storage
        hass.config_entries.async_entries.return_value = [entry]

        result = await _get_manager(hass, "test_vehicle")

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_manager_async_setup_exception_caught_and_logged(self):
        """Lines 97-113: Exception in async_setup is caught and logged."""
        hass = MagicMock()
        entry = _make_entry("entry_1", "test_vehicle", {"vehicle_name": "Test Vehicle"})
        entry.runtime_data.trip_manager = None  # Will create new

        # Make async_setup raise
        async_setup_error = RuntimeError("Storage corrupted")
        mock_persistence = MagicMock()
        mock_persistence.async_setup = AsyncMock(side_effect=async_setup_error)
        mock_persistence.async_save_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.trip.manager.TripPersistence",
            return_value=mock_persistence,
        ):
            hass.config_entries.async_entries.return_value = [entry]
            result = await _get_manager(hass, "test_vehicle")

        # Manager still returned despite error
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_manager_returns_existing_manager(self):
        """Lines 123-129: Returns existing manager when already in runtime_data."""
        hass = MagicMock()
        entry = _make_entry("entry_1", "test_vehicle", {"vehicle_name": "Test Vehicle"})

        # Create a real-ish mock manager
        existing_manager = MagicMock()
        existing_manager._state = MagicMock()
        existing_manager._state.recurring_trips = {}
        existing_manager._state.punctual_trips = {}

        entry.runtime_data.trip_manager = existing_manager
        hass.config_entries.async_entries.return_value = [entry]

        result = await _get_manager(hass, "test_vehicle")

        assert result is existing_manager


class TestBuildPresenceConfig:
    """Test build_presence_config (lines 145-167)."""

    def test_build_presence_config_returns_dict_with_all_keys(self):
        """Lines 157-167: Returns dict with all sensor keys from entry.data."""
        entry = MagicMock()
        entry.data = {
            "home_sensor": "sensor.home",
            "plugged_sensor": "sensor.plugged",
            "charging_sensor": "sensor.charging",
            "home_coordinates": {"lat": 40.4, "lon": -3.7},
            "vehicle_coordinates_sensor": "sensor.vehicle_gps",
            "notification_service": "notify.mobile",
            "soc_sensor": "sensor.battery_soc",
        }

        result = build_presence_config(entry)

        assert result["home_sensor"] == "sensor.home"
        assert result["plugged_sensor"] == "sensor.plugged"
        assert result["charging_sensor"] == "sensor.charging"
        assert result["home_coordinates"] == {"lat": 40.4, "lon": -3.7}
        assert result["vehicle_coordinates_sensor"] == "sensor.vehicle_gps"
        assert result["notification_service"] == "notify.mobile"
        assert result["soc_sensor"] == "sensor.battery_soc"

    def test_build_presence_config_with_missing_keys(self):
        """Lines 157-167: Missing keys return None."""
        entry = MagicMock()
        entry.data = {
            "home_sensor": "sensor.home",
            # Other keys missing
        }

        result = build_presence_config(entry)

        assert result["home_sensor"] == "sensor.home"
        assert result["plugged_sensor"] is None
        assert result["charging_sensor"] is None
        assert result["home_coordinates"] is None
        assert result["vehicle_coordinates_sensor"] is None
        assert result["notification_service"] is None
        assert result["soc_sensor"] is None
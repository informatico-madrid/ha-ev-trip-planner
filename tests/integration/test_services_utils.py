"""Tests for services/_utils.py shared utilities.

Covers _find_entry_by_vehicle, _get_coordinator, _get_manager,
_ensure_setup, and build_presence_config.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.ev_trip_planner.services._utils import (
    _ensure_setup,
    _find_entry_by_vehicle,
    _get_coordinator,
    _get_manager,
    build_presence_config,
)
from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_SENSOR,
    CONF_HOME_COORDINATES,
    CONF_HOME_SENSOR,
    CONF_NOTIFICATION_SERVICE,
    CONF_PLUGGED_SENSOR,
    CONF_SOC_SENSOR,
    CONF_VEHICLE_COORDINATES_SENSOR,
)


class TestFindEntryByVehicle:
    """Test _find_entry_by_vehicle helper."""

    def test_find_entry_by_vehicle_match(self) -> None:
        """Should return entry when vehicle names match (case-insensitive)."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "TestVehicle"}
        entry.entry_id = "entry_1"
        hass.config_entries.async_entries.return_value = [entry]

        result = _find_entry_by_vehicle(hass, "testvehicle")
        assert result is entry

    def test_find_entry_by_vehicle_no_match(self) -> None:
        """Should return None when no entry matches."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "OtherVehicle"}
        entry.entry_id = "entry_1"
        hass.config_entries.async_entries.return_value = [entry]

        result = _find_entry_by_vehicle(hass, "testvehicle")
        assert result is None

    def test_find_entry_by_vehicle_none_data(self) -> None:
        """Should skip entries with None data."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = None
        entry.entry_id = "entry_1"
        hass.config_entries.async_entries.return_value = [entry]

        result = _find_entry_by_vehicle(hass, "testvehicle")
        assert result is None

    def test_find_entry_by_vehicle_empty_entries(self) -> None:
        """Should return None when no config entries exist."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries.return_value = []

        result = _find_entry_by_vehicle(hass, "testvehicle")
        assert result is None

    def test_find_entry_by_vehicle_case_insensitive(self) -> None:
        """Vehicle name matching should be case-insensitive."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "Test Vehicle"}
        entry.entry_id = "entry_1"
        hass.config_entries.async_entries.return_value = [entry]

        result = _find_entry_by_vehicle(hass, "test_vehicle")
        assert result is entry

    def test_find_entry_by_vehicle_with_spaces(self) -> None:
        """normalize_vehicle_id handles spaces in vehicle names."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "Mi Vehiculo"}
        entry.entry_id = "entry_1"
        hass.config_entries.async_entries.return_value = [entry]

        result = _find_entry_by_vehicle(hass, "mi_vehiculo")
        assert result is entry


class TestGetCoordinator:
    """Test _get_coordinator helper."""

    def test_get_coordinator_found(self) -> None:
        """Should return coordinator when entry and runtime_data exist."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "entry_1"
        entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(), trip_manager=MagicMock()
        )
        hass.config_entries.async_entries.return_value = [entry]

        result = _get_coordinator(hass, "test_vehicle")
        assert result is entry.runtime_data.coordinator

    def test_get_coordinator_no_entry(self) -> None:
        """Should return None when entry not found."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries.return_value = []

        result = _get_coordinator(hass, "test_vehicle")
        assert result is None

    def test_get_coordinator_no_runtime_data(self) -> None:
        """Should return None when runtime_data is missing."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "entry_1"
        entry.runtime_data = None
        hass.config_entries.async_entries.return_value = [entry]

        result = _get_coordinator(hass, "test_vehicle")
        assert result is None


class TestGetManager:
    """Test _get_manager async helper."""

    @pytest.mark.asyncio
    async def test_get_manager_existing(self) -> None:
        """Should return existing manager from runtime_data."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "entry_1"
        entry.unique_id = "test_vehicle"
        manager = MagicMock()
        manager._recurring_trips = [1, 2]
        manager._punctual_trips = [3]
        entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(), trip_manager=manager
        )
        hass.config_entries.async_entries.return_value = [entry]

        result = await _get_manager(hass, "test_vehicle")
        assert result is manager

    @pytest.mark.asyncio
    async def test_get_manager_vehicle_not_found(self) -> None:
        """Should raise ValueError when vehicle not in config entries."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries.return_value = []

        with pytest.raises(ValueError, match="Vehicle unknown_vehicle not found"):
            await _get_manager(hass, "unknown_vehicle")

    @pytest.mark.asyncio
    async def test_get_manager_create_new(self) -> None:
        """Should create new manager when none in runtime_data."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "entry_1"
        entry.unique_id = "test_vehicle"
        entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(), trip_manager=None
        )
        hass.config_entries.async_entries.return_value = [entry]

        with patch(
            "custom_components.ev_trip_planner.services._utils.TripManager"
        ) as MockManager:
            mock_mgr = MagicMock()
            mock_mgr._recurring_trips = []
            mock_mgr._punctual_trips = []
            MockManager.return_value = mock_mgr
            mock_mgr.async_setup = AsyncMock()

            result = await _get_manager(hass, "test_vehicle")
            assert result is mock_mgr
            MockManager.assert_called_once()
            mock_mgr.async_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_manager_setup_failure(self) -> None:
        """Manager async_setup failure should not propagate."""
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        hass = MagicMock()
        hass.config_entries = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "entry_1"
        entry.unique_id = "test_vehicle"
        entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(), trip_manager=None
        )
        hass.config_entries.async_entries.return_value = [entry]

        with patch(
            "custom_components.ev_trip_planner.services._utils.TripManager"
        ) as MockManager:
            mock_mgr = MagicMock()
            mock_mgr._recurring_trips = []
            mock_mgr._punctual_trips = []
            MockManager.return_value = mock_mgr
            mock_mgr.async_setup = AsyncMock(side_effect=RuntimeError("setup failed"))

            result = await _get_manager(hass, "test_vehicle")
            assert result is mock_mgr


class TestEnsureSetup:
    """Test _ensure_setup helper."""

    @pytest.mark.asyncio
    async def test_ensure_setup_noop(self) -> None:
        """_ensure_setup is currently a no-op and should not raise."""
        mgr = MagicMock()
        await _ensure_setup(mgr)

    @pytest.mark.asyncio
    async def test_ensure_setup_multiple_calls(self) -> None:
        """Calling _ensure_setup multiple times should remain a no-op."""
        mgr = MagicMock()
        await _ensure_setup(mgr)
        await _ensure_setup(mgr)


class TestBuildPresenceConfig:
    """Test build_presence_config helper."""

    def test_build_presence_config_all_fields(self) -> None:
        """Should build config dict with all fields from entry.data."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            CONF_HOME_SENSOR: "sensor.home",
            CONF_PLUGGED_SENSOR: "sensor.plugged",
            CONF_CHARGING_SENSOR: "sensor.charging",
            CONF_HOME_COORDINATES: [40.0, -3.0],
            CONF_VEHICLE_COORDINATES_SENSOR: "sensor.vehicle_coords",
            CONF_NOTIFICATION_SERVICE: "notify.mobile",
            CONF_SOC_SENSOR: "sensor.soc",
        }

        result = build_presence_config(entry)
        assert result[CONF_HOME_SENSOR] == "sensor.home"
        assert result[CONF_PLUGGED_SENSOR] == "sensor.plugged"
        assert result[CONF_CHARGING_SENSOR] == "sensor.charging"
        assert result[CONF_HOME_COORDINATES] == [40.0, -3.0]
        assert result[CONF_VEHICLE_COORDINATES_SENSOR] == "sensor.vehicle_coords"
        assert result[CONF_NOTIFICATION_SERVICE] == "notify.mobile"
        assert result[CONF_SOC_SENSOR] == "sensor.soc"

    def test_build_presence_config_missing_fields(self) -> None:
        """Missing fields should be None in config."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {}

        result = build_presence_config(entry)
        assert result[CONF_HOME_SENSOR] is None
        assert result[CONF_PLUGGED_SENSOR] is None
        assert result[CONF_SOC_SENSOR] is None

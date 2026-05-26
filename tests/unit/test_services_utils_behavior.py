"""Tests for services/_utils.py — targets mutation-observable behavior.

Targets 72 survivors in _get_manager by asserting:
- Return value is TripManager
- Manager properties are correct
- Raises ValueError for unknown vehicle
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.services._utils import (
    _ensure_setup,
    _find_entry_by_vehicle,
    _get_coordinator,
    _get_manager,
)


def _make_runtime_data(coordinator=None, trip_manager=None, emhass_adapter=None):
    """Create a mock runtime_data object."""
    rt = MagicMock()
    rt.coordinator = coordinator
    rt.trip_manager = trip_manager
    rt.emhass_adapter = emhass_adapter
    return rt


def _make_entry(entry_id: str, vehicle_name: str, data: dict[str, Any] | None = None):
    """Create a mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = data or {"vehicle_name": vehicle_name}
    entry.runtime_data = _make_runtime_data()
    return entry


class TestGetManagerReturnsManager:
    """Targets 72 survivors in _get_manager — assert return value mutations."""

    @pytest.mark.asyncio
    async def test_returns_trip_manager_instance(self):
        """Kill mutations: return trip_manager → None or wrong type."""
        from custom_components.ev_trip_planner.trip.manager import TripManager

        hass = MagicMock()
        vehicle_id = "test_vehicle"
        entry = _make_entry("e1", vehicle_id)

        mock_mgr = MagicMock(spec=TripManager)
        mock_mgr._state = MagicMock()
        mock_mgr._state.recurring_trips = []
        mock_mgr._state.punctual_trips = []
        mock_mgr._persistence = MagicMock()
        mock_mgr._persistence.async_setup = AsyncMock()

        entry.runtime_data.trip_manager = mock_mgr

        hass.config_entries.async_entries.return_value = [entry]

        result = await _get_manager(hass, vehicle_id)

        assert result is mock_mgr
        assert result._state.recurring_trips == []
        assert result._state.punctual_trips == []

    @pytest.mark.asyncio
    async def test_creates_manager_when_none(self):
        """Kill mutations: creates new TripManager → None (or skips creation)."""

        hass = MagicMock()
        vehicle_id = "test_vehicle"
        entry = _make_entry("e1", vehicle_id)
        entry.runtime_data.trip_manager = None

        hass.config_entries.async_entries.return_value = [entry]

        # Need to patch TripManager constructor
        with patch(
            "custom_components.ev_trip_planner.services._utils.TripManager"
        ) as MockTripManager:
            mock_mgr = MagicMock()
            mock_mgr._state = MagicMock()
            mock_mgr._state.recurring_trips = []
            mock_mgr._state.punctual_trips = []
            mock_mgr._persistence = MagicMock()
            mock_mgr._persistence.async_setup = AsyncMock()
            MockTripManager.return_value = mock_mgr

            result = await _get_manager(hass, vehicle_id)

            MockTripManager.assert_called_once_with(hass, vehicle_id)
            mock_mgr._persistence.async_setup.assert_called_once()
            assert result is mock_mgr

    @pytest.mark.asyncio
    async def test_raises_valueerror_for_unknown_vehicle(self):
        """Kill mutations: raises ValueError → no exception or wrong exception."""
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = []

        with pytest.raises(ValueError) as exc_info:
            await _get_manager(hass, "unknown_vehicle")

        assert "unknown_vehicle" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_valueerror_for_entry_without_data(self):
        """Kill mutations: entry with None data → doesn't raise or wrong message."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "e1"
        entry.data = None

        hass.config_entries.async_entries.return_value = [entry]

        with pytest.raises(ValueError) as exc_info:
            await _get_manager(hass, "any_vehicle")

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_returns_manager_from_runtime_data(self):
        """Kill mutations: runtime_data.trip_manager → None (skips returning manager)."""
        from custom_components.ev_trip_planner.trip.manager import TripManager

        hass = MagicMock()
        vehicle_id = "test_vehicle"
        mock_mgr = MagicMock(spec=TripManager)
        mock_mgr._state = MagicMock()
        mock_mgr._state.recurring_trips = [{"id": "r1"}]
        mock_mgr._state.punctual_trips = [{"id": "p1"}]

        entry = _make_entry("e1", vehicle_id)
        entry.runtime_data.trip_manager = mock_mgr

        hass.config_entries.async_entries.return_value = [entry]

        result = await _get_manager(hass, vehicle_id)

        assert result is mock_mgr
        assert len(result._state.recurring_trips) == 1
        assert len(result._state.punctual_trips) == 1


class TestFindEntryByVehicleBehavior:
    """Targets mutation survivors in _find_entry_by_vehicle."""

    def test_returns_correct_entry_by_vehicle_name(self):
        """Kill mutations: entry lookup → wrong entry or None."""
        hass = MagicMock()
        entry1 = _make_entry("e1", "My Tesla", {"vehicle_name": "My Tesla"})
        entry2 = _make_entry("e2", "Other Car", {"vehicle_name": "Other Car"})
        hass.config_entries.async_entries.return_value = [entry1, entry2]

        with patch(
            "custom_components.ev_trip_planner.services._utils.normalize_vehicle_id",
            side_effect=lambda x: x.lower().replace(" ", "_"),
        ):
            result = _find_entry_by_vehicle(hass, "my_tesla")

        assert result is entry1

    def test_case_insensitive_lookup(self):
        """Kill mutations: vehicle_id.lower() → vehicle_id.upper() or no normalization."""
        hass = MagicMock()
        entry = _make_entry("e1", "MY_VEHICLE", {"vehicle_name": "MY_VEHICLE"})
        hass.config_entries.async_entries.return_value = [entry]

        result = _find_entry_by_vehicle(hass, "my_vehicle")

        assert result is entry

    def test_returns_none_when_not_found(self):
        """Kill mutations: returns entry instead of None."""
        hass = MagicMock()
        entry = _make_entry("e1", "vehicle_a", {"vehicle_name": "vehicle_a"})
        hass.config_entries.async_entries.return_value = [entry]

        result = _find_entry_by_vehicle(hass, "vehicle_b")

        assert result is None


class TestGetCoordinatorBehavior:
    """Targets mutation survivors in _get_coordinator."""

    def test_returns_none_when_no_entry(self):
        """Kill mutations: returns coordinator instead of None."""
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = []

        result = _get_coordinator(hass, "unknown")

        assert result is None

    def test_returns_coordinator_from_entry(self):
        """Kill mutations: entry.runtime_data.coordinator → None."""
        from custom_components.ev_trip_planner.coordinator import (
            TripPlannerCoordinator,
        )

        hass = MagicMock()
        coord = MagicMock(spec=TripPlannerCoordinator)
        entry = _make_entry("e1", "vehicle1")
        entry.runtime_data.coordinator = coord

        hass.config_entries.async_entries.return_value = [entry]

        result = _get_coordinator(hass, "vehicle1")

        assert result is coord


class TestEnsureSetupNoop:
    """Targets mutation survivors in _ensure_setup."""

    @pytest.mark.asyncio
    async def test_is_noop(self):
        """Kill mutations: pass → raise or do something."""
        mgr = MagicMock()

        await _ensure_setup(mgr)

        # No calls should be made — it's a pass statement
        mgr.assert_not_called()

"""Tests for diagnostics module."""

import pytest
from unittest.mock import MagicMock

from custom_components.ev_trip_planner.diagnostics import async_get_config_entry_diagnostics


class TestDiagnostics:
    """Tests for async_get_config_entry_diagnostics."""

    @pytest.mark.asyncio
    async def test_diagnostics_returns_dict(self):
        """Test that diagnostics returns a dictionary."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        entry.data = {"vehicle_name": "test_vehicle"}

        # Mock runtime data
        coordinator = MagicMock()
        coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {},
            "kwh_today": 0.0,
            "hours_today": 0.0,
            "next_trip": None,
            "emhass_power_profile": None,
            "emhass_deferrables_schedule": None,
            "emhass_status": None,
        }
        entry.runtime_data = MagicMock()
        entry.runtime_data.coordinator = coordinator
        entry.runtime_data.trip_manager = MagicMock()

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_diagnostics_with_no_coordinator_data(self):
        """Test diagnostics when coordinator data is None."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_entry_456"
        entry.data = {"vehicle_name": "another_vehicle"}

        # Mock runtime data with no coordinator
        entry.runtime_data = MagicMock()
        entry.runtime_data.coordinator = None
        entry.runtime_data.trip_manager = None

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert isinstance(result, dict)
        # Should handle None data gracefully
        assert "coordinator" in result
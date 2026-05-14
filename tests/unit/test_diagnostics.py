"""Tests for diagnostics module."""

from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.diagnostics import (
    REDACT_KEYS,
    async_get_config_entry_diagnostics,
)


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

    # --- Mutation killing tests ---

    @pytest.mark.asyncio
    async def test_diagnostics_extracts_entry_data(self):
        """Test that entry_id, version, minor_version are extracted — kills mutmut on entry fields."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "entry_abc"
        entry.version = 2
        entry.minor_version = 1
        entry.data = {"vehicle_name": "MyCar", "soc_sensor": "sensor.test"}

        entry.runtime_data = None

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["entry"]["entry_id"] == "entry_abc"
        assert result["entry"]["version"] == 2
        assert result["entry"]["minor_version"] == 1

    @pytest.mark.asyncio
    async def test_diagnostics_no_runtime_data(self):
        """Test diagnostics when entry has no runtime_data — kills mutmut_1,2,6,7,8."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "no_runtime"
        entry.version = 1
        entry.minor_version = 0
        entry.data = {}

        # Explicitly no runtime_data
        del entry.runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert isinstance(result, dict)
        assert "entry" in result
        # coordinator should have None data
        assert result["coordinator"]["data_keys"] == []
        assert result["coordinator"]["last_update_success"] is None

    @pytest.mark.asyncio
    async def test_diagnostics_coordinator_data_keys(self):
        """Test coordinator data keys are extracted — kills mutmut_9,10,14,15,16."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "coord_test"
        entry.version = 1
        entry.minor_version = 0
        entry.data = {}

        coordinator = MagicMock()
        coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {},
            "kwh_today": 5.0,
        }
        coordinator.last_update_success = True

        trip_manager = MagicMock()
        trip_manager.vehicle_id = "vehicle_1"
        trip_manager._recurring_trips = {"t1": {}}
        trip_manager._punctual_trips = {"t2": {}, "t3": {}}

        runtime = MagicMock()
        runtime.coordinator = coordinator
        runtime.trip_manager = trip_manager
        runtime.emhass_adapter = None
        entry.runtime_data = runtime

        result = await async_get_config_entry_diagnostics(hass, entry)

        # Verify coordinator data was extracted using correct attr name
        assert set(result["coordinator"]["data_keys"]) == {
            "recurring_trips",
            "punctual_trips",
            "kwh_today",
        }
        assert result["coordinator"]["last_update_success"] is True

    @pytest.mark.asyncio
    async def test_diagnostics_trip_manager_data(self):
        """Test trip_manager data is extracted — kills mutmut_17,18,22,23,24."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "tm_test"
        entry.version = 1
        entry.minor_version = 0
        entry.data = {}

        coordinator = MagicMock()
        coordinator.data = {}
        coordinator.last_update_success = False

        trip_manager = MagicMock()
        trip_manager._state = MagicMock()
        trip_manager._state.vehicle_id = "my_nissan"
        trip_manager._state.recurring_trips = {"r1": {}, "r2": {}}
        trip_manager._state.punctual_trips = {"p1": {}}

        runtime = MagicMock()
        runtime.coordinator = coordinator
        runtime.trip_manager = trip_manager
        runtime.emhass_adapter = None
        entry.runtime_data = runtime

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["trip_manager"]["vehicle_id"] == "my_nissan"
        assert result["trip_manager"]["recurring_trips_count"] == 2
        assert result["trip_manager"]["punctual_trips_count"] == 1

    @pytest.mark.asyncio
    async def test_diagnostics_with_emhass_adapter(self):
        """Test EMHASS data included when adapter exists — kills mutmut on emhass branch."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "emhass_test"
        entry.version = 1
        entry.minor_version = 0
        entry.data = {}

        coordinator = MagicMock()
        coordinator.data = {}
        coordinator.last_update_success = True

        trip_manager = MagicMock()
        trip_manager.vehicle_id = "v1"
        trip_manager._recurring_trips = {}
        trip_manager._punctual_trips = {}

        emhass = MagicMock()
        emhass.vehicle_id = "emhass_v1"
        emhass._index_map = {"idx1": 0}
        emhass.get_available_indices.return_value = [0, 1, 2]

        runtime = MagicMock()
        runtime.coordinator = coordinator
        runtime.trip_manager = trip_manager
        runtime.emhass_adapter = emhass
        entry.runtime_data = runtime

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert "emhass" in result
        assert result["emhass"]["vehicle_id"] == "emhass_v1"
        assert result["emhass"]["index_map"] == {"idx1": 0}
        assert result["emhass"]["available_indices"] == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_diagnostics_no_emhass_adapter(self):
        """Test no EMHASS section when adapter is None."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "no_emhass"
        entry.version = 1
        entry.minor_version = 0
        entry.data = {}

        coordinator = MagicMock()
        coordinator.data = {}
        coordinator.last_update_success = True

        trip_manager = MagicMock()
        trip_manager.vehicle_id = "v1"
        trip_manager._recurring_trips = {}
        trip_manager._punctual_trips = {}

        runtime = MagicMock()
        runtime.coordinator = coordinator
        runtime.trip_manager = trip_manager
        runtime.emhass_adapter = None
        entry.runtime_data = runtime

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert "emhass" not in result

    @pytest.mark.asyncio
    async def test_diagnostics_redacts_sensitive_keys(self):
        """Test that REDACT_KEYS are redacted from entry.data."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "redact_test"
        entry.version = 1
        entry.minor_version = 0
        entry.data = {
            "vehicle_name": "secret_car",
            "soc_sensor": "secret_sensor",
            "range_sensor": "secret_range",
            "other_key": "not_secret",
        }
        entry.runtime_data = None

        result = await async_get_config_entry_diagnostics(hass, entry)

        entry_data = result["entry"]["data"]
        # Redacted keys should be masked
        assert entry_data["vehicle_name"] != "secret_car"
        assert entry_data["soc_sensor"] != "secret_sensor"
        assert entry_data["range_sensor"] != "secret_range"
        # Non-redacted key should be intact
        assert entry_data["other_key"] == "not_secret"

    @pytest.mark.asyncio
    async def test_diagnostics_coordinator_none_data(self):
        """Test coordinator with None data returns empty data_keys."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "coord_none"
        entry.version = 1
        entry.minor_version = 0
        entry.data = {}

        coordinator = MagicMock()
        coordinator.data = None
        coordinator.last_update_success = False

        runtime = MagicMock()
        runtime.coordinator = coordinator
        runtime.trip_manager = MagicMock()
        runtime.emhass_adapter = None
        entry.runtime_data = runtime

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["coordinator"]["data_keys"] == []
        assert result["coordinator"]["last_update_success"] is False


def test_redact_keys_contains_expected_values():
    """Test REDACT_KEYS has expected sensitive key names."""
    assert "vehicle_name" in REDACT_KEYS
    assert "soc_sensor" in REDACT_KEYS
    assert "range_sensor" in REDACT_KEYS
    assert len(REDACT_KEYS) == 3

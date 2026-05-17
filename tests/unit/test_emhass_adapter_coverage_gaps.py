"""Tests for uncovered emhass/adapter.py paths.

Lines 92, 97, 102: ValueError raises in async_validate_config
Lines 685, 688: _get_current_soc returns None paths
Lines 1065, 1077: deficit results loop break/continue
Lines 1118-1122: SOC unavailable error path in publish_deferrable_load
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter


def _valid_entry():
    """Return a ConfigEntry-like mock with all required fields."""
    entry = MagicMock()
    entry.entry_id = "entry_1"
    entry.data = {
        "vehicle_name": "Test Vehicle",
        "battery_capacity_kwh": 60.0,
        "charging_power_kw": 7.0,
        "safety_margin_percent": 10.0,
    }
    entry.options = {}
    return entry


def _make_hass_mock():
    """Mock HomeAssistant with default state returns."""
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = _valid_entry()
    hass.states.get.return_value = MagicMock(state="50.0")
    return hass


class TestAsyncValidateConfig:
    """Test async_validate_config error branches (lines 92, 97, 102)."""

    @pytest.mark.asyncio
    async def test_missing_battery_capacity_kwh_raises(self):
        """Line 91-95: Missing battery_capacity_kwh raises ValueError."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_vehicle"
        entry.data = {}  # No required fields
        entry.options = {}
        hass.config_entries.async_get_entry.return_value = entry

        with pytest.raises(ValueError) as exc_info:
            EMHASSAdapter(hass, entry)
        assert "battery_capacity_kwh" in str(exc_info.value)
        assert "test_vehicle" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_charging_power_kw_raises(self):
        """Line 96-100: Missing charging_power_kw raises ValueError."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_vehicle"
        entry.data = {"battery_capacity_kwh": 60.0}  # Missing charging_power_kw
        entry.options = {}
        hass.config_entries.async_get_entry.return_value = entry

        with pytest.raises(ValueError) as exc_info:
            EMHASSAdapter(hass, entry)
        assert "charging_power_kw" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_safety_margin_percent_raises(self):
        """Line 101-105: Missing safety_margin_percent raises ValueError."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_vehicle"
        entry.data = {
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.0,
            # Missing safety_margin_percent
        }
        entry.options = {}
        hass.config_entries.async_get_entry.return_value = entry

        with pytest.raises(ValueError) as exc_info:
            EMHASSAdapter(hass, entry)
        assert "safety_margin_percent" in str(exc_info.value)


class TestGetCurrentSoc:
    """Test _get_current_soc branches (lines 685, 688)."""

    @pytest.mark.asyncio
    async def test_get_current_soc_no_sensor_configured(self):
        """Line 684-685: No soc_sensor in entry → returns None."""
        hass = _make_hass_mock()
        entry = _valid_entry()
        entry.data["soc_sensor"] = None  # No sensor

        adapter = EMHASSAdapter(hass, entry)
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_sensor_not_in_hass(self):
        """Lines 686-688: Sensor entity not found in hass.states → returns None."""
        hass = _make_hass_mock()
        hass.states.get.return_value = None  # Sensor not found
        entry = _valid_entry()
        entry.data["soc_sensor"] = "sensor.missing"

        adapter = EMHASSAdapter(hass, entry)
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_invalid_state_value(self):
        """Lines 689-692: State value can't be converted to float → returns None."""
        hass = _make_hass_mock()
        mock_state = MagicMock()
        mock_state.state = "not_a_number"
        hass.states.get.return_value = mock_state
        entry = _valid_entry()
        entry.data["soc_sensor"] = "sensor.invalid"

        adapter = EMHASSAdapter(hass, entry)
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_valid_value(self):
        """Valid SOC float value from sensor state."""
        hass = _make_hass_mock()
        mock_state = MagicMock()
        mock_state.state = "75.0"
        hass.states.get.return_value = mock_state
        entry = _valid_entry()
        entry.data["soc_sensor"] = "sensor.valid"

        adapter = EMHASSAdapter(hass, entry)
        result = await adapter._get_current_soc()
        assert result == 75.0


class TestPublishDeferrableLoad:
    """Test async_publish_deferrable_load SOC unavailable path (lines 1117-1122)."""

    @pytest.mark.asyncio
    async def test_publish_deferrable_load_returns_false_when_soc_unavailable(self):
        """Lines 1117-1122: SOC sensor unavailable → returns False."""
        hass = _make_hass_mock()
        entry = _valid_entry()
        entry.data["soc_sensor"] = None  # No sensor
        adapter = EMHASSAdapter(hass, entry)

        trip = {
            "id": "trip_1",
            "kwh": 10.0,
            "datetime": "2026-05-20T08:00:00+00:00",
        }

        result = await adapter.async_publish_deferrable_load(trip)
        assert result is False


# --- Coverage for remaining lines in adapter.py ---


class TestGetCachedOptimizationResultsDebug:
    """Coverage for get_cached_optimization_results debug logging (line 245)."""

    def test_get_cached_returns_per_trip_and_power_profile(self):
        """Line 245: get_cached_optimization_results logs debug BUG-DEBUG for each trip."""
        from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        adapter.hass = MagicMock()
        adapter.vehicle_id = "test_vehicle"
        adapter.entry_id = "test_entry"
        adapter._entry = MagicMock()
        adapter._index_manager = MagicMock()
        adapter._load_publisher = MagicMock()
        adapter._error_handler = MagicMock()
        adapter._published_trips = set()
        adapter._cached_per_trip_params = {
            "trip1": {"def_total_hours": 2.0, "def_start_timestep": 0, "def_end_timestep": 10},
            "trip2": {"def_total_hours": 3.0, "def_start_timestep": 5, "def_end_timestep": 15},
        }
        adapter._cached_power_profile = [0.0, 1.5, 2.0]
        adapter._cached_deferrables_schedule = []
        adapter._cached_emhass_status = "ready"

        result = adapter.get_cached_optimization_results()

        assert result["emhass_power_profile"] == [0.0, 1.5, 2.0]
        assert result["emhass_status"] == "ready"
        assert len(result["per_trip_emhass_params"]) == 2


class TestPopulatePerTripCacheSOCUnavailable:
    """Coverage for SOC unavailable fallback (lines 415-422)."""

    @pytest.mark.asyncio
    async def test_soc_unavailable_uses_default_50_percent(self):
        """Lines 414-422: When SOC sensor unavailable, use default 50.0 for computation.

        Verifies the code path where _get_current_soc returns None
        (sensor unavailable) and the adapter falls back to 50.0.
        """
        from datetime import datetime, timezone
        from unittest.mock import patch, AsyncMock

        from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_vehicle"
        entry.data = {
            "battery_capacity_kwh": 62.0,
            "charging_power_kw": 7.4,
            "safety_margin_percent": 10.0,
            "soc_sensor": "sensor.bat_soc",
        }
        entry.options = {}

        adapter = EMHASSAdapter(hass, entry)

        # Patch _get_current_soc to return None (sensor unavailable)
        # and dt_util.now to return a fixed datetime
        fixed_dt = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
        with (
            patch.object(adapter, "_get_current_soc", new_callable=AsyncMock, return_value=None),
            patch("homeassistant.util.dt.now", return_value=fixed_dt),
        ):
            trips = [
                {
                    "id": "trip_1",
                    "km": 50.0,
                    "datetime": "2026-05-17T18:00:00+00:00",
                    "tipo": "punctual",
                }
            ]
            result = await adapter._precompute_and_process_trips(trips, 62.0)

            # When SOC unavailable, adapter falls back to 50.0
            assert result == 50.0


class TestApplyDeficitResultsEdgeCases:
    """Coverage for deficit propagation edge cases (line 1069)."""

    def test_apply_deficit_results_continues_when_trip_id_none(self):
        """Line 1069: continue when trip_id is None."""
        from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter
        from unittest.mock import MagicMock

        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        adapter.hass = MagicMock()
        adapter._cached_per_trip_params = {}

        param1 = {"activo": True, "def_total_hours": 2.0, "def_start_timestep": 0, "emhass_index": 0, "power_watts": 7400.0, "charging_window": []}
        active = [param1]

        results = [{"adjusted_def_total_hours": 3.0}]

        # trip_id is None — should continue without crashing (line 1069)
        adapter._find_trip_id_for_params = MagicMock(return_value=None)
        adapter._apply_deficit_results(results, active)


class TestGetCachedOptimizationResultsEmpty:
    """Coverage for get_cached_optimization_results with empty cache."""

    def test_get_cached_with_empty_cache(self):
        """Verify empty cache returns empty structures."""
        from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        adapter.hass = MagicMock()
        adapter._cached_per_trip_params = {}
        adapter._cached_power_profile = None
        adapter._cached_deferrables_schedule = None
        adapter._cached_emhass_status = None

        result = adapter.get_cached_optimization_results()
        assert result["emhass_power_profile"] is None
        assert result["emhass_deferrables_schedule"] is None


# --- Additional coverage for adapter.py lines 685, 688 ---


class TestGetCurrentSocSecondSensorCheck:
    """Coverage for second SOC sensor check paths (lines 685, 688)."""

    @pytest.mark.asyncio
    async def test_get_current_soc_second_sensor_returns_none(self):
        """Lines 685, 688: Second SOC sensor check path when first parse failed.
        
        This exercises the path where:
        - First sensor check at line 652 returns a state (not None)
        - Float parse fails at line 665 (ValueError)
        - Lines 679-682 re-read soc_sensor from entry
        - Second sensor check at line 686 returns None state
        - Line 688 returns None
        """
        from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter
        from unittest.mock import MagicMock

        hass = MagicMock()
        entry = MagicMock()
        entry.data = {
            "battery_capacity_kwh": 62.0,
            "charging_power_kw": 7.4,
            "safety_margin_percent": 10.0,
            "soc_sensor": "sensor.first_soc",
        }
        entry.options = {"soc_sensor": "sensor.second_soc"}

        # First states.get returns a state that can't be parsed as float
        # Second states.get returns None (second sensor unavailable)
        hass.states.get = MagicMock(side_effect=[
            MagicMock(state="not_a_number"),  # line 652: parse fails → except path
            None,                               # line 686: second sensor returns None
        ])

        adapter = EMHASSAdapter(hass, entry)
        result = await adapter._get_current_soc()

        # Second sensor check returned None → should return None
        assert result is None

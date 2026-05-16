"""Tests for uncovered adapter.py paths (lines 401-402, 415-416, 695, 736, 744, 777-778, 793, 797, 815)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass.adapter import (
    EMHASSAdapter,
    PerTripCacheParams,
)


def _make_valid_entry(**overrides):
    """Create a MagicMock ConfigEntry with all required fields."""
    entry = MagicMock()
    entry.entry_id = "test_vehicle"
    data = {
        "vehicle_name": "test_vehicle",
        "battery_capacity_kwh": 60.0,
        "kwh_per_km": 0.15,
        "charging_power_kw": 7.0,
        "safety_margin_percent": 10.0,
    }
    data.update(overrides)
    entry.data = data
    entry.options = {}
    return entry


@pytest.fixture
def mock_entry():
    """Minimal MagicMock ConfigEntry with required fields."""
    return _make_valid_entry()


@pytest.fixture
def mock_hass(tmp_path):
    """Minimal MagicMock HomeAssistant."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)
    hass.states.get.return_value = None
    hass.services.has_service.return_value = False
    return hass


class TestProcessTripsWithWindowsException:
    """Test exception handler in _process_trips_with_windows (lines 401-402)."""

    @pytest.mark.asyncio
    async def test_populate_cache_exception_sets_error_status(
        self, mock_hass, mock_entry
    ):
        """Lines 401-402: Exception during _populate_per_trip_cache_entry sets _cached_emhass_status to error."""
        window_by_trip_id: dict[str, dict[str, Any]] = {
            "trip_001": {"inicio_ventana": datetime.now(timezone.utc), "fin_ventana": datetime.now(timezone.utc) + timedelta(hours=4)},
        }
        trips = [{"id": "trip_001"}]
        with patch.object(
            EMHASSAdapter,
            "_populate_per_trip_cache_entry",
            side_effect=RuntimeError("test error"),
        ):
            adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
            adapter._cached_emhass_status = "success"
            await adapter._process_trips_with_windows(
                trips=trips,
                battery_capacity_kwh=60.0,
                soc_current=50.0,
                window_by_trip_id=window_by_trip_id,
            )
            assert adapter._cached_emhass_status == "error"


class TestGetHorizonHoursException:
    """Test exception handler in _get_horizon_hours (lines 415-416)."""

    def test_exception_returns_default(self, mock_hass, mock_entry):
        """Lines 415-416: Exception in _get_horizon_hours returns default 168."""
        mock_entry.data = {
            "vehicle_name": "test_vehicle",
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.0,
            "safety_margin_percent": 10.0,
            "planning_horizon_days": "not_a_number",
        }
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = adapter._get_horizon_hours()
        assert result == 168

    def test_exception_in_int_conversion_returns_default(self, mock_hass, mock_entry):
        """Lines 415-416: Exception in int() conversion returns default 168."""
        mock_entry.data = {
            "vehicle_name": "test_vehicle",
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.0,
            "safety_margin_percent": 10.0,
            "planning_horizon_days": "abc",
        }
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = adapter._get_horizon_hours()
        assert result == 168


class TestPopulatePerTripCacheEntryMissingPaths:
    """Test uncovered paths in _populate_per_trip_cache_entry."""

    @pytest.mark.asyncio
    async def test_empty_cached_params_returns_early(self):
        """Line 735: Empty _cached_per_trip_params returns early."""
        hass = MagicMock()
        entry = _make_valid_entry()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        adapter._cached_per_trip_params = {}
        adapter._apply_deficit_propagation()  # Should not raise

    def test_single_active_trip_returns_early(self):
        """Line 739: Less than 2 active trips returns early."""
        hass = MagicMock()
        entry = _make_valid_entry()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        adapter._cached_per_trip_params = {
            "trip_001": {"activo": True, "def_start_timestep": 0, "emhass_index": 0},
        }
        adapter._apply_deficit_propagation()  # Should not raise


class TestBuildDeficitWindowsEmptyChargingWindow:
    """Test _build_deficit_windows with empty charging windows (lines 777-778)."""

    def test_empty_charging_window_produces_zero_hours(self):
        """Lines 777-778: Empty charging_window should produce zero horas_carga."""
        hass = MagicMock()
        entry = _make_valid_entry()
        adapter = EMHASSAdapter(hass=hass, entry=entry)

        active = [
            {
                "id": "trip_001",
                "activo": True,
                "def_start_timestep": 0,
                "emhass_index": 0,
                "charging_window": [],  # Empty
                "energia_necesaria_kwh": 10.0,
            },
            {
                "id": "trip_002",
                "activo": True,
                "def_start_timestep": 2,
                "emhass_index": 1,
                "charging_window": [],  # Empty
                "energia_necesaria_kwh": 5.0,
            },
        ]
        windows, total_hours_list = adapter._build_deficit_windows(active)
        # Empty charging windows should produce windows with 0 horas_carga
        assert len(windows) == 2
        assert all(w.get("horas_carga_necesarias", 0) == 0 for w in windows)
        assert total_hours_list == [0.0, 0.0]


class TestApplyDeficitPropagationEarlyReturns:
    """Test early returns in _apply_deficit_propagation (lines 744)."""

    def test_windows_empty_returns_early(self):
        """Line 744: Empty windows list returns early."""
        hass = MagicMock()
        entry = _make_valid_entry()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        # Two active trips but empty charging windows -> _build_deficit_windows returns empty
        adapter._cached_per_trip_params = {
            "trip_001": {
                "activo": True,
                "def_start_timestep": 0,
                "emhass_index": 0,
                "charging_window": [],  # Empty -> windows will be empty
            },
            "trip_002": {
                "activo": True,
                "def_start_timestep": 2,
                "emhass_index": 1,
                "charging_window": [],  # Empty -> windows will be empty
            },
        }
        # Should return early without error when windows are empty
        adapter._apply_deficit_propagation()


class TestApplyDeficitResults:
    """Test _apply_deficit_results (lines 793, 797)."""

    def test_apply_deficit_results_empty(self):
        """Lines 793, 797: Empty results list should not raise."""
        hass = MagicMock()
        entry = _make_valid_entry()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        adapter._cached_per_trip_params = {}
        adapter._apply_deficit_results([], [])

    def test_apply_deficit_results_with_data(self):
        """Lines 793, 797: Results with data should update cached params."""
        hass = MagicMock()
        entry = _make_valid_entry()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        # _find_trip_id_for_params uses identity (p is params), so active[0] must BE trip_001
        trip_001 = {"def_start_timestep": 0, "emhass_index": 0, "power_watts": 3600}
        adapter._cached_per_trip_params = {
            "trip_001": trip_001,
        }
        results = [
            {"adjusted_def_total_hours": 5.0},
        ]
        # active[0] must be the SAME OBJECT as trip_001 for identity check to pass
        active = [trip_001]
        adapter._apply_deficit_results(results, active)
        assert trip_001.get("adjusted_def_total_hours") == 5.0


class TestFindTripIdForParams:
    """Test _find_trip_id_for_params (line 815)."""

    def test_find_trip_id_returns_none_for_unknown(self):
        """Line 815: No matching trip returns None."""
        hass = MagicMock()
        entry = _make_valid_entry()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        trip_001 = {"id": "trip_001"}
        adapter._cached_per_trip_params = {
            "trip_001": trip_001,
        }
        # Different dict - should return None
        other_params = {"def_start_timestep": 0, "emhass_index": 0}
        result = adapter._find_trip_id_for_params(other_params)
        assert result is None

    def test_find_trip_id_returns_matching(self):
        """Line 812-814: Matching params dict should return trip_id."""
        hass = MagicMock()
        entry = _make_valid_entry()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        trip_001 = {"id": "trip_001"}
        adapter._cached_per_trip_params = {
            "trip_001": trip_001,
        }
        # Same dict object - should return trip_001
        result = adapter._find_trip_id_for_params(trip_001)
        assert result == "trip_001"


class TestLine744EmptyWindows:
    """Test line 744: early return when _build_deficit_windows returns empty."""

    def test_line_744_empty_windows_returns_early(self):
        """Line 744: When _build_deficit_windows returns empty list, return early."""
        hass = MagicMock()
        entry = _make_valid_entry()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        adapter._cached_per_trip_params = {
            "trip_001": {"activo": True, "def_start_timestep": 0, "emhass_index": 0},
            "trip_002": {"activo": True, "def_start_timestep": 2, "emhass_index": 1},
        }
        # Mock _build_deficit_windows to return empty list
        with patch.object(
            adapter, "_build_deficit_windows", return_value=([], [])
        ) as mock_build:
            # Should return early at line 744 without calling calculate_hours_deficit_propagation
            adapter._apply_deficit_propagation()
            mock_build.assert_called_once()
            # Should not reach the deficit calculation


class TestLines650652KmFallbackAndLine695:
    """Test lines 650-652 (km-based energy fallback) and line 695 (no fin_ventana fallback)."""

    @pytest.mark.asyncio
    async def test_km_fallback_and_no_fin_ventana(self):
        """Lines 650-652, 695: trip with 'km' but no 'kwh', and charging_windows without 'fin_ventana'."""
        from homeassistant.util import dt as dt_util

        hass = MagicMock()
        entry = _make_valid_entry()
        # Entry must have t_base so the SOC capping block is entered (line 635)
        entry.options = {"t_base": 24.0}

        # Trip with 'km' but WITHOUT 'kwh' — triggers lines 650-652
        trip = {
            "id": "km_trip",
            "km": 100.0,  # 100 km * 0.15 kWh/km = 15 kWh needed
        }

        adapter = EMHASSAdapter(hass=hass, entry=entry)

        now = dt_util.now()
        deadline = now + timedelta(hours=8)

        # Mock _calculate_charging_windows to return windows WITHOUT 'fin_ventana'
        # This triggers line 695 (fallback when no fin_ventana)
        mock_windows = [
            {"inicio_ventana": now + timedelta(hours=2), "ventana_horas": 6}
            # Note: NO 'fin_ventana' key
        ]

        with patch.object(
            adapter._load_publisher,
            "_calculate_charging_windows",
            return_value=mock_windows,
        ):
            # Also mock _calculate_deadline_from_trip to return our deadline
            with patch.object(
                adapter, "_calculate_deadline_from_trip", return_value=deadline
            ):
                params = PerTripCacheParams(
                    trip=trip,
                    trip_id="km_trip",
                    charging_power_kw=7.0,
                    battery_capacity_kwh=60.0,
                    safety_margin_percent=10.0,
                    soc_current=50.0,  # < 100 so SOC capping block is entered
                )
                await adapter._populate_per_trip_cache_entry(params)

                # Verify cache entry was created
                assert "km_trip" in adapter._cached_per_trip_params
                cache_entry = adapter._cached_per_trip_params["km_trip"]

                # Verify the km-based energy calculation was used (lines 650-652)
                # 100 km * 0.15 kWh/km = 15 kWh
                # The cache should have non-zero kwh_needed
                assert cache_entry.get("kwh_needed", 0) > 0

                # Verify def_end_timestep was calculated (line 695 fallback)
                # hours_available ~8 hours, int() may truncate to 7 or 8
                def_end = cache_entry.get("def_end_timestep")
                assert def_end in (7, 8)

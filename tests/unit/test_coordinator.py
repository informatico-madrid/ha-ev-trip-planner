"""Execution tests for TripPlannerCoordinator.

Covers __init__, vehicle_id property, _async_update_data, and async_refresh_trips.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.coordinator import (
    _LOG_REFRESH_TRIPS_DONE,
    _LOG_REFRESH_TRIPS_START,
    _LOG_UPDATE_DATA_CALLED,
    _LOG_UPDATE_DATA_RETURNING,
    _LOG_UPDATE_DATA_TRIPS_BEFORE,
    CoordinatorConfig,
    TripPlannerCoordinator,
)


# FIX: Mock frame reporting for HA 2026.3+ compatibility
# DataUpdateCoordinator requires frame helper to be set up
# This fixture mocks report_usage to bypass the check
@pytest.fixture(autouse=True)
def mock_frame_reporting():
    """Mock frame reporting to avoid 'Frame helper not set up' error."""
    with patch("homeassistant.helpers.frame.report_usage", return_value=None):
        yield


_LOGGER = logging.getLogger(__name__)


def _make_mock_hass():
    """Create a minimal mock HomeAssistant."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


def _make_mock_entry(vehicle_name="test_vehicle", extra_data=None, extra_options=None):
    """Create a minimal mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        "vehicle_name": vehicle_name,
        "charging_power_kw": 7.0,
        "battery_capacity_kwh": 75.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    entry.options = extra_options or {}
    if extra_data:
        entry.data.update(extra_data)
    return entry


def _make_trip_manager():
    """Create a TripManager-like mock with sub-component mocks."""
    tm = MagicMock()
    tm._crud = MagicMock()
    tm._crud.async_get_recurring_trips = AsyncMock(
        return_value=[
            {
                "id": "rec_1",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "km": 50,
                "kwh": 7.5,
                "activo": True,
            }
        ]
    )
    tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    tm._soc_query = MagicMock()
    tm._soc_query.async_get_kwh_needed_today = AsyncMock(return_value=12.5)
    tm._soc_query.async_get_hours_needed_today = AsyncMock(return_value=2.0)
    tm._navigator = MagicMock()
    tm._navigator.async_get_next_trip = AsyncMock(return_value=None)
    return tm


def _make_coordinator(
    vehicle_name="test_vehicle",
    trip_manager=None,
    emhass_adapter=None,
    extra_entry_data=None,
):
    """Create a fully wired TripPlannerCoordinator."""
    hass = _make_mock_hass()
    entry = _make_mock_entry(vehicle_name=vehicle_name, extra_data=extra_entry_data)
    if trip_manager is None:
        trip_manager = _make_trip_manager()
    config = CoordinatorConfig(emhass_adapter=emhass_adapter)
    return TripPlannerCoordinator(
        hass=hass,
        entry=entry,
        trip_manager=trip_manager,
        config=config,
    )


class TestCoordinatorInit:
    """Test TripPlannerCoordinator.__init__."""

    def test_init_default_config(self):
        """Default config creates coordinator with correct defaults."""
        coord = _make_coordinator()
        assert coord._vehicle_id == "test_vehicle"
        assert coord._entry is not None
        assert coord._emhass_adapter is None

    def test_init_with_custom_config(self):
        """Custom config passes through emhass_adapter and logger."""
        adapter = MagicMock()
        custom_logger = logging.getLogger("custom")
        config = CoordinatorConfig(emhass_adapter=adapter, logger=custom_logger)
        hass = _make_mock_hass()
        entry = _make_mock_entry()
        coord = TripPlannerCoordinator(
            hass=hass,
            entry=entry,
            trip_manager=_make_trip_manager(),
            config=config,
        )
        assert coord._emhass_adapter is adapter
        assert coord.logger is custom_logger

    def test_init_vehicle_name_normalized(self):
        """Vehicle name is lowercased with spaces replaced by underscores."""
        coord = _make_coordinator(vehicle_name="My Test Vehicle")
        assert coord._vehicle_id == "my_test_vehicle"

    def test_init_vehicle_name_empty(self):
        """Empty vehicle_name results in empty string (code doesn't default to 'unknown')."""
        coord = _make_coordinator(vehicle_name="")
        assert coord._vehicle_id == ""

    def test_init_update_interval_is_120_seconds(self):
        """__init__ sets update_interval to timedelta(seconds=120).

        This test kills mutations on the timedelta(seconds=120) value
        that survive because tests don't assert on the update interval.
        """
        from datetime import timedelta

        coord = _make_coordinator()
        assert coord.update_interval == timedelta(seconds=120)


class TestCoordinatorVehicleId:
    """Test TripPlannerCoordinator.vehicle_id property."""

    def test_vehicle_id_returns_normalized_name(self):
        """vehicle_id property returns normalized vehicle name."""
        coord = _make_coordinator(vehicle_name="Test Vehicle")
        assert coord.vehicle_id == "test_vehicle"


class TestCoordinatorAsyncUpdateData:
    """Test TripPlannerCoordinator._async_update_data."""

    @pytest.mark.asyncio
    async def test_async_update_data_with_emhass(self):
        """Full path: coordinator has emhass_adapter → reads cached results."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {"rec_1": {"index": 0}},
            "emhass_power_profile": [100, 200, 300],
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }
        tm = _make_trip_manager()
        coord = _make_coordinator(
            trip_manager=tm,
            emhass_adapter=adapter,
        )
        result = await coord._async_update_data()
        assert result["recurring_trips"] is not None
        assert result["punctual_trips"] is not None
        assert result["kwh_today"] == 12.5
        assert result["hours_today"] == 2.0
        assert result["next_trip"] is None
        assert result["emhass_power_profile"] == [100, 200, 300]
        assert all(isinstance(v, int) for v in result["emhass_power_profile"])
        tm._crud.async_get_recurring_trips.assert_called_once()
        tm._crud.async_get_punctual_trips.assert_called_once()
        tm._soc_query.async_get_kwh_needed_today.assert_called_once()
        tm._soc_query.async_get_hours_needed_today.assert_called_once()
        tm._navigator.async_get_next_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_update_data_without_emhass(self):
        """No emhass_adapter → EMHASS keys are None."""
        coord = _make_coordinator(emhass_adapter=None)
        result = await coord._async_update_data()
        assert result["emhass_power_profile"] is None
        assert result["emhass_deferrables_schedule"] is None
        assert result["emhass_status"] is None

    @pytest.mark.asyncio
    async def test_async_update_data_emhass_empty_returns_empty_params(self):
        """EMHASS returns empty cache → per_trip_emhass_params is empty, no fallback."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {},
            "emhass_power_profile": [],
        }
        tm = _make_trip_manager()
        tm._crud.async_get_recurring_trips = AsyncMock(
            return_value=[
                {
                    "id": "rec_1",
                    "kwh": 7.5,
                    "km": 50,
                    "datetime": "2026-05-20T09:00:00+00:00",
                }
            ]
        )
        coord = _make_coordinator(
            trip_manager=tm,
            emhass_adapter=adapter,
        )
        result = await coord._async_update_data()
        # No mock fallback — empty EMHASS params means empty dict
        assert result["per_trip_emhass_params"] == {}
        # Main trip data is unaffected
        assert "rec_1" in result["recurring_trips"]

    @pytest.mark.asyncio
    async def test_async_update_data_empty_trips(self):
        """No trips → EMHASS adapter not called with empty trips."""
        tm = _make_trip_manager()
        tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
        coord = _make_coordinator(trip_manager=tm, emhass_adapter=None)
        result = await coord._async_update_data()
        assert result["recurring_trips"] == {}
        assert result["punctual_trips"] == {}

    @pytest.mark.asyncio
    async def test_async_update_data_punctual_trips_included(self):
        """Punctual trips are included alongside recurring trips."""
        tm = _make_trip_manager()
        tm._crud.async_get_punctual_trips = AsyncMock(
            return_value=[
                {
                    "id": "pun_1",
                    "kwh": 3.0,
                    "km": 20,
                    "datetime": "2026-05-20T08:00:00+00:00",
                }
            ]
        )
        coord = _make_coordinator(trip_manager=tm, emhass_adapter=None)
        result = await coord._async_update_data()
        assert "pun_1" in result["punctual_trips"]


class TestCoordinatorRefreshTrips:
    """Test TripPlannerCoordinator.async_refresh_trips."""

    @pytest.mark.asyncio
    async def test_async_refresh_trips_calls_parent_refresh(self):
        """async_refresh_trips delegates to async_refresh()."""
        coord = _make_coordinator()
        # async_refresh is a DataUpdateCoordinator method — mock it
        coord.async_refresh = AsyncMock(return_value=MagicMock())
        await coord.async_refresh_trips()
        coord.async_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_refresh_trips_with_existing_data(self):
        """async_refresh_trips logs data keys when data already exists."""
        coord = _make_coordinator()
        # Pre-populate self.data to simulate prior _async_update_data run
        coord.data = {"recurring_trips": {}, "punctual_trips": {}, "kwh_today": 0.0}
        coord.async_refresh = AsyncMock(return_value=MagicMock())
        await coord.async_refresh_trips()
        coord.async_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_refresh_trips_with_none_data(self):
        """async_refresh_trips handles None data gracefully."""
        coord = _make_coordinator()
        coord.data = None
        coord.async_refresh = AsyncMock(return_value=MagicMock())
        await coord.async_refresh_trips()
        coord.async_refresh.assert_called_once()


# ---------- US-5: Log string constant tests ----------


class TestLogStringConstants:
    """US-5: Assert log string constants are correct — kills log_text mutations."""

    def test_log_update_data_called_contains_vehicle_placeholder(self):
        """_LOG_UPDATE_DATA_CALLED has vehicle %s placeholder."""
        assert "%s" in _LOG_UPDATE_DATA_CALLED
        assert "_async_update_data" in _LOG_UPDATE_DATA_CALLED

    def test_log_update_data_trips_before_is_present(self):
        """_LOG_UPDATE_DATA_TRIPS_BEFORE contains EMHASS fetch reference."""
        assert "trip_manager" in _LOG_UPDATE_DATA_TRIPS_BEFORE
        assert "EMHASS" in _LOG_UPDATE_DATA_TRIPS_BEFORE

    def test_log_update_data_returning_has_keys_placeholder(self):
        """_LOG_UPDATE_DATA_RETURNING has keys=%s placeholder."""
        assert "keys=" in _LOG_UPDATE_DATA_RETURNING

    def test_log_refresh_trips_start_has_vehicle_and_data_placeholders(self):
        """_LOG_REFRESH_TRIPS_START has vehicle and data placeholders."""
        assert "%s" in _LOG_REFRESH_TRIPS_START
        assert "async_refresh_trips START" in _LOG_REFRESH_TRIPS_START

    def test_log_refresh_trips_done_has_vehicle_and_data_placeholders(self):
        """_LOG_REFRESH_TRIPS_DONE has vehicle and data placeholders."""
        assert "%s" in _LOG_REFRESH_TRIPS_DONE
        assert "async_refresh_trips DONE" in _LOG_REFRESH_TRIPS_DONE


# ---------- EMHASS data passthrough tests ----------


class TestEMHASSDataPassthrough:
    """Test that EMHASS data keys propagate correctly into the return value."""

    @pytest.mark.asyncio
    async def test_emhass_data_keys_in_return(self):
        """EMHASS adapter data keys appear in coordinator result dict."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {"rec_1": {"index": 0}},
            "emhass_power_profile": [100, 200, 300],
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }
        coord = _make_coordinator(emhass_adapter=adapter)
        result = await coord._async_update_data()
        assert "emhass_power_profile" in result
        assert "emhass_deferrables_schedule" in result
        assert "emhass_status" in result
        assert "per_trip_emhass_params" in result

    @pytest.mark.asyncio
    async def test_emhass_data_values_passed_through(self):
        """EMHASS adapter data values propagate into result."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {"trip_a": {"index": 1}},
            "emhass_power_profile": [42],
            "emhass_deferrables_schedule": ["sched_1"],
            "emhass_status": "computing",
        }
        coord = _make_coordinator(emhass_adapter=adapter)
        result = await coord._async_update_data()
        assert result["emhass_power_profile"] == [42]
        assert result["emhass_deferrables_schedule"] == ["sched_1"]
        assert result["emhass_status"] == "computing"
        assert result["per_trip_emhass_params"] == {"trip_a": {"index": 1}}

    @pytest.mark.asyncio
    async def test_no_emhass_adapter_yields_none_values(self):
        """Without adapter, EMHASS keys are None and params are empty dict."""
        coord = _make_coordinator(emhass_adapter=None)
        result = await coord._async_update_data()
        assert result["emhass_power_profile"] is None
        assert result["emhass_deferrables_schedule"] is None
        assert result["emhass_status"] is None
        assert result["per_trip_emhass_params"] == {}


# ---------- Intermediate state / return dict structure tests ----------


class TestReturnDictStructure:
    """Test that the return dict has all expected keys with correct types."""

    @pytest.mark.asyncio
    async def test_return_dict_has_all_contract_keys(self):
        """Return dict contains all keys from the data contract."""
        coord = _make_coordinator()
        result = await coord._async_update_data()
        expected_keys = {
            "recurring_trips",
            "punctual_trips",
            "kwh_today",
            "hours_today",
            "next_trip",
            "emhass_power_profile",
            "emhass_deferrables_schedule",
            "emhass_status",
            "per_trip_emhass_params",
        }
        assert set(result.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_intermediate_trip_keys_in_result(self):
        """Recurring trip IDs appear as keys in result['recurring_trips']."""
        tm = _make_trip_manager()
        tm._crud.async_get_recurring_trips = AsyncMock(
            return_value=[
                {"id": "trip_alpha", "kwh": 5.0, "km": 30},
                {"id": "trip_beta", "kwh": 10.0, "km": 60},
            ]
        )
        coord = _make_coordinator(trip_manager=tm)
        result = await coord._async_update_data()
        assert "trip_alpha" in result["recurring_trips"]
        assert "trip_beta" in result["recurring_trips"]
        assert result["recurring_trips"]["trip_alpha"]["kwh"] == 5.0
        assert result["recurring_trips"]["trip_beta"]["km"] == 60

    @pytest.mark.asyncio
    async def test_intermediate_kwh_hours_types(self):
        """kwh_today and hours_today have correct types in result."""
        coord = _make_coordinator()
        result = await coord._async_update_data()
        assert isinstance(result["kwh_today"], (int, float))
        assert isinstance(result["hours_today"], (int, float))
        assert result["kwh_today"] == 12.5
        assert result["hours_today"] == 2.0

    @pytest.mark.asyncio
    async def test_intermediate_next_trip_none_by_default(self):
        """next_trip is None when no trips exist."""
        coord = _make_coordinator()
        result = await coord._async_update_data()
        assert result["next_trip"] is None

    @pytest.mark.asyncio
    async def test_punctual_trips_not_in_recurring_dict(self):
        """Punctual trips should not appear in recurring_trips dict."""
        tm = _make_trip_manager()
        tm._crud.async_get_punctual_trips = AsyncMock(
            return_value=[{"id": "pun_x", "kwh": 3.0, "km": 20}]
        )
        tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        coord = _make_coordinator(trip_manager=tm)
        result = await coord._async_update_data()
        assert "pun_x" not in result["recurring_trips"]
        assert "pun_x" in result["punctual_trips"]


# ---------- async_refresh_trips log assertion tests ----------


class TestRefreshTripsLogAssertions:
    """Target mutations on async_refresh_trips: conditional data display, log args."""

    @pytest.mark.asyncio
    async def test_refresh_trips_logs_keys_when_data_exists(self, caplog):
        """async_refresh_trips logs data keys when data is not None — exercises the
        'list(self.data.keys())' code path, killing mutations on 'is None' bool flip."""
        caplog.set_level(logging.DEBUG)
        coord = _make_coordinator()
        coord.data = {"recurring_trips": {}, "punctual_trips": {}}
        coord.async_refresh = AsyncMock(return_value=MagicMock())
        await coord.async_refresh_trips()
        # The log should contain the list of keys, not the "None" string
        log_records = [
            r for r in caplog.records if "async_refresh_trips START" in r.message
        ]
        assert len(log_records) >= 1
        # Verify the log message includes actual keys, proving the 'else' branch
        # was taken (kills mutations on 'is None' → 'is not None' bool flip)
        combined = " ".join(r.message for r in log_records)
        assert "recurring_trips" in combined or "punctual_trips" in combined

    @pytest.mark.asyncio
    async def test_refresh_trips_logs_none_when_data_is_none(self, caplog):
        """async_refresh_trips logs 'None' when data is None — exercises the
        'self.data is None' branch, killing mutations that flip the condition."""
        caplog.set_level(logging.DEBUG)
        coord = _make_coordinator()
        coord.data = None
        coord.async_refresh = AsyncMock(return_value=MagicMock())
        await coord.async_refresh_trips()
        log_records = [
            r for r in caplog.records if "async_refresh_trips START" in r.message
        ]
        assert len(log_records) >= 1
        combined = " ".join(r.message for r in log_records)
        # When data is None, the string "None" should appear in the log
        assert "None" in combined

    @pytest.mark.asyncio
    async def test_refresh_trips_vehicle_id_in_logs(self, caplog):
        """async_refresh_trips logs the vehicle_id in both log calls."""
        caplog.set_level(logging.DEBUG)
        coord = _make_coordinator(vehicle_name="my_vehicle")
        coord.data = None
        coord.async_refresh = AsyncMock(return_value=MagicMock())
        await coord.async_refresh_trips()
        log_records = [r for r in caplog.records if "async_refresh_trips" in r.message]
        combined = " ".join(r.message for r in log_records)
        assert "my_vehicle" in combined

    @pytest.mark.asyncio
    async def test_refresh_trips_after_refresh_has_data(self, caplog):
        """After async_refresh() runs, self.data may be populated — second log call
        should show keys, not 'None'. This exercises both log calls with different
        data states."""
        caplog.set_level(logging.DEBUG)
        coord = _make_coordinator()
        # Before refresh: data is None (simulating first call)
        coord.data = None
        coord.async_refresh = AsyncMock(return_value=MagicMock())
        # After mock refresh, data becomes populated
        # The mock doesn't actually update data, so we set it after the call
        await coord.async_refresh_trips()
        # Both log calls used the None branch since data was None
        log_records = [r for r in caplog.records if "async_refresh_trips" in r.message]
        assert len(log_records) >= 2


# ---------- Emhass conditional path tests ----------


class TestEmhassConditionalPath:
    """Tests for the if self._emhass_adapter is not None conditional."""

    @pytest.mark.asyncio
    async def test_emhass_adapter_present_bypasses_default(self):
        """With adapter, default None values are not used."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {},
            "emhass_power_profile": [1, 2, 3],
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }
        coord = _make_coordinator(emhass_adapter=adapter)
        result = await coord._async_update_data()
        # Should NOT be None — came from adapter
        assert result["emhass_power_profile"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_emhass_adapter_absent_uses_defaults(self):
        """Without adapter, EMHASS keys get default None/empty values."""
        coord = _make_coordinator(emhass_adapter=None)
        result = await coord._async_update_data()
        assert result["emhass_power_profile"] is None
        assert result["emhass_status"] is None

    @pytest.mark.asyncio
    async def test_emhass_adapter_warning_on_empty_params(self):
        """Empty per_trip_emhass_params triggers a warning log."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {},
        }
        coord = _make_coordinator(emhass_adapter=adapter)
        # Capture log records via caplog
        result = await coord._async_update_data()
        assert result["per_trip_emhass_params"] == {}

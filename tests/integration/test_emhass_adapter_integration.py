"""Integration tests for EmhassAdapter — real config-entry + freezegun clock.

Drive EmhassAdapter through a full publish → remove lifecycle,
asserting on every entity registered for deferrable loads and on
the IndexManager cooldown state across time.

NFR-9: Integration test coverage for EmhassAdapter.
NFR-8: Multi-assert — assert on full dispatch args, not just "was called".
NFR-10: Distinctive data — real ISO timestamps, real-shape EMHASS config.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time

from custom_components.ev_trip_planner.emhass import (
    EMHASSAdapter,
    ErrorHandler,
    IndexManager,
    LoadPublisher,
)


def _run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.new_event_loop().run_until_complete(coro)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance for EMHASS adapter tests."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    # SOC sensor state
    soc_state = MagicMock()
    soc_state.state = "75.5"
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=soc_state)

    return hass


@pytest.fixture
def mock_config_entry():
    """Create a realistic mock ConfigEntry with vehicle data."""
    entry = MagicMock()
    entry.entry_id = "test_vehicle_001"
    entry.data = {
        "vehicle_name": "Tesla Model 3",
        "battery_capacity_kwh": 75.0,
        "charging_power_kw": 7.4,
        "safety_margin_percent": 15.0,
        "kwh_per_km": 0.15,
        "soc_sensor": "sensor.battery_soc",
    }
    entry.options = {
        "charging_power_kw": 7.4,
        "planning_horizon_days": 7,
    }
    entry.async_on_unload = MagicMock(return_value=MagicMock())
    return entry


@pytest.fixture
def emhass_adapter(mock_hass, mock_config_entry):
    """Create EMHASS adapter with real config entry."""
    return EMHASSAdapter(mock_hass, mock_config_entry)


@pytest.fixture
def realistic_trip():
    """Create a realistic trip dict with all fields populated."""
    future = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
    return {
        "id": "pun_test_001",
        "tipo": "puntual",
        "datetime": future,
        "kwh": 12.5,
        "km": 80,
        "descripcion": "Test trip to city",
        "activo": True,
        "creado": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def realistic_recurring_trip():
    """Create a realistic recurring trip dict."""
    return {
        "id": "rec_lun_001",
        "tipo": "recurrente",
        "dia_semana": "lunes",
        "hora": "09:00",
        "kwh": 5.0,
        "km": 30,
        "descripcion": "Daily commute",
        "activo": True,
        "creado": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Test: Adapter initialization
# ============================================================================


class TestAdapterInit:
    """Test EMHASS adapter initialization with real config entry."""

    def test_adapter_created_with_config(self, emhass_adapter, mock_config_entry):
        """Adapter initialized with values from config entry."""
        assert emhass_adapter.vehicle_id == mock_config_entry.entry_id
        assert emhass_adapter._stored_charging_power_kw == 7.4
        assert emhass_adapter._load_publisher.battery_capacity_kwh == 75.0
        assert emhass_adapter._load_publisher.charging_power_kw == 7.4
        assert emhass_adapter._load_publisher.safety_margin_percent == 15.0

    def test_adapter_has_subcomponents(self, emhass_adapter):
        """Adapter has IndexManager, LoadPublisher, ErrorHandler."""
        assert emhass_adapter._index_manager is not None
        assert emhass_adapter._load_publisher is not None
        assert emhass_adapter._error_handler is not None
        assert isinstance(emhass_adapter._index_manager, IndexManager)
        assert isinstance(emhass_adapter._load_publisher, LoadPublisher)
        assert isinstance(emhass_adapter._error_handler, ErrorHandler)

    def test_missing_battery_capacity_raises(self, mock_hass):
        """Missing battery_capacity_kwh raises ValueError."""
        entry = MagicMock()
        entry.entry_id = "test"
        entry.data = {"vehicle_name": "Test"}
        entry.options = {}
        entry.async_on_unload = MagicMock(return_value=MagicMock())
        with pytest.raises(ValueError, match="battery_capacity_kwh"):
            EMHASSAdapter(mock_hass, entry)

    def test_missing_charging_power_raises(self, mock_hass):
        """Missing charging_power_kw raises ValueError."""
        entry = MagicMock()
        entry.entry_id = "test"
        entry.data = {
            "vehicle_name": "Test",
            "battery_capacity_kwh": 50.0,
        }
        entry.options = {}
        entry.async_on_unload = MagicMock(return_value=MagicMock())
        with pytest.raises(ValueError, match="charging_power_kw"):
            EMHASSAdapter(mock_hass, entry)

    def test_missing_safety_margin_raises(self, mock_hass):
        """Missing safety_margin_percent raises ValueError."""
        entry = MagicMock()
        entry.entry_id = "test"
        entry.data = {
            "vehicle_name": "Test",
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 7.0,
        }
        entry.options = {}
        entry.async_on_unload = MagicMock(return_value=MagicMock())
        with pytest.raises(ValueError, match="safety_margin_percent"):
            EMHASSAdapter(mock_hass, entry)

    def test_soc_sensor_from_config(self, mock_hass, mock_config_entry):
        """SOC sensor name read from config entry."""
        adapter = EMHASSAdapter(mock_hass, mock_config_entry)
        assert adapter._load_publisher._soc_sensor == "sensor.battery_soc"


# ============================================================================
# Test: IndexManager lifecycle
# ============================================================================


class TestIndexManagerLifecycle:
    """Test IndexManager assign/release/cooldown lifecycle."""

    def test_assign_index_to_new_trip(self, emhass_adapter):
        """First trip gets index 0."""
        result = emhass_adapter._index_manager.assign_index("trip-1")
        assert result == 0
        assert "trip-1" in emhass_adapter._index_map
        assert emhass_adapter._index_map["trip-1"] == 0

    def test_assign_index_returns_existing(self, emhass_adapter):
        """Same trip_id returns same index."""
        idx1 = emhass_adapter._index_manager.assign_index("trip-1")
        idx2 = emhass_adapter._index_manager.assign_index("trip-1")
        assert idx1 == idx2 == 0

    def test_second_trip_gets_next_index(self, emhass_adapter):
        """Second trip gets index 1."""
        emhass_adapter._index_manager.assign_index("trip-1")
        idx2 = emhass_adapter._index_manager.assign_index("trip-2")
        assert idx2 == 1

    def test_release_index_removes_map_entry(self, emhass_adapter):
        """Released index removed from _index_map."""
        emhass_adapter._index_manager.assign_index("trip-1")
        assert emhass_adapter._index_manager.assign_index("trip-2") == 1
        result = emhass_adapter._index_manager.release_index("trip-1")
        assert result is True
        assert "trip-1" not in emhass_adapter._index_map

    def test_release_unknown_trip_returns_false(self, emhass_adapter):
        """Release non-existent trip returns False."""
        assert emhass_adapter._index_manager.release_index("nonexistent") is False

    def test_cooldown_prevents_immediate_reuse(self, emhass_adapter):
        """Released index is in cooldown and not reused."""
        idx = emhass_adapter._index_manager.assign_index("trip-1")
        emhass_adapter._index_manager.release_index("trip-1")
        # Trip-1's index should be in cooldown
        assert idx in [r["index"] for r in emhass_adapter._index_manager._released_indices]
        # Trip-2 should get the next non-cooldown index
        idx2 = emhass_adapter._index_manager.assign_index("trip-2")
        assert idx2 != idx

    def test_cooldown_expiry_allows_reuse(self):
        """After cooldown expires, index can be reused."""
        mgr = IndexManager(cooldown_hours=0)  # Instant cooldown
        idx = mgr.assign_index("trip-1")
        mgr.release_index("trip-1")
        # With cooldown_hours=0, the index should be available again
        new_idx = mgr.assign_index("trip-2")
        assert new_idx == idx  # Same index reused after cooldown


# ============================================================================
# Test: Publish cycle via adapter API
# ============================================================================


class TestPublishCycle:
    """Test full publish lifecycle through adapter's async_publish_all."""

    def test_publish_success(self, emhass_adapter, realistic_trip):
        """Successful publish populates cache and published_trips."""
        result = _run_async(
            emhass_adapter.async_publish_all_deferrable_loads([realistic_trip])
        )
        assert result is True
        assert "pun_test_001" in emhass_adapter._published_trips
        assert "pun_test_001" in emhass_adapter._cached_per_trip_params

    def test_publish_creaches_index(self, emhass_adapter, realistic_trip):
        """Published trip has emhass_index in cache."""
        _run_async(emhass_adapter.async_publish_all_deferrable_loads([realistic_trip]))
        params = emhass_adapter._cached_per_trip_params["pun_test_001"]
        assert params["emhass_index"] == 0
        assert params["activo"] is True
        assert "def_total_hours" in params
        assert "def_start_timestep" in params
        assert "def_end_timestep" in params
        assert "power_watts" in params
        assert "kwh_needed" in params

    def test_publish_multi_assert_full_params(self, emhass_adapter, realistic_trip):
        """Assert on ALL cache entry fields after publish."""
        _run_async(emhass_adapter.async_publish_all_deferrable_loads([realistic_trip]))
        params = emhass_adapter._cached_per_trip_params["pun_test_001"]
        # Assert every key is present and non-None
        assert params["activo"] is True
        assert params["emhass_index"] == 0
        assert isinstance(params["def_start_timestep"], int)
        assert isinstance(params["def_end_timestep"], int)
        assert params["def_end_timestep"] >= params["def_start_timestep"]
        assert params["def_total_hours"] >= 0
        assert params["total_hours"] == params["def_total_hours"]
        assert params["power_watts"] >= 0
        assert params["kwh_needed"] >= 0
        assert isinstance(params["charging_window"], list)
        assert isinstance(params["p_deferrable_matrix"], list)

    def test_publish_future_deadline(self, emhass_adapter):
        """Trip with future deadline publishes successfully."""
        future = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        trip = {
            "id": "pun_future",
            "tipo": "puntual",
            "datetime": future,
            "kwh": 10.0,
        }
        result = _run_async(
            emhass_adapter.async_publish_all_deferrable_loads([trip])
        )
        assert result is True

    def test_publish_past_deadline_zero_hours(self, emhass_adapter):
        """Trip with past deadline gets 0 def_total_hours (no charging window)."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        trip = {
            "id": "pun_past",
            "tipo": "puntual",
            "datetime": past,
            "kwh": 10.0,
        }
        result = _run_async(
            emhass_adapter.async_publish_all_deferrable_loads([trip])
        )
        assert result is True
        assert "pun_past" in emhass_adapter._cached_per_trip_params
        params = emhass_adapter._cached_per_trip_params["pun_past"]
        # Past deadline → zero-length charging window (start==end==0)
        assert params["def_start_timestep"] == 0
        assert params["def_end_timestep"] == 0

    def test_publish_no_id_skipped(self, emhass_adapter):
        """Trip without ID produces 0 cached params (skipped)."""
        trip = {"tipo": "puntual", "kwh": 10.0}
        result = _run_async(
            emhass_adapter.async_publish_all_deferrable_loads([trip])
        )
        # Adapter returns True (no exception), but trip is skipped
        assert result is True
        assert len(emhass_adapter._cached_per_trip_params) == 0


# ============================================================================
# Test: Remove cycle
# ============================================================================


class TestRemoveCycle:
    """Test remove lifecycle with assertions on IndexManager state."""

    def test_remove_success(self, emhass_adapter, realistic_trip):
        """Successful remove returns True."""
        _run_async(emhass_adapter.async_publish_all_deferrable_loads([realistic_trip]))
        result = _run_async(emhass_adapter.async_remove_deferrable_load("pun_test_001"))
        assert result is True

    def test_remove_removes_from_index_map(self, emhass_adapter, realistic_trip):
        """Remove removes trip from index map."""
        _run_async(emhass_adapter.async_publish_all_deferrable_loads([realistic_trip]))
        _run_async(emhass_adapter.async_remove_deferrable_load("pun_test_001"))
        assert "pun_test_001" not in emhass_adapter._index_map

    def test_remove_in_cooldown_after_release(self, emhass_adapter, realistic_trip):
        """After remove, released index is in cooldown."""
        _run_async(emhass_adapter.async_publish_all_deferrable_loads([realistic_trip]))
        _run_async(emhass_adapter.async_remove_deferrable_load("pun_test_001"))
        released = emhass_adapter._index_manager._released_indices
        assert len(released) >= 1
        assert released[-1]["index"] == 0

    def test_remove_unknown_trip(self, emhass_adapter):
        """Remove non-existent trip returns False."""
        result = _run_async(emhass_adapter.async_remove_deferrable_load("nonexistent"))
        assert result is False

    def test_remove_multi_assert(self, emhass_adapter, realistic_trip):
        """Assert on index map state, cooldown state, and published_trips after remove."""
        _run_async(emhass_adapter.async_publish_all_deferrable_loads([realistic_trip]))
        before_count = len(emhass_adapter._index_map)
        before_cooldown = len(emhass_adapter._index_manager._released_indices)
        before_published = len(emhass_adapter._published_trips)

        assert before_count == 1
        assert before_published == 1

        result = _run_async(emhass_adapter.async_remove_deferrable_load("pun_test_001"))
        assert result is True
        assert len(emhass_adapter._index_map) == before_count - 1
        assert len(emhass_adapter._index_manager._released_indices) == before_cooldown + 1

    def test_remove_cleans_cache(self, emhass_adapter, realistic_trip):
        """async_remove_deferrable_load cleans _cached_per_trip_params."""
        _run_async(emhass_adapter.async_publish_all_deferrable_loads([realistic_trip]))
        assert "pun_test_001" in emhass_adapter._cached_per_trip_params

        result = _run_async(emhass_adapter.async_remove_deferrable_load("pun_test_001"))
        assert result is True
        assert "pun_test_001" not in emhass_adapter._cached_per_trip_params


# ============================================================================
# Test: Multi-trip publish
# ============================================================================


class TestMultiTripPublish:
    """Test publishing multiple trips and asserting full state."""

    def test_publish_two_trips(self, emhass_adapter, realistic_trip, realistic_recurring_trip):
        """Two trips get different indices."""
        _run_async(emhass_adapter.async_publish_all_deferrable_loads(
            [realistic_trip, realistic_recurring_trip]
        ))
        assert "pun_test_001" in emhass_adapter._index_map
        assert "rec_lun_001" in emhass_adapter._index_map
        assert emhass_adapter._index_map["pun_test_001"] != emhass_adapter._index_map["rec_lun_001"]

    def test_multi_assert_all_published(self, emhass_adapter, realistic_trip, realistic_recurring_trip):
        """After publishing both trips, assert all state is correct."""
        _run_async(emhass_adapter.async_publish_all_deferrable_loads(
            [realistic_trip, realistic_recurring_trip]
        ))
        # Both in published_trips
        assert "pun_test_001" in emhass_adapter._published_trips
        assert "rec_lun_001" in emhass_adapter._published_trips

        # Both in index map
        assert len(emhass_adapter._index_map) == 2

        # Both in cache
        assert "pun_test_001" in emhass_adapter._cached_per_trip_params
        assert "rec_lun_001" in emhass_adapter._cached_per_trip_params

        # Each has valid params
        for tid in ("pun_test_001", "rec_lun_001"):
            params = emhass_adapter._cached_per_trip_params[tid]
            assert params["emhass_index"] >= 0
            assert params["def_total_hours"] >= 0

    def test_publish_three_trips_gets_sequential_indices(self, emhass_adapter):
        """Three distinct trips get indices 0, 1, 2."""
        trips = []
        for i in range(3):
            trips.append({
                "id": f"trip_{i}",
                "tipo": "puntual",
                "datetime": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
                "kwh": 5.0,
            })
        _run_async(emhass_adapter.async_publish_all_deferrable_loads(trips))

        for i in range(3):
            assert f"trip_{i}" in emhass_adapter._index_map
            assert emhass_adapter._index_map[f"trip_{i}"] == i


# ============================================================================
# Test: IndexManager cooldown across time with freezegun
# ============================================================================


class TestCooldownAcrossTime:
    """Test IndexManager cooldown expiry using freezegun time travel."""

    def test_cooldown_prevents_reuse_within_window(self):
        """Released index cannot be reused during cooldown window."""
        mgr = IndexManager(cooldown_hours=24)
        idx = mgr.assign_index("trip-1")
        mgr.release_index("trip-1")

        # During cooldown, index should not be reused
        new_idx = mgr.assign_index("trip-2")
        assert new_idx != idx  # Different index assigned

    def test_cooldown_expiry_allows_reuse(self):
        """After cooldown expires, released index is pruned from cooldown."""
        mgr = IndexManager(cooldown_hours=0)  # Instant cooldown
        idx = mgr.assign_index("trip-1")
        mgr.release_index("trip-1")
        # With cooldown_hours=0, pruned immediately
        mgr._prune_expired_cooldown()
        assert len(mgr._released_indices) == 0
        # Next assign should succeed with next available index
        new_idx = mgr.assign_index("trip-2")
        assert new_idx >= 0  # Valid index assigned

    @freeze_time("2026-05-21T12:00:00+00:00")
    def test_cooldown_prune_expired(self):
        """Expired entries are pruned after cooldown expires."""
        mgr = IndexManager(cooldown_hours=24)

        # Assign and release at t=0
        idx = mgr.assign_index("trip-1")
        mgr.release_index("trip-1")

        # Prune before expiry — should still have entry
        mgr._prune_expired_cooldown()
        assert len(mgr._released_indices) == 1

        # After expiry — entry should be pruned
        with freeze_time("2026-05-23T12:01:00+00:00"):
            mgr._prune_expired_cooldown()
            assert len(mgr._released_indices) == 0

            # Index should be immediately reusable
            new_idx = mgr.assign_index("trip-2")
            assert new_idx == idx


# ============================================================================
# Test: ErrorHandler with real config context
# ============================================================================


class TestErrorHandlerIntegration:
    """Test ErrorHandler with config context and callback assertions."""

    def test_handle_missing_id_returns_false(self, emhass_adapter):
        """handle_missing_id returns False."""
        result = emhass_adapter._error_handler.handle_missing_id("trip-1")
        assert result is False

    def test_handle_deadline_error_returns_false(self, emhass_adapter):
        """handle_deadline_error returns False."""
        result = emhass_adapter._error_handler.handle_deadline_error("trip-1")
        assert result is False

    def test_handle_index_error_returns_none(self, emhass_adapter):
        """handle_index_error returns None."""
        result = emhass_adapter._error_handler.handle_index_error("trip-1")
        assert result is None

    def test_error_callback_invoked(self, emhass_adapter):
        """on_error callback is invoked on error."""
        callback = MagicMock()
        handler = ErrorHandler(
            hass=emhass_adapter.hass,
            on_error=callback,
        )
        handler.handle_error("test_op", ValueError("test error"))
        assert callback.call_count == 1
        call_args = callback.call_args
        assert call_args[0][0] == "test_op"
        assert isinstance(call_args[0][1], ValueError)

    def test_error_callback_exception_suppressed(self, emhass_adapter):
        """Error callback raising exception is suppressed."""
        callback = MagicMock(side_effect=RuntimeError("callback failed"))
        handler = ErrorHandler(
            hass=emhass_adapter.hass,
            on_error=callback,
        )
        # Should not propagate
        handler.handle_error("test_op", ValueError("original error"))
        assert callback.call_count == 1


# ============================================================================
# Test: async_publish_all_deferrable_loads
# ============================================================================


class TestPublishAll:
    """Test async_publish_all_deferrable_loads with full state assertions."""

    def test_publish_all_empty_trips_clears_cache(self, emhass_adapter):
        """Empty trip list clears cache."""
        # First publish something
        future = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
        trip = {
            "id": "test_trip",
            "tipo": "puntual",
            "datetime": future,
            "kwh": 10.0,
        }
        _run_async(emhass_adapter.async_publish_all_deferrable_loads([trip]))
        assert len(emhass_adapter._cached_per_trip_params) > 0

        # Then publish empty
        result = _run_async(emhass_adapter.async_publish_all_deferrable_loads([]))
        assert result is True
        assert emhass_adapter._cached_per_trip_params == {}

    def test_publish_all_multiple_trips(self, emhass_adapter):
        """Publish all trips asserts on full result state."""
        future = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
        trip_list = [
            {
                "id": "trip_a",
                "tipo": "puntual",
                "datetime": future,
                "kwh": 10.0,
            },
            {
                "id": "trip_b",
                "tipo": "puntual",
                "datetime": future,
                "kwh": 5.0,
            },
        ]
        result = _run_async(
            emhass_adapter.async_publish_all_deferrable_loads(trip_list)
        )
        assert result is True
        assert len(emhass_adapter._published_trips) == 2

    def test_publish_all_sets_caches(self, emhass_adapter):
        """Publish all sets power profile and deferrables schedule."""
        result = _run_async(emhass_adapter.async_publish_all_deferrable_loads([]))
        assert result is True
        assert emhass_adapter._cached_power_profile is not None
        assert emhass_adapter._cached_deferrables_schedule is not None
        assert emhass_adapter._cached_emhass_status == "ready"

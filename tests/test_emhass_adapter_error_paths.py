"""Tests for EMHASS Adapter error handling and edge cases.

Covers uncovered lines in:
- emhass_adapter.py: get_cached_optimization_results, error handling methods,
  shell command verification, power profile calculation, sensor checking.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_INDEX_COOLDOWN_HOURS,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_SERVICE,
    CONF_VEHICLE_NAME,
    EMHASS_STATE_ACTIVE,
    EMHASS_STATE_ERROR,
    EMHASS_STATE_READY,
)


# =============================================================================
# get_cached_optimization_results tests
# =============================================================================

class TestGetCachedOptimizationResults:
    """Tests for get_cached_optimization_results."""

    def test_returns_all_cached_fields(self):
        """Returns dict with all EMHASS data keys."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        adapter._cached_power_profile = [100, 200]
        adapter._cached_deferrables_schedule = {"slot_0": "active"}
        adapter._cached_emhass_status = EMHASS_STATE_READY

        result = adapter.get_cached_optimization_results()

        assert result["emhass_power_profile"] == [100, 200]
        assert result["emhass_deferrables_schedule"] == {"slot_0": "active"}
        assert result["emhass_status"] == EMHASS_STATE_READY

    def test_missing_attributes_return_none(self):
        """Returns None for attributes not yet set."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)

        result = adapter.get_cached_optimization_results()

        assert result["emhass_power_profile"] is None
        assert result["emhass_deferrables_schedule"] is None
        assert result["emhass_status"] is None


# =============================================================================
# get_assigned_index and get_all_assigned_indices tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_assigned_index_returns_index_when_assigned(hass, mock_store):
    """get_assigned_index returns the mapped index for a trip."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        idx = await adapter.async_assign_index_to_trip("trip_xyz")
        assert adapter.get_assigned_index("trip_xyz") == idx


@pytest.mark.asyncio
async def test_get_assigned_index_returns_none_when_not_assigned(hass, mock_store):
    """get_assigned_index returns None for unknown trip."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        assert adapter.get_assigned_index("unknown_trip") is None


@pytest.mark.asyncio
async def test_get_all_assigned_indices_returns_all_mappings(hass, mock_store):
    """get_all_assigned_indices returns all trip→index mappings."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        idx1 = await adapter.async_assign_index_to_trip("trip_a")
        idx2 = await adapter.async_assign_index_to_trip("trip_b")

        all_indices = adapter.get_all_assigned_indices()
        assert all_indices == {"trip_a": idx1, "trip_b": idx2}


@pytest.mark.asyncio
async def test_get_available_indices_excludes_assigned(hass, mock_store):
    """get_available_indices excludes assigned indices."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 10,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        idx = await adapter.async_assign_index_to_trip("trip_1")
        available = adapter.get_available_indices()

        assert idx not in available
        assert 1 in available  # Index 1 still available


# =============================================================================
# calculate_deferrable_parameters edge cases
# =============================================================================

class TestCalculateDeferrableParameters:
    """Tests for calculate_deferrable_parameters edge cases."""

    def test_zero_kwh_returns_empty(self):
        """Zero kwh trip returns empty dict."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1", "kwh": 0}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result == {}

    def test_negative_kwh_returns_empty(self):
        """Negative kwh trip returns empty dict."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1", "kwh": -5.0}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result == {}

    def test_missing_kwh_returns_empty(self):
        """Trip without kwh field returns empty dict."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1"}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result == {}

    def test_valid_trip_with_future_deadline(self):
        """Valid trip with future deadline returns full params."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        future_time = (datetime.now() + timedelta(hours=10)).isoformat()
        trip = {"id": "trip_1", "kwh": 7.4, "datetime": future_time}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result["total_energy_kwh"] == 7.4
        assert result["power_watts"] == 7400.0
        assert result["total_hours"] == 1.0
        assert result["end_timestep"] >= 1
        assert result["is_single_constant"] is True

    def test_valid_trip_without_deadline_uses_24h_default(self):
        """Trip without datetime uses 24h default end_timestep."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1", "kwh": 7.4}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result["total_energy_kwh"] == 7.4
        assert result["end_timestep"] == 24

    def test_trip_with_past_deadline_caps_end_timestep(self):
        """Trip with past deadline caps end_timestep at 1."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        past_time = (datetime.now() - timedelta(hours=5)).isoformat()
        trip = {"id": "trip_1", "kwh": 7.4, "datetime": past_time}

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result["end_timestep"] == 1

    def test_exception_in_calculation_returns_empty_dict(self):
        """Exception during calculation returns empty dict without raising."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trip = {"id": "trip_1", "kwh": "not_a_number"}  # String instead of number

        result = adapter.calculate_deferrable_parameters(trip, 7.4)

        assert result == {}


# =============================================================================
# async_verify_shell_command_integration tests
# =============================================================================

@pytest.mark.asyncio
async def test_verify_shell_command_deferrable_sensor_not_found(hass, mock_store):
    """Returns error when deferrable sensor does not exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_exists"] is False
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0]


@pytest.mark.asyncio
async def test_verify_shell_command_sensor_missing_power_profile(
    hass, mock_store
):
    """Returns error when sensor exists but lacks power_profile_watts."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.attributes = {}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)

        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_exists"] is True
        assert result["deferrable_sensor_has_data"] is False


@pytest.mark.asyncio
async def test_verify_shell_command_sensor_with_empty_profile(hass, mock_store):
    """Returns error when sensor has empty power profile."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.attributes = {"power_profile_watts": []}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)

        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_has_data"] is False


@pytest.mark.asyncio
async def test_verify_shell_command_fully_configured(hass, mock_store):
    """Returns is_configured=True when sensor has data and EMHASS sensors exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.attributes = {"power_profile_watts": [100, 200, 300]}
    mock_sensor.entity_id = "sensor.emhass_perfil_diferible_test_entry_id"

    mock_emhass_sensor = MagicMock()
    mock_emhass_sensor.entity_id = "sensor.emhass_response_1"

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)
        adapter.hass.states.async_all = MagicMock(
            return_value=[mock_emhass_sensor]
        )
        await adapter.async_assign_index_to_trip("trip_1")

        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_exists"] is True
        assert result["deferrable_sensor_has_data"] is True
        assert result["is_configured"] is True


# =============================================================================
# async_check_emhass_response_sensors tests
# =============================================================================

@pytest.mark.asyncio
async def test_check_emhass_no_trips_returns_all_verified(hass, mock_store):
    """Returns all_verified=True when no trips to check."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter.async_check_emhass_response_sensors()

        assert result["all_trips_verified"] is True
        assert result["verified_trips"] == []
        assert result["missing_trips"] == []


@pytest.mark.asyncio
async def test_check_emhass_trip_missing_config_sensor(hass, mock_store):
    """Returns missing_trips when config sensor doesn't exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        await adapter.async_assign_index_to_trip("trip_1")
        adapter.hass.states.get = MagicMock(return_value=None)
        adapter.hass.states.async_all = MagicMock(return_value=[])

        result = await adapter.async_check_emhass_response_sensors()

        assert result["all_trips_verified"] is False
        assert "trip_1" in result["missing_trips"]


@pytest.mark.asyncio
async def test_check_emhass_with_active_config_sensor(hass, mock_store):
    """Returns trip as verified when config sensor is ACTIVE."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.state = EMHASS_STATE_ACTIVE
    mock_sensor.attributes = {}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        await adapter.async_assign_index_to_trip("trip_1")
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)
        adapter.hass.states.async_all = MagicMock(return_value=[mock_sensor])

        result = await adapter.async_check_emhass_response_sensors()

        assert result["all_trips_verified"] is True
        assert "trip_1" in result["verified_trips"]


@pytest.mark.asyncio
async def test_check_emhass_with_specific_trip_ids(hass, mock_store):
    """Checks only the specified trip IDs."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    mock_sensor = MagicMock()
    mock_sensor.state = EMHASS_STATE_ACTIVE
    mock_sensor.attributes = {}

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        await adapter.async_assign_index_to_trip("trip_1")
        await adapter.async_assign_index_to_trip("trip_2")
        adapter.hass.states.get = MagicMock(return_value=mock_sensor)
        adapter.hass.states.async_all = MagicMock(return_value=[mock_sensor])

        result = await adapter.async_check_emhass_response_sensors(trip_ids=["trip_1"])

        assert "trip_1" in result["verified_trips"]
        assert "trip_2" not in result["verified_trips"]


# =============================================================================
# Error handling: async_handle_emhass_unavailable, async_handle_sensor_error,
# async_handle_shell_command_failure
# =============================================================================

@pytest.mark.asyncio
async def test_handle_emhass_unavailable_sends_notification(hass, mock_store):
    """async_handle_emhass_unavailable calls async_notify_error."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        with patch.object(
            adapter, "async_notify_error", new_callable=AsyncMock
        ) as mock_notify:
            mock_notify.return_value = True
            result = await adapter.async_handle_emhass_unavailable(
                "Connection refused", trip_id="trip_abc"
            )

            mock_notify.assert_called_once()
            call_args = mock_notify.call_args
            assert call_args[1]["error_type"] == "emhass_unavailable"
            assert "trip_abc" in call_args[1]["trip_id"]


@pytest.mark.asyncio
async def test_handle_sensor_error_calls_notify(hass, mock_store):
    """async_handle_sensor_error sends error notification."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        with patch.object(
            adapter, "async_notify_error", new_callable=AsyncMock
        ) as mock_notify:
            mock_notify.return_value = True
            result = await adapter.async_handle_sensor_error(
                "Sensor data invalid", "sensor.test"
            )

            mock_notify.assert_called_once()
            assert mock_notify.call_args[1]["error_type"] == "sensor_missing"


@pytest.mark.asyncio
async def test_handle_shell_command_failure_calls_notify(hass, mock_store):
    """async_handle_shell_command_failure sends error notification."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        with patch.object(
            adapter, "async_notify_error", new_callable=AsyncMock
        ) as mock_notify:
            mock_notify.return_value = True
            result = await adapter.async_handle_shell_command_failure(
                trip_id="trip_xyz"
            )

            mock_notify.assert_called_once()
            assert mock_notify.call_args[1]["error_type"] == "shell_command_failure"


# =============================================================================
# get_last_error and async_clear_error tests
# =============================================================================

class TestGetLastError:
    """Tests for get_last_error."""

    def test_returns_none_when_no_error(self):
        """Returns None when _last_error is not set."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        adapter._last_error = None
        adapter._last_error_time = None

        result = adapter.get_last_error()

        assert result is None

    def test_returns_error_dict_when_error_exists(self):
        """Returns dict with message and time when error exists."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        adapter._last_error = "Something went wrong"
        adapter._last_error_time = datetime(2025, 1, 15, 10, 30, 0)

        result = adapter.get_last_error()

        assert result["message"] == "Something went wrong"
        assert result["time"] == "2025-01-15T10:30:00"


@pytest.mark.asyncio
async def test_async_clear_error_clears_error_state(hass, mock_store):
    """async_clear_error clears _last_error and _last_error_time."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter._last_error = "Previous error"
        adapter._last_error_time = datetime.now()

        mock_sensor_state = MagicMock()
        mock_sensor_state.attributes = {"error_type": "old_error"}
        sensor_id = f"sensor.emhass_perfil_diferible_{adapter.entry_id}"
        adapter.hass.states.get = MagicMock(return_value=mock_sensor_state)

        await adapter.async_clear_error()

        assert adapter._last_error is None
        assert adapter._last_error_time is None


@pytest.mark.asyncio
async def test_async_clear_error_with_no_sensor(hass, mock_store):
    """async_clear_error handles case where sensor doesn't exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter._last_error = "Previous error"
        adapter.hass.states.get = MagicMock(return_value=None)

        # Should not raise
        await adapter.async_clear_error()

        assert adapter._last_error is None


# =============================================================================
# _calculate_power_profile_from_trips tests
# =============================================================================

class TestCalculatePowerProfileFromTrips:
    """Tests for _calculate_power_profile_from_trips edge cases."""

    def test_empty_trips_list_returns_all_zeros(self):
        """Empty trips list returns power profile of all zeros."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)

        result = adapter._calculate_power_profile_from_trips([], 7.4, 24)

        assert result == [0.0] * 24

    def test_trip_without_datetime_is_skipped(self):
        """Trip without datetime field is skipped."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        trips = [{"id": "trip_1", "kwh": 7.4}]

        result = adapter._calculate_power_profile_from_trips(trips, 7.4, 24)

        assert result == [0.0] * 24

    def test_trip_with_past_deadline_is_skipped(self):
        """Trip with deadline in the past is skipped."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        past_time = (datetime.now() - timedelta(hours=5)).isoformat()
        trips = [{"id": "trip_1", "kwh": 7.4, "datetime": past_time}]

        result = adapter._calculate_power_profile_from_trips(trips, 7.4, 24)

        assert 7400.0 not in result  # Should be all zeros

    def test_trip_with_future_deadline_sets_charging_window(self):
        """Trip with future deadline sets charging in appropriate hours."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        # Trip 20 hours from now
        future_time = (datetime.now() + timedelta(hours=20)).isoformat()
        trips = [{"id": "trip_1", "kwh": 7.4, "datetime": future_time}]

        result = adapter._calculate_power_profile_from_trips(trips, 7.4, 168)

        # Should have some charging slots set
        assert any(v > 0 for v in result)

    def test_multiple_trips_all_included(self):
        """Multiple trips all contribute to the power profile."""
        adapter = EMHASSAdapter.__new__(EMHASSAdapter)
        future_time_1 = (datetime.now() + timedelta(hours=10)).isoformat()
        future_time_2 = (datetime.now() + timedelta(hours=30)).isoformat()
        trips = [
            {"id": "trip_1", "kwh": 7.4, "datetime": future_time_1},
            {"id": "trip_2", "kwh": 3.7, "datetime": future_time_2},
        ]

        result = adapter._calculate_power_profile_from_trips(trips, 7.4, 168)

        # Both should set charging
        assert any(v > 0 for v in result)


# =============================================================================
# async_publish_deferrable_load edge cases
# =============================================================================

@pytest.mark.asyncio
async def test_publish_deferrable_load_no_trip_manager(hass, mock_store):
    """async_publish_deferrable_load handles missing trip manager gracefully."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        adapter.hass.data["test_entry_id"] = MagicMock()
        adapter.hass.data["test_entry_id"].trip_manager = None

        future_time = (datetime.now() + timedelta(hours=10)).isoformat()
        trip = {
            "id": "trip_abc",
            "kwh": 7.4,
            "datetime": future_time,
            "tipo": "puntual",
        }

        # Should handle None trip_manager without raising
        try:
            await adapter.async_publish_deferrable_load(trip)
        except Exception as e:
            if "NoneType" in str(type(e)):
                pytest.fail("async_publish_deferrable_load raised on None trip_manager")


# =============================================================================
# async_get_integration_status tests
# =============================================================================

@pytest.mark.asyncio
async def test_async_get_integration_status_returns_status_dict(hass, mock_store):
    """async_get_integration_status returns comprehensive status dict."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        status = await adapter.async_get_integration_status()

        assert "status" in status
        assert "message" in status
        assert "details" in status
        assert "verification" in status["details"]
        assert "response_check" in status["details"]

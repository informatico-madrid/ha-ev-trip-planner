"""Tests for schedule_monitor.py error handling and edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from homeassistant.core import HomeAssistant


def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.states = Mock()
    hass.services = Mock()
    hass.async_create_task = Mock()
    hass.data = {}

    # Add bus attribute needed by async_track_state_change_event
    hass.bus = Mock()
    hass.bus.async_listen = Mock(return_value=Mock())

    return hass


@pytest.fixture
def mock_control_strategy():
    """Create mock control strategy."""
    strategy = Mock()
    strategy.async_activate = AsyncMock(return_value=True)
    strategy.async_deactivate = AsyncMock(return_value=True)
    strategy.async_get_status = AsyncMock(return_value=False)
    return strategy


@pytest.fixture
def mock_presence_monitor():
    """Create mock presence monitor."""
    monitor = Mock()
    monitor.async_check_home_status = AsyncMock(return_value=True)
    monitor.async_check_plugged_status = AsyncMock(return_value=True)
    return monitor


@pytest.fixture
def mock_emhass_adapter():
    """Create mock EMHASS adapter."""
    adapter = Mock()
    adapter.get_all_assigned_indices = Mock(return_value={})
    adapter.emhass_available = True
    return adapter


# =============================================================================
# VehicleScheduleMonitor - error handling branches (note: error paths that
# require async_activate/async_deactivate returning failed results are
# tested via integration tests in production)
# =============================================================================


@pytest.mark.asyncio
async def test_async_start_charging_no_presence_monitor(
    mock_control_strategy, mock_emhass_adapter
):
    """Test _async_start_charging when presence_monitor is None."""
    from custom_components.ev_trip_planner.schedule_monitor import VehicleScheduleMonitor

    hass = mock_hass()
    monitor = VehicleScheduleMonitor(
        hass=hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=None,  # No presence monitor
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )

    # Control strategy activate returns success
    success_result = MagicMock()
    success_result.success = True
    mock_control_strategy.async_activate = AsyncMock(return_value=success_result)

    # Should not raise even with no presence monitor
    await monitor._async_start_charging(0)

    # Control strategy should be called
    mock_control_strategy.async_activate.assert_called_once()


@pytest.mark.asyncio
async def test_async_handle_schedule_change_parses_schedule(
    mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test _async_handle_schedule_change with valid schedule triggers charging."""
    from custom_components.ev_trip_planner.schedule_monitor import VehicleScheduleMonitor

    hass = mock_hass()
    monitor = VehicleScheduleMonitor(
        hass=hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )

    # Mock schedule entity exists with "on" state
    mock_state = MagicMock()
    mock_state.state = "on"
    hass.states.get = Mock(return_value=mock_state)

    # Mock presence for start charging
    mock_presence_monitor.async_check_home_status = AsyncMock(return_value=True)
    mock_presence_monitor.async_check_plugged_status = AsyncMock(return_value=True)

    # Mock start charging
    success_result = MagicMock()
    success_result.success = True
    mock_control_strategy.async_activate = AsyncMock(return_value=success_result)
    monitor._async_notify = AsyncMock()

    # Call directly (schedule change triggers start)
    await monitor._async_handle_schedule_change(0)

    # Should trigger start charging
    mock_control_strategy.async_activate.assert_called_once()


@pytest.mark.asyncio
async def test_async_handle_schedule_change_parses_schedule_off(
    mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test _async_handle_schedule_change with 'off' schedule triggers stop."""
    from custom_components.ev_trip_planner.schedule_monitor import VehicleScheduleMonitor

    hass = mock_hass()
    monitor = VehicleScheduleMonitor(
        hass=hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )

    # Mock schedule entity exists with "off" state
    mock_state = MagicMock()
    mock_state.state = "off"
    hass.states.get = Mock(return_value=mock_state)

    # Mock stop charging
    monitor._last_actions[0] = "start"
    success_result = MagicMock()
    success_result.success = True
    mock_control_strategy.async_deactivate = AsyncMock(return_value=success_result)
    monitor._async_notify = AsyncMock()

    # Call directly
    await monitor._async_handle_schedule_change(0)

    # Should trigger stop charging
    mock_control_strategy.async_deactivate.assert_called_once()


@pytest.mark.asyncio
async def test_async_notify_error_handling(
    mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test _async_notify handles exceptions gracefully."""
    from custom_components.ev_trip_planner.schedule_monitor import VehicleScheduleMonitor

    hass = mock_hass()
    monitor = VehicleScheduleMonitor(
        hass=hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="invalid-service-no-dot",  # Invalid format
        emhass_adapter=mock_emhass_adapter,
    )

    # Should not raise even with invalid service
    await monitor._async_notify("Test Title", "Test Message")


# =============================================================================
# VehicleScheduleMonitor - duplicate action prevention
# =============================================================================

@pytest.mark.asyncio
async def test_async_start_charging_duplicate_prevents_second_call(
    mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test that _async_start_charging prevents duplicate calls."""
    from custom_components.ev_trip_planner.schedule_monitor import VehicleScheduleMonitor

    hass = mock_hass()
    monitor = VehicleScheduleMonitor(
        hass=hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )

    # First: set _last_actions to "start" (already started)
    monitor._last_actions[0] = "start"

    # Second: mock async_activate to track if called
    mock_control_strategy.async_activate = AsyncMock()

    # Should not call activate (duplicate prevention)
    await monitor._async_start_charging(0)
    mock_control_strategy.async_activate.assert_not_called()


@pytest.mark.asyncio
async def test_async_stop_charging_duplicate_prevents_second_call(
    mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test that _async_stop_charging prevents duplicate calls."""
    from custom_components.ev_trip_planner.schedule_monitor import VehicleScheduleMonitor

    hass = mock_hass()
    monitor = VehicleScheduleMonitor(
        hass=hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )

    # Already stopped
    monitor._last_actions[0] = "stop"

    # Should not call deactivate
    mock_control_strategy.async_deactivate = AsyncMock()
    await monitor._async_stop_charging(0)
    mock_control_strategy.async_deactivate.assert_not_called()


# =============================================================================
# VehicleScheduleMonitor - schedule parsing
# =============================================================================

def test_parse_schedule_with_unknown_state():
    """_parse_schedule returns False for 'unknown' state."""
    from custom_components.ev_trip_planner.schedule_monitor import VehicleScheduleMonitor

    monitor = VehicleScheduleMonitor(
        hass=MagicMock(),
        vehicle_id="test_vehicle",
        control_strategy=MagicMock(),
        presence_monitor=MagicMock(),
        notification_service="persistent_notification.create",
        emhass_adapter=MagicMock(),
    )

    assert monitor._parse_schedule("unknown") is False


def test_parse_schedule_with_unavailable_state():
    """_parse_schedule returns False for 'unavailable' state."""
    from custom_components.ev_trip_planner.schedule_monitor import VehicleScheduleMonitor

    monitor = VehicleScheduleMonitor(
        hass=MagicMock(),
        vehicle_id="test_vehicle",
        control_strategy=MagicMock(),
        presence_monitor=MagicMock(),
        notification_service="persistent_notification.create",
        emhass_adapter=MagicMock(),
    )

    assert monitor._parse_schedule("unavailable") is False


def test_parse_schedule_with_empty_state():
    """_parse_schedule returns False for empty state."""
    from custom_components.ev_trip_planner.schedule_monitor import VehicleScheduleMonitor

    monitor = VehicleScheduleMonitor(
        hass=MagicMock(),
        vehicle_id="test_vehicle",
        control_strategy=MagicMock(),
        presence_monitor=MagicMock(),
        notification_service="persistent_notification.create",
        emhass_adapter=MagicMock(),
    )

    assert monitor._parse_schedule("") is False

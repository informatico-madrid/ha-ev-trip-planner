"""Tests for Schedule Monitor."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.ev_trip_planner.schedule_monitor import (
    ScheduleMonitor,
    VehicleScheduleMonitor,
)
from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME,
    CONF_NOTIFICATION_SERVICE,
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.states = Mock()
    hass.services = Mock()
    hass.async_create_task = Mock()
    hass.data = {}  # Add data attribute needed by async_track_state_change_event
    
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
    adapter.get_all_assigned_indices = Mock(return_value={
        "trip_001": 0,
        "trip_002": 1,
    })
    adapter.vehicle_id = "test_vehicle"
    return adapter


@pytest.mark.asyncio
async def test_schedule_monitor_instantiation(mock_hass):
    """Test ScheduleMonitor can be created."""
    monitor = ScheduleMonitor(mock_hass)
    
    assert monitor.hass == mock_hass
    assert monitor._vehicle_monitors == {}
    assert monitor._unsub_handlers == []


@pytest.mark.asyncio
async def test_schedule_monitor_setup_single_vehicle(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test ScheduleMonitor setup for single vehicle."""
    monitor = ScheduleMonitor(mock_hass)
    
    vehicle_configs = {
        "entry_001": {
            CONF_VEHICLE_NAME: "test_vehicle",
            "control_strategy": mock_control_strategy,
            "presence_monitor": mock_presence_monitor,
            CONF_NOTIFICATION_SERVICE: "persistent_notification.create",
            "emhass_adapter": mock_emhass_adapter,
        }
    }
    
    await monitor.async_setup(vehicle_configs)
    
    assert "test_vehicle" in monitor._vehicle_monitors
    assert len(monitor._vehicle_monitors) == 1
    
    vehicle_monitor = monitor._vehicle_monitors["test_vehicle"]
    assert isinstance(vehicle_monitor, VehicleScheduleMonitor)
    assert vehicle_monitor.vehicle_id == "test_vehicle"


@pytest.mark.asyncio
async def test_schedule_monitor_setup_multiple_vehicles(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test ScheduleMonitor setup for multiple vehicles."""
    monitor = ScheduleMonitor(mock_hass)
    
    vehicle_configs = {
        "entry_001": {
            CONF_VEHICLE_NAME: "vehicle_1",
            "control_strategy": mock_control_strategy,
            "presence_monitor": mock_presence_monitor,
            CONF_NOTIFICATION_SERVICE: "persistent_notification.create",
            "emhass_adapter": mock_emhass_adapter,
        },
        "entry_002": {
            CONF_VEHICLE_NAME: "vehicle_2",
            "control_strategy": mock_control_strategy,
            "presence_monitor": mock_presence_monitor,
            CONF_NOTIFICATION_SERVICE: "persistent_notification.create",
            "emhass_adapter": mock_emhass_adapter,
        },
    }
    
    await monitor.async_setup(vehicle_configs)
    
    assert "vehicle_1" in monitor._vehicle_monitors
    assert "vehicle_2" in monitor._vehicle_monitors
    assert len(monitor._vehicle_monitors) == 2


@pytest.mark.asyncio
async def test_schedule_monitor_stop(mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter):
    """Test ScheduleMonitor stops all vehicle monitors."""
    monitor = ScheduleMonitor(mock_hass)
    
    vehicle_configs = {
        "entry_001": {
            CONF_VEHICLE_NAME: "test_vehicle",
            "control_strategy": mock_control_strategy,
            "presence_monitor": mock_presence_monitor,
            CONF_NOTIFICATION_SERVICE: "persistent_notification.create",
            "emhass_adapter": mock_emhass_adapter,
        }
    }
    
    await monitor.async_setup(vehicle_configs)
    
    # Stop monitoring
    await monitor.async_stop()
    
    assert len(monitor._vehicle_monitors) == 0


@pytest.mark.asyncio
async def test_vehicle_schedule_monitor_instantiation(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test VehicleScheduleMonitor can be created."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    assert monitor.hass == mock_hass
    assert monitor.vehicle_id == "test_vehicle"
    assert monitor.control_strategy == mock_control_strategy
    assert monitor.presence_monitor == mock_presence_monitor
    assert monitor.notification_service == "persistent_notification.create"
    assert monitor.emhass_adapter == mock_emhass_adapter
    assert monitor._unsub_handlers == {}
    assert monitor._last_actions == {}


@pytest.mark.asyncio
async def test_vehicle_monitor_start_with_trips(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test VehicleScheduleMonitor starts monitoring existing trips."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    # Mock schedule entity exists
    mock_hass.states.get = Mock(side_effect=lambda entity_id: Mock(state="idle") if "schedule" in entity_id else None)
    
    with patch.object(monitor, '_async_monitor_schedule', new_callable=AsyncMock) as mock_monitor:
        await monitor.async_start()
        
        # Should monitor both indices (0 and 1)
        assert mock_monitor.call_count == 2
        mock_monitor.assert_any_call(0)
        mock_monitor.assert_any_call(1)


@pytest.mark.asyncio
async def test_vehicle_monitor_start_no_trips(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test VehicleScheduleMonitor handles no trips gracefully."""
    # Adapter with no assigned indices
    mock_emhass_adapter.get_all_assigned_indices = Mock(return_value={})
    
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    await monitor.async_start()
    
    # Should not crash
    assert monitor._unsub_handlers == {}


@pytest.mark.asyncio
async def test_vehicle_monitor_start_no_adapter(
    mock_hass, mock_control_strategy, mock_presence_monitor
):
    """Test VehicleScheduleMonitor handles missing adapter gracefully."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=None,  # No adapter
    )
    
    await monitor.async_start()
    
    # Should log warning and not crash
    assert monitor._unsub_handlers == {}


@pytest.mark.asyncio
async def test_vehicle_monitor_stop(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test VehicleScheduleMonitor stops monitoring correctly."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    # Add some mock unsub handlers
    mock_unsub1 = Mock()
    mock_unsub2 = Mock()
    monitor._unsub_handlers = {0: mock_unsub1, 1: mock_unsub2}
    monitor._last_actions = {0: "start", 1: "stop"}
    
    await monitor.async_stop()
    
    # Verify unsub functions called
    mock_unsub1.assert_called_once()
    mock_unsub2.assert_called_once()
    
    # Verify handlers cleared
    assert monitor._unsub_handlers == {}
    assert monitor._last_actions == {}


@pytest.mark.asyncio
async def test_add_trip_monitor(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test adding monitoring for a new trip."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    # Mock schedule entity exists
    mock_hass.states.get = Mock(return_value=Mock(state="idle"))
    
    with patch.object(monitor, '_async_monitor_schedule', new_callable=AsyncMock) as mock_monitor:
        await monitor.async_add_trip_monitor("trip_003", 2)
        
        # Should monitor index 2
        mock_monitor.assert_called_once_with(2)


@pytest.mark.asyncio
async def test_add_trip_monitor_already_exists(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test adding monitoring for already monitored index."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    # Already monitoring index 0
    monitor._unsub_handlers[0] = Mock()
    
    with patch.object(monitor, '_async_monitor_schedule', new_callable=AsyncMock) as mock_monitor:
        await monitor.async_add_trip_monitor("trip_001", 0)
        
        # Should not call monitor again
        mock_monitor.assert_not_called()


@pytest.mark.asyncio
async def test_remove_trip_monitor(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test removing monitoring for a trip."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    # Add mock unsub handler
    mock_unsub = Mock()
    monitor._unsub_handlers[0] = mock_unsub
    monitor._last_actions[0] = "start"
    
    await monitor.async_remove_trip_monitor(0)
    
    # Verify unsub called and handlers cleared
    mock_unsub.assert_called_once()
    assert 0 not in monitor._unsub_handlers
    assert 0 not in monitor._last_actions


@pytest.mark.asyncio
async def test_remove_trip_monitor_not_exists(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test removing monitoring for non-existent index."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    # Should not crash
    await monitor.async_remove_trip_monitor(99)


@pytest.mark.asyncio
async def test_parse_schedule_simple_on():
    """Test schedule parsing for simple 'on' state."""
    monitor = VehicleScheduleMonitor(
        hass=Mock(),
        vehicle_id="test_vehicle",
        control_strategy=Mock(),
        presence_monitor=Mock(),
        notification_service="persistent_notification.create",
        emhass_adapter=Mock(),
    )
    
    # Test various "on" states
    assert monitor._parse_schedule("on") is True
    assert monitor._parse_schedule("ON") is True
    assert monitor._parse_schedule("On") is True
    assert monitor._parse_schedule("true") is True
    assert monitor._parse_schedule("TRUE") is True


@pytest.mark.asyncio
async def test_parse_schedule_off():
    """Test schedule parsing for 'off' state."""
    monitor = VehicleScheduleMonitor(
        hass=Mock(),
        vehicle_id="test_vehicle",
        control_strategy=Mock(),
        presence_monitor=Mock(),
        notification_service="persistent_notification.create",
        emhass_adapter=Mock(),
    )
    
    # Test various "off" states
    assert monitor._parse_schedule("off") is False
    assert monitor._parse_schedule("unknown") is False
    assert monitor._parse_schedule("unavailable") is False
    assert monitor._parse_schedule("") is False
    assert monitor._parse_schedule(None) is False


@pytest.mark.asyncio
async def test_async_notify_success(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test notification sending success."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    mock_hass.services.async_call = AsyncMock()
    
    await monitor._async_notify("Test Title", "Test Message")
    
    # Verify service call
    mock_hass.services.async_call.assert_called_once()
    call_args = mock_hass.services.async_call.call_args
    assert call_args[0][0] == "persistent_notification"
    assert call_args[0][1] == "create"
    assert call_args[0][2]["title"] == "Test Title"
    assert call_args[0][2]["message"] == "Test Message"


@pytest.mark.asyncio
async def test_async_notify_failure(
    mock_hass, mock_control_strategy, mock_presence_monitor, mock_emhass_adapter
):
    """Test notification sending failure."""
    monitor = VehicleScheduleMonitor(
        hass=mock_hass,
        vehicle_id="test_vehicle",
        control_strategy=mock_control_strategy,
        presence_monitor=mock_presence_monitor,
        notification_service="persistent_notification.create",
        emhass_adapter=mock_emhass_adapter,
    )
    
    mock_hass.services.async_call = AsyncMock(side_effect=Exception("Service error"))
    
    # Should not raise exception
    await monitor._async_notify("Test Title", "Test Message")
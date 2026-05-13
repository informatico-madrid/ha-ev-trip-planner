"""Edge-case tests for presence_monitor to hit uncovered lines.

Covers lines 150-151, 298, 305, 311, 314, 325, 351, 388, 391-392, 432, 439-440.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    CONF_HOME_COORDINATES,
    CONF_HOME_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_SOC_SENSOR,
    CONF_VEHICLE_COORDINATES_SENSOR,
)
from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor


@pytest.fixture(autouse=True)
def mock_store_class():
    """Patch Store for all presence_monitor tests."""
    from homeassistant.helpers import storage as ha_storage

    class MockStore:
        def __init__(self, *a, **kw):
            self._data = {}

        async def async_load(self):
            return self._data.get("data")

        async def async_save(self, data):
            self._data["data"] = data
            return True

    with patch.object(ha_storage, "Store", MockStore):
        yield


# ---------------------------------------------------------------------------
# _get_soc_from_sensor  (lines 150-151 — ValueError / AttributeError)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_soc_value_error(mock_hass):
    """Line 150: float(state.state) raises ValueError."""
    config = {CONF_SOC_SENSOR: "sensor.battery"}
    monitor = PresenceMonitor(mock_hass, "v1", config)
    sensor_state = Mock()
    sensor_state.state = "not_a_number"
    mock_hass.states.get = Mock(return_value=sensor_state)
    result = monitor._get_soc_from_sensor()
    assert result is None


@pytest.mark.asyncio
async def test_get_soc_attribute_error(mock_hass):
    """Line 150: float(state.state) raises AttributeError (state attr missing)."""
    config = {CONF_SOC_SENSOR: "sensor.battery"}
    monitor = PresenceMonitor(mock_hass, "v1", config)
    bad_state = MagicMock(spec=[])  # no .state attribute
    mock_hass.states.get = Mock(return_value=bad_state)
    result = monitor._get_soc_from_sensor()
    assert result is None


# ---------------------------------------------------------------------------
# _async_check_home_sensor  (lines 298, 305)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_home_sensor_no_home_sensor(mock_hass):
    """Line 298: home_sensor is None → return False."""
    config = {}  # no CONF_HOME_SENSOR
    monitor = PresenceMonitor(mock_hass, "v1", config)
    result = await monitor._async_check_home_sensor()
    assert result is False


@pytest.mark.asyncio
async def test_check_home_sensor_no_state_obj(mock_hass):
    """Line 300: state_obj is None → return False."""
    config = {CONF_HOME_SENSOR: "binary_sensor.home"}
    monitor = PresenceMonitor(mock_hass, "v1", config)
    mock_hass.states.get = Mock(return_value=None)
    result = await monitor._async_check_home_sensor()
    assert result is False


@pytest.mark.asyncio
async def test_check_home_sensor_state_is_none(mock_hass):
    """Line 305: state is None → return False."""
    config = {CONF_HOME_SENSOR: "binary_sensor.home"}
    monitor = PresenceMonitor(mock_hass, "v1", config)
    mock_obj = Mock()
    mock_obj.state = None
    mock_hass.states.get = Mock(return_value=mock_obj)
    result = await monitor._async_check_home_sensor()
    assert result is False


# ---------------------------------------------------------------------------
# _async_check_home_coordinates  (lines 311, 314, 325)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_home_coords_no_home_coords(mock_hass):
    """Line 311: no home_coords → return False."""
    config = {CONF_HOME_SENSOR: "binary_sensor.home"}
    monitor = PresenceMonitor(mock_hass, "v1", config)
    # home_coords never set, stays None
    result = await monitor._async_check_home_coordinates()
    assert result is False


@pytest.mark.asyncio
async def test_check_home_coords_no_vehicle_coords_sensor(mock_hass):
    """Line 314: vehicle_coords_sensor is None → return True."""
    config = {CONF_HOME_COORDINATES: "[40.4168, -3.7038]"}
    monitor = PresenceMonitor(mock_hass, "v1", config)
    # home_coords parsed and set, vehicle_coords_sensor stays None
    result = await monitor._async_check_home_coordinates()
    assert result is True


@pytest.mark.asyncio
async def test_check_home_coords_invalid_vehicle_coords(mock_hass):
    """Line 325: vehicle_coords is falsy (parse failure) → return True."""
    config = {
        CONF_HOME_COORDINATES: "[40.4168, -3.7038]",
        CONF_VEHICLE_COORDINATES_SENSOR: "sensor.vehicle_coords",
    }
    monitor = PresenceMonitor(mock_hass, "v1", config)
    mock_obj = Mock()
    mock_obj.state = "not-coordinates"
    mock_hass.states.get = Mock(return_value=mock_obj)
    result = await monitor._async_check_home_coordinates()
    assert result is True


# ---------------------------------------------------------------------------
# _async_send_notification  (line 351)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_notification_no_service(mock_hass):
    """Line 351: no notification_service → return False."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.home",
        CONF_PLUGGED_SENSOR: "binary_sensor.plugged",
    }
    monitor = PresenceMonitor(mock_hass, "v1", config)
    result = await monitor._async_send_notification("title", "body")
    assert result is False


# ---------------------------------------------------------------------------
# _parse_coordinates  (lines 388, 391-392)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_coordinates_out_of_range(mock_hass):
    """Line 388: lat/lon out of valid range → return None."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "v1", config)
    result = monitor._parse_coordinates("[200.0, 10.0]")
    assert result is None


@pytest.mark.asyncio
async def test_parse_coordinates_value_error(mock_hass):
    """Line 391: ValueError on float() → return None."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "v1", config)
    # "abc,def" gives 2 parts (passes len check) but float() fails
    result = monitor._parse_coordinates("abc,def")
    assert result is None


# ---------------------------------------------------------------------------
# _async_handle_soc_change  (lines 432, 439-440)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soc_change_no_new_state(mock_hass):
    """Line 432: new_state is None → return early."""
    config = {CONF_SOC_SENSOR: "sensor.battery"}
    trip_mgr = AsyncMock()
    monitor = PresenceMonitor(mock_hass, "v1", config, trip_manager=trip_mgr)
    event = Mock()
    event.data = {"new_state": None}
    await monitor._async_handle_soc_change(event)
    trip_mgr._schedule.publish_deferrable_loads.assert_not_called()


@pytest.mark.asyncio
async def test_soc_change_non_numeric_state(mock_hass):
    """Lines 439-440: float(state.state) raises ValueError → return."""
    config = {CONF_SOC_SENSOR: "sensor.battery"}
    trip_mgr = AsyncMock()
    monitor = PresenceMonitor(mock_hass, "v1", config, trip_manager=trip_mgr)
    event = Mock()
    bad_state = Mock()
    bad_state.state = "unavailable"  # will be caught at line 434; need numeric but fails float
    event.data = {"old_state": Mock(state="50"), "new_state": bad_state}
    # State "unavailable" is caught at line 434, let's use "abc" which passes
    bad_state.state = "abc"
    await monitor._async_handle_soc_change(event)
    trip_mgr._schedule.publish_deferrable_loads.assert_not_called()

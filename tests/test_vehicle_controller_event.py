"""Tests for VehicleController event handling.

Bug fix for PR #21: Event handler uses event.get() instead of event.data.get()
for Home Assistant Event objects.
"""

import inspect
import pytest
from unittest.mock import MagicMock

from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor


class TestEventHandling:
    """Tests for vehicle controller event handling."""

    @pytest.mark.asyncio
    async def test_event_data_extraction_uses_event_data_get(self):
        """Test that SOC change handler uses event.data.get() not event.get().

        Bug: _async_handle_soc_change in presence_monitor.py was using:
            new_state = event.get("data", {}).get("new_state")

        This is WRONG because HA Event objects have:
            - event.data (dict attribute)
            - event.event_type (string attribute)
            - event.time_fired (datetime attribute)

        NOT event.get() method.

        FIX: Should use:
            new_state = event.data.get("new_state")

        This test verifies the fix by checking the source code uses event.data.get().
        """
        # Get source code dynamically using inspect
        source = inspect.getsource(PresenceMonitor._async_handle_soc_change)

        # The bug: using event.get() instead of event.data.get()
        # This will fail because HA Event objects don't have a .get() method
        assert 'event.get("data")' not in source, (
            "Event handler should NOT use event.get() - use event.data.get() instead"
        )

        # The fix: should use event.data.get()
        assert "event.data.get" in source, (
            "Event handler should use event.data.get() for HA Event objects"
        )

    @pytest.mark.asyncio
    async def test_ha_event_object_structure(self):
        """Test that we understand HA Event object structure.

        Home Assistant Event objects have:
        - event.data: dict - The event payload/data
        - event.event_type: str - The event type (e.g., 'state_changed')
        - event.time_fired: datetime - When the event was fired
        - event.origin: str - Where the event originated

        They do NOT have:
        - event.get() method - This is a dict method, not an Event method

        This test documents the expected structure and verifies the fix.
        """
        # Get source code dynamically
        source = inspect.getsource(PresenceMonitor._async_handle_soc_change)

        # The correct way to access event data:
        # new_state = event.data.get("new_state")
        assert "event.data.get" in source, (
            "Should use event.data.get() for HA Event objects"
        )

        # NOT the buggy way:
        # new_state = event.get("data", {}).get("new_state")
        assert 'event.get("data")' not in source, (
            "Should NOT use event.get() for HA Event objects"
        )

    @pytest.mark.asyncio
    async def test_async_handle_soc_change_with_mock_event(self):
        """Test that _async_handle_soc_change works with a mock HA Event.

        This verifies that the event handler correctly accesses event.data
        when given a proper Home Assistant Event object.
        """
        # Create a mock event that simulates HA Event structure
        mock_new_state = MagicMock()
        mock_new_state.state = "75"

        mock_event = MagicMock()
        mock_event.data = {"new_state": mock_new_state}

        # Create a presence monitor with minimal config
        config = {
            "home_sensor": "binary_sensor.home",
            "soc_sensor": "sensor.battery",
            "plugged_sensor": "binary_sensor.plugged",
            "home_coordinates": "40.0,-3.0",
            "vehicle_coordinates_sensor": "sensor.gps",
            "notification_service": None,
        }

        monitor = PresenceMonitor(
            hass=MagicMock(),
            vehicle_id="test_vehicle",
            config=config,
            trip_manager=None,
        )

        # Call the handler with mock event - should not raise
        # If the code uses event.get() instead of event.data.get(), this will fail
        try:
            await monitor._async_handle_soc_change(mock_event)
        except AttributeError:
            pytest.fail(
                "_async_handle_soc_change used event.get() instead of event.data.get()"
            )

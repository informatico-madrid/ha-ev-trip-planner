"""Tests for VehicleController event handling.

Bug fix for PR #21: Event handler uses event.get() instead of event.data.get()
for Home Assistant Event objects.
"""

import pytest


class TestEventHandling:
    """Tests for vehicle controller event handling."""

    @pytest.mark.asyncio
    async def test_event_data_extraction_uses_event_data_get(self):
        """Test that SOC change handler uses event.data.get() not event.get().

        Bug: _async_handle_soc_change in presence_monitor.py uses:
            new_state = event.get("data", {}).get("new_state")

        This is WRONG because HA Event objects have:
            - event.data (dict attribute)
            - event.event_type (string attribute)
            - event.time_fired (datetime attribute)

        NOT event.get() method.

        FIX: Should use:
            new_state = event.data.get("new_state")

        RED: This test will fail until the bug is fixed.
        """
        # Read the source code to verify the bug exists
        with open(
            "/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/"
            "custom_components/ev_trip_planner/presence_monitor.py",
            "r"
        ) as f:
            content = f.read()

        # The bug: using event.get() instead of event.data.get()
        # This will fail because HA Event objects don't have a .get() method
        assert 'event.get("data"' not in content, \
            "Event handler should NOT use event.get() - use event.data.get() instead"

        # The fix: should use event.data.get()
        assert 'event.data.get' in content, \
            "Event handler should use event.data.get() for HA Event objects"

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

        This test documents the expected structure.
        """
        # Verify the Event class structure by checking HA documentation
        # Home Assistant core: HomeAssistant.core.Event
        # https://developers.home-assistant.io/docs/core/events

        # The correct way to access event data:
        # new_state = event.data.get("new_state")

        # NOT the buggy way:
        # new_state = event.get("data", {}).get("new_state")
        # This fails because Event objects don't have a .get() method

        # This assertion documents the expected fix
        expected_fix = 'event.data.get("new_state")'
        buggy_code = 'event.get("data"'

        # We'll verify this by reading the source file
        with open(
            "/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/"
            "custom_components/ev_trip_planner/presence_monitor.py",
            "r"
        ) as f:
            content = f.read()

        # The fix should use event.data.get()
        assert 'event.data.get' in content, \
            "Should use event.data.get() for HA Event objects"

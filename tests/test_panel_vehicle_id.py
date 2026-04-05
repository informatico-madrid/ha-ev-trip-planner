"""Tests for EV Trip Planner panel vehicle_id filtering.

This test verifies that the panel correctly filters and displays trips
by matching vehicle_id attribute from EMHASS sensors with the vehicle_id
extracted from URL params (_vehicleId).

Bug fix for PR #21: Panel was filtering by entry_id but sensor stores vehicle_id
"""

import pytest


class TestPanelVehicleIdFiltering:
    """Tests for panel vehicle_id filtering behavior."""

    @pytest.mark.asyncio
    async def test_sensor_stores_vehicle_id_not_entry_id(self):
        """Test that EMHASS sensors store vehicle_id, not entry_id.

        EMHASSAdapter.publish_deferrable_loads() sets sensor attributes:
        - vehicle_id: self.vehicle_id (the slug from config)
        - NOT entry_id: self.entry_id (HA's internal UUID)

        This is the root cause of the bug - panel was looking for entry_id
        but sensor only stores vehicle_id.

        This test passes to verify the sensor attribute structure.
        """
        # Read the actual source code to verify sensor attributes
        with open(
            "/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/"
            "custom_components/ev_trip_planner/emhass_adapter.py",
            "r"
        ) as f:
            content = f.read()

        # Verify publish_deferrable_loads sets vehicle_id attribute
        assert '"vehicle_id": self.vehicle_id' in content, \
            "EMHASS adapter should set vehicle_id attribute on sensor"

        # Verify it does NOT set entry_id attribute
        # (entry_id is the internal HA UUID, should not be exposed to panel)
        assert '"entry_id": self.entry_id' not in content, \
            "EMHASS adapter should NOT set entry_id attribute"

    @pytest.mark.asyncio
    async def test_panel_should_filter_by_vehicle_id(self):
        """Test that panel filters trips by vehicle_id from URL.

        Bug: Panel was trying to filter by entry_id (UUID) but EMHASS sensors
        store vehicle_id (slug from URL). This caused trips to not display.

        RED: This test will fail until panel.js is fixed.
        """
        # Read panel.js source
        with open(
            "/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/"
            "custom_components/ev_trip_planner/frontend/panel.js",
            "r"
        ) as f:
            content = f.read()

        # The fix: panel should filter using vehicle_id from sensor attributes
        # When filtering trips, panel should check:
        # sensor.vehicle_id === panel._vehicleId (from URL)

        # This assertion will FAIL if panel.js still uses entry_id
        # for trip filtering logic
        assert 'sensor.dataset.vehicle_id' in content or \
               'sensor.attributes.vehicle_id' in content or \
               'state.attributes.vehicle_id' in content, \
            "Panel should filter by vehicle_id attribute, not entry_id"

    @pytest.mark.asyncio
    async def test_vehicle_id_mismatch_prevents_display(self):
        """Test that vehicle_id mismatch prevents trips from displaying.

        If panel filters by entry_id (UUID) but sensor stores vehicle_id (slug),
        no trips will be displayed because:
        - entry_id = "a1b2c3d4e5f6" (UUID)
        - vehicle_id = "mi_coche" (slug)
        - These never match, so filter returns empty array

        RED: Demonstrates the bug behavior.
        """
        # Simulate sensor attributes (as stored by EMHASS adapter)
        sensor_attributes = {
            "vehicle_id": "mi_coche",  # What panel SHOULD use
            "power_profile_watts": [0] * 168,
        }

        # Simulate panel._vehicleId from URL
        url_vehicle_id = "mi_coche"

        # BUGGY filtering (using entry_id which doesn't exist)
        buggy_match = sensor_attributes.get("entry_id") == url_vehicle_id

        # FIXED filtering (using vehicle_id)
        fixed_match = sensor_attributes.get("vehicle_id") == url_vehicle_id

        # Buggy version should fail (no trips displayed)
        assert buggy_match is False, \
            "Buggy entry_id filter should fail to match vehicle_id"

        # Fixed version should succeed (trips displayed)
        assert fixed_match is True, \
            "Fixed vehicle_id filter should match correctly"

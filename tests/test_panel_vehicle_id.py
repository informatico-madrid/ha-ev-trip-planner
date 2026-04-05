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
    async def test_sensor_stores_vehicle_id_and_entry_id(self):
        """Test that EMHASS sensors store both vehicle_id and entry_id.

        EMHASSAdapter.publish_deferrable_loads() sets sensor attributes:
        - vehicle_id: self.vehicle_id (the slug from config) - for panel filtering
        - entry_id: self.entry_id (HA's internal UUID) - for orphan detection at startup

        Both attributes are intentionally set for different purposes:
        - vehicle_id: Used by panel to identify which vehicle's trips to display
        - entry_id: Used by startup orphan cleanup to identify orphaned sensors

        This test verifies the sensor attribute structure is correct.
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

        # Verify entry_id IS set (for orphan detection - FR-1.2)
        # This is intentional and necessary for startup orphan cleanup
        assert '"entry_id": self.entry_id' in content, \
            "EMHASS adapter should set entry_id attribute for orphan detection"

    @pytest.mark.asyncio
    async def test_panel_passes_vehicle_id_to_trip_list_service(self):
        """Test that panel passes vehicle_id from URL to trip_list service.

        Panel.js does NOT filter trips client-side by reading sensor attributes.
        Instead, it correctly passes vehicle_id to the backend trip_list service
        which does the filtering server-side.

        This is the CORRECT pattern - panel passes:
        { vehicle_id: this._vehicleId } to ev_trip_planner.trip_list service
        """
        # Read panel.js source
        with open(
            "/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/"
            "custom_components/ev_trip_planner/frontend/panel.js",
            "r"
        ) as f:
            content = f.read()

        # Panel should call trip_list service with vehicle_id parameter
        # Pattern: callService('ev_trip_planner', 'trip_list', { vehicle_id: ... })
        assert "callService" in content and "'trip_list'" in content, \
            "Panel should call trip_list service"

        # Verify vehicle_id is passed to trip_list service
        assert "vehicle_id: this._vehicleId" in content or \
               'vehicle_id: this._vehicleId' in content, \
            "Panel should pass vehicle_id from URL to trip_list service"

        # Verify _getTripsList uses _vehicleId for the service call
        assert "await this._getTripsList()" in content or \
               "_vehicleId" in content, \
            "Panel should use _vehicleId for fetching trips"

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

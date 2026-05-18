"""Test that vehicle package re-exports 3 public names.

During SOLID decomposition, the vehicle_controller.py god module will be
reorganized into a vehicle/ package. Test verifies import paths exist.
"""

from __future__ import annotations


class TestVehicleModuleExports:
    """Verify vehicle package re-exports vehicle functions."""

    def test_vehicle_controller_importable(self):
        """VehicleController must be importable from vehicle."""
        from custom_components.ev_trip_planner.vehicle import (
            VehicleController,
        )

        assert VehicleController is not None

    def test_vehicle_control_strategy_importable(self):
        """VehicleControlStrategy must be importable from vehicle."""
        from custom_components.ev_trip_planner.vehicle import (
            VehicleControlStrategy,
        )

        assert VehicleControlStrategy is not None

    def test_create_control_strategy_importable(self):
        """create_control_strategy must be importable from vehicle."""
        from custom_components.ev_trip_planner.vehicle import (
            create_control_strategy,
        )

        assert callable(create_control_strategy)

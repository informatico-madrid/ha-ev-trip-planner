"""Test that vehicle.controller module exports VehicleController.

VERIFIES: VehicleController and create_control_strategy are importable
"""

from custom_components.ev_trip_planner.vehicle.controller import (
    VehicleController,
    create_control_strategy,
)
from custom_components.ev_trip_planner.vehicle.strategy import (
    VehicleControlStrategy,
)


class TestVehicleControllerModule:
    """Verify vehicle.controller exports."""

    def test_vehicle_controller_class(self):
        """VehicleController must be importable."""
        assert VehicleController is not None

    def test_create_control_strategy_callable(self):
        """create_control_strategy must be callable."""
        assert callable(create_control_strategy)

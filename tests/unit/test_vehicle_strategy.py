"""Test that vehicle.strategy module exports strategy classes.

VERIFIES: VehicleControlStrategy ABC has 3 abstract methods
"""

from abc import ABC

from custom_components.ev_trip_planner.vehicle.strategy import (
    HomeAssistantWrapper,
    RetryState,
    ServiceStrategy,
    SwitchStrategy,
    VehicleControlStrategy,
)


class TestVehicleStrategyModule:
    """Verify vehicle.strategy exports."""

    def test_vehicle_control_strategy_is_abstract(self):
        """VehicleControlStrategy must be an ABC."""
        assert issubclass(VehicleControlStrategy, ABC)

    def test_vehicle_control_strategy_has_abstract_methods(self):
        """VehicleControlStrategy must define 3 abstract methods."""
        abstract_methods = getattr(
            VehicleControlStrategy, "__abstractmethods__", set()
        )
        expected = {"async_activate", "async_deactivate", "async_get_status"}
        assert expected.issubset(abstract_methods)

    def test_switch_strategy_subclass(self):
        """SwitchStrategy must subclass VehicleControlStrategy."""
        assert issubclass(SwitchStrategy, VehicleControlStrategy)

    def test_service_strategy_subclass(self):
        """ServiceStrategy must subclass VehicleControlStrategy."""
        assert issubclass(ServiceStrategy, VehicleControlStrategy)

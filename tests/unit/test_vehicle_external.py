"""Test that vehicle.external module exports external strategies.

VERIFIES: ScriptStrategy and ExternalStrategy are importable
"""

from custom_components.ev_trip_planner.vehicle.external import (
    ExternalStrategy,
    ScriptStrategy,
)
from custom_components.ev_trip_planner.vehicle.strategy import (
    VehicleControlStrategy,
)


class TestVehicleExternalModule:
    """Verify vehicle.external exports."""

    def test_script_strategy_subclass(self):
        """ScriptStrategy must subclass VehicleControlStrategy."""
        assert issubclass(ScriptStrategy, VehicleControlStrategy)

    def test_external_strategy_subclass(self):
        """ExternalStrategy must subclass VehicleControlStrategy."""
        assert issubclass(ExternalStrategy, VehicleControlStrategy)

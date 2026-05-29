"""Tests for IndexManager in emhass.index_manager."""

import pytest  # noqa: F401


class TestIndexManagerExists:
    """Test that IndexManager class exists in emhass.index_manager module."""

    def test_index_manager_importable(self):
        """IndexManager can be imported from emhass.index_manager."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        assert IndexManager is not None


# ---------------------------------------------------------------------------
# Default parameter value tests — kill mutations on IndexManager.__init__ defaults
#
# Mutations that survive (unregistered, caused by __init__ deduplication):
#   mutmut_1: max_deferrable_loads=50 -> 51
#   mutmut_2: cooldown_hours=24 -> 25
#
# Tests instantiate IndexManager() with NO arguments and check the stored
# default values directly.
# ---------------------------------------------------------------------------


class TestIndexManagerDefaultValues:
    """Kill default-parameter mutations on IndexManager.__init__.

    Mutants change:
    - max_deferrable_loads: 50 → 51
    - cooldown_hours: 24 → 25

    Creating IndexManager() with no args and checking _max_deferrable_loads
    and _index_cooldown_hours will fail if the defaults were mutated.
    """

    def test_default_max_deferrable_loads_is_50(self):
        """Default max_deferrable_loads must be 50.

        Kills mutmut_1: max_deferrable_loads=50 -> max_deferrable_loads=51.
        """
        from custom_components.ev_trip_planner.emhass.index_manager import IndexManager

        mgr = IndexManager()
        assert mgr._max_deferrable_loads == 50, (
            f"Expected _max_deferrable_loads=50, got {mgr._max_deferrable_loads}"
        )

    def test_default_cooldown_hours_is_24(self):
        """Default cooldown_hours must be 24.

        Kills mutmut_2: cooldown_hours=24 -> cooldown_hours=25.
        """
        from custom_components.ev_trip_planner.emhass.index_manager import IndexManager

        mgr = IndexManager()
        assert mgr._index_cooldown_hours == 24, (
            f"Expected _index_cooldown_hours=24, got {mgr._index_cooldown_hours}"
        )

    def test_default_values_together(self):
        """Both defaults correct when instantiated with no arguments."""
        from custom_components.ev_trip_planner.emhass.index_manager import IndexManager

        mgr = IndexManager()
        assert mgr._max_deferrable_loads == 50
        assert mgr._index_cooldown_hours == 24

    def test_custom_max_deferrable_loads_overrides_default(self):
        """Explicitly passing max_deferrable_loads overrides the default.

        Ensures the default check is not accidentally testing the explicit arg.
        """
        from custom_components.ev_trip_planner.emhass.index_manager import IndexManager

        mgr = IndexManager(max_deferrable_loads=10)
        assert mgr._max_deferrable_loads == 10

    def test_custom_cooldown_hours_overrides_default(self):
        """Explicitly passing cooldown_hours overrides the default."""
        from custom_components.ev_trip_planner.emhass.index_manager import IndexManager

        mgr = IndexManager(cooldown_hours=48)
        assert mgr._index_cooldown_hours == 48

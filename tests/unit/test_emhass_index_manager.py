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

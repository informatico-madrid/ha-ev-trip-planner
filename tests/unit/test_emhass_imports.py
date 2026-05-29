"""Test: emhass package re-exports EMHASSAdapter.

RED phase — this test must FAIL because the emhass/ package does not exist yet.
The package will be created in a subsequent GREEN task.
"""

import pytest  # noqa: F401


class TestEmhassPackageImports:
    """Verify EMHASSAdapter is importable from the emhass package."""

    def test_emhass_adapter_importable_from_package(self):
        """EMHASSAdapter must be importable from custom_components.ev_trip_planner.emhass.adapter."""
        from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

        assert callable(EMHASSAdapter)
        assert isinstance(EMHASSAdapter, type)

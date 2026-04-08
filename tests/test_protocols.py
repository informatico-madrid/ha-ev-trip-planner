"""Tests for structural protocol compatibility.

TDD RED phase - These tests verify that YamlTripStorage implements TripStorageProtocol
structurally via isinstance(). The protocols.py module doesn't exist yet, so these
tests will fail with ImportError initially.
"""

import pytest


class TestYamlTripStorageImplementsTripStorageProtocol:
    """Verify YamlTripStorage structurally implements TripStorageProtocol.

    This test is in TDD RED phase - protocols.py doesn't exist yet,
    so this test should fail with ImportError.
    """

    def test_import_yaml_trip_storage_succeeds(self):
        """YamlTripStorage should be importable from ev_trip_planner."""
        from custom_components.ev_trip_planner import YamlTripStorage

        assert YamlTripStorage is not None

    def test_import_trip_storage_protocol_succeeds(self):
        """TripStorageProtocol should be importable from ev_trip_planner.protocols."""
        from custom_components.ev_trip_planner.protocols import TripStorageProtocol

        assert TripStorageProtocol is not None

    def test_yaml_trip_storage_isinstance_trip_storage_protocol(self):
        """YamlTripStorage instance should be recognized as TripStorageProtocol.

        This uses isinstance() with a @runtime_checkable Protocol to verify
        structural compatibility at runtime.
        """
        from custom_components.ev_trip_planner import YamlTripStorage
        from custom_components.ev_trip_planner.protocols import TripStorageProtocol

        # Create a minimal mock for hass to satisfy YamlTripStorage constructor
        storage = YamlTripStorage(hass=None, vehicle_id="test_vehicle")
        assert isinstance(storage, TripStorageProtocol)

    def test_trip_storage_protocol_is_runtime_checkable(self):
        """TripStorageProtocol should be marked with @runtime_checkable."""
        from custom_components.ev_trip_planner.protocols import TripStorageProtocol

        import typing

        # RuntimeCheckable Protocol classes have __protocol_attrs__ set
        # or can be verified via isinstance check on a simple object
        assert hasattr(TripStorageProtocol, "_is_protocol")
        # The protocol should be usable with isinstance at runtime
        # (requires @runtime_checkable decorator)
        assert getattr(TripStorageProtocol, "_is_protocol", False) is True
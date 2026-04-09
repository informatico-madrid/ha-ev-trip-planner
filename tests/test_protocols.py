"""Tests for structural protocol compatibility.

These tests verify that YamlTripStorage implements TripStorageProtocol
and EMHASSAdapter implements EMHASSPublisherProtocol structurally via isinstance().
"""


from unittest.mock import MagicMock
from pathlib import Path


class TestYamlTripStorageImplementsTripStorageProtocol:
    """Verify YamlTripStorage (real class) implements TripStorageProtocol.

    T029.1-T029.4: Replace local stub with actual YamlTripStorage import.
    """

    def test_import_yaml_trip_storage_succeeds(self):
        """YamlTripStorage should be importable from ev_trip_planner.yaml_trip_storage."""
        from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage

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
        from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage
        from custom_components.ev_trip_planner.protocols import TripStorageProtocol

        # Create a mock hass and use the real YamlTripStorage constructor
        mock_hass = MagicMock()
        mock_hass.config = MagicMock()
        mock_hass.config.config_dir = Path("/tmp/test")

        storage = YamlTripStorage(mock_hass, vehicle_id="test_vehicle")
        assert isinstance(storage, TripStorageProtocol), (
            "YamlTripStorage does not implement TripStorageProtocol"
        )

    def test_trip_storage_protocol_is_runtime_checkable(self):
        """TripStorageProtocol should be marked with @runtime_checkable."""
        from custom_components.ev_trip_planner.protocols import TripStorageProtocol

        # Verify it's actually runtime_checkable
        assert hasattr(TripStorageProtocol, '__protocol_attrs__')
        # The decorator should make it behave correctly with isinstance()
        # This is verified by the previous test passing


class TestEMHASSPublisherAdapterImplementsEMHASSPublisherProtocol:
    """Verify EMHASSAdapter implements EMHASSPublisherProtocol structurally.

    T029.3-T029.4: Test EMHASSPublisherProtocol isinstance checks.
    """

    def test_emhass_adapter_import_succeeds(self):
        """EMHASSAdapter should be importable."""
        from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter

        assert EMHASSAdapter is not None

    def test_emhass_publisher_protocol_import_succeeds(self):
        """EMHASSPublisherProtocol should be importable."""
        from custom_components.ev_trip_planner.protocols import EMHASSPublisherProtocol

        assert EMHASSPublisherProtocol is not None

    def test_emhass_adapter_isinstance_emhass_publisher_protocol(self):
        """EMHASSAdapter instance should be recognized as EMHASSPublisherProtocol.

        Uses isinstance() with @runtime_checkable Protocol to verify
        structural compatibility at runtime.
        """
        from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
        from custom_components.ev_trip_planner.protocols import EMHASSPublisherProtocol

        # Create a mock hass and entry
        mock_hass = MagicMock()
        mock_entry = MagicMock()

        adapter = EMHASSAdapter(mock_hass, mock_entry)
        assert isinstance(adapter, EMHASSPublisherProtocol), (
            "EMHASSAdapter does not implement EMHASSPublisherProtocol"
        )

    def test_emhass_publisher_protocol_is_runtime_checkable(self):
        """EMHASSPublisherProtocol should be marked with @runtime_checkable."""
        from custom_components.ev_trip_planner.protocols import EMHASSPublisherProtocol

        # Verify it's actually runtime_checkable
        assert hasattr(EMHASSPublisherProtocol, '__protocol_attrs__')
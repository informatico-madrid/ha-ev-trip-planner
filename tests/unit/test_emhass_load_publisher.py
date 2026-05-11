"""Red test: LoadPublisher class must exist in emhass.load_publisher."""

from custom_components.ev_trip_planner.emhass.load_publisher import LoadPublisher


class TestLoadPublisherExists:
    """LoadPublisher must be importable from emhass.load_publisher."""

    def test_load_publisher_importable(self):
        """LoadPublisher class is importable from emhass.load_publisher."""
        assert LoadPublisher is not None

    def test_load_publisher_has_publish_method(self):
        """LoadPublisher must have a publish method."""
        assert hasattr(LoadPublisher, "publish")

    def test_load_publisher_has_update_method(self):
        """LoadPublisher must have an update method."""
        assert hasattr(LoadPublisher, "update")

    def test_load_publisher_has_remove_method(self):
        """LoadPublisher must have a remove method."""
        assert hasattr(LoadPublisher, "remove")

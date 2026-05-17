"""[RED] Test: TripCRUD, TripLifecycle, TripPersistence have expected methods.

Verifies the new composition classes expose the full set of CRUD and lifecycle
methods. async_setup lives on TripPersistence (the persistence sub-component).
"""

import unittest


class TestTripCRUD(unittest.TestCase):
    """TripCRUD must be importable from trip._crud with expected methods."""

    def test_crud_is_importable(self):
        """TripCRUD can be imported from custom_components.ev_trip_planner.trip._crud."""
        from custom_components.ev_trip_planner.trip._crud import TripCRUD

        self.assertIsNotNone(TripCRUD)

    def test_has_async_add_recurring_trip(self):
        from custom_components.ev_trip_planner.trip._crud import TripCRUD

        self.assertTrue(hasattr(TripCRUD, "async_add_recurring_trip"))
        self.assertTrue(callable(getattr(TripCRUD, "async_add_recurring_trip")))

    def test_has_async_update_trip(self):
        from custom_components.ev_trip_planner.trip._crud import TripCRUD

        self.assertTrue(hasattr(TripCRUD, "async_update_trip"))
        self.assertTrue(callable(getattr(TripCRUD, "async_update_trip")))

    def test_has_async_delete_trip(self):
        from custom_components.ev_trip_planner.trip._crud import TripCRUD

        self.assertTrue(hasattr(TripCRUD, "async_delete_trip"))
        self.assertTrue(callable(getattr(TripCRUD, "async_delete_trip")))


class TestTripLifecycle(unittest.TestCase):
    """TripLifecycle must be importable from trip._trip_lifecycle with expected methods."""

    def test_lifecycle_is_importable(self):
        """TripLifecycle can be imported from trip._trip_lifecycle."""
        from custom_components.ev_trip_planner.trip._trip_lifecycle import TripLifecycle

        self.assertIsNotNone(TripLifecycle)

    def test_has_async_pause_recurring_trip(self):
        from custom_components.ev_trip_planner.trip._trip_lifecycle import TripLifecycle

        self.assertTrue(hasattr(TripLifecycle, "async_pause_recurring_trip"))
        self.assertTrue(callable(getattr(TripLifecycle, "async_pause_recurring_trip")))

    def test_has_async_resume_recurring_trip(self):
        from custom_components.ev_trip_planner.trip._trip_lifecycle import TripLifecycle

        self.assertTrue(hasattr(TripLifecycle, "async_resume_recurring_trip"))
        self.assertTrue(callable(getattr(TripLifecycle, "async_resume_recurring_trip")))

    def test_has_async_complete_punctual_trip(self):
        from custom_components.ev_trip_planner.trip._trip_lifecycle import TripLifecycle

        self.assertTrue(hasattr(TripLifecycle, "async_complete_punctual_trip"))
        self.assertTrue(
            callable(getattr(TripLifecycle, "async_complete_punctual_trip"))
        )

    def test_has_async_cancel_punctual_trip(self):
        from custom_components.ev_trip_planner.trip._trip_lifecycle import TripLifecycle

        self.assertTrue(hasattr(TripLifecycle, "async_cancel_punctual_trip"))
        self.assertTrue(callable(getattr(TripLifecycle, "async_cancel_punctual_trip")))


class TestTripPersistence(unittest.TestCase):
    """TripPersistence must be importable from trip._persistence with expected methods."""

    def test_persistence_is_importable(self):
        """TripPersistence can be imported from trip._persistence."""
        from custom_components.ev_trip_planner.trip._persistence import TripPersistence

        self.assertIsNotNone(TripPersistence)

    def test_has_async_setup(self):
        from custom_components.ev_trip_planner.trip._persistence import TripPersistence

        self.assertTrue(hasattr(TripPersistence, "async_setup"))
        self.assertTrue(callable(getattr(TripPersistence, "async_setup")))


if __name__ == "__main__":
    unittest.main()

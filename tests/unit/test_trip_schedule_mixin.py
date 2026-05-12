"""[RED] Test: TripScheduler has schedule generation.

Verifies TripScheduler is importable from trip._schedule
and exposes async_generate_deferrables_schedule and publish_deferrable_loads.
"""

import unittest


class TestScheduleMixin(unittest.TestCase):
    """TripScheduler must be importable from trip._schedule with expected methods."""

    def test_schedule_mixin_is_importable(self):
        """TripScheduler can be imported from custom_components.ev_trip_planner.trip._schedule."""
        from custom_components.ev_trip_planner.trip._schedule import TripScheduler

        self.assertIsNotNone(TripScheduler)

    def test_has_async_generate_deferrables_schedule(self):
        from custom_components.ev_trip_planner.trip._schedule import TripScheduler

        self.assertTrue(hasattr(TripScheduler, "async_generate_deferrables_schedule"))
        self.assertTrue(
            callable(getattr(TripScheduler, "async_generate_deferrables_schedule"))
        )

    def test_has_publish_deferrable_loads(self):
        from custom_components.ev_trip_planner.trip._schedule import TripScheduler

        self.assertTrue(hasattr(TripScheduler, "publish_deferrable_loads"))
        self.assertTrue(callable(getattr(TripScheduler, "publish_deferrable_loads")))


if __name__ == "__main__":
    unittest.main()

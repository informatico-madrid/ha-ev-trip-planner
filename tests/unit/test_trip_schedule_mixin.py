"""[RED] Test: _ScheduleMixin has schedule generation.

Verifies _ScheduleMixin is importable from trip._schedule_mixin
and exposes async_generate_deferrables_schedule and publish_deferrable_loads.
"""

import unittest


class TestScheduleMixin(unittest.TestCase):
    """_ScheduleMixin must be importable from trip._schedule_mixin with expected methods."""

    def test_schedule_mixin_is_importable(self):
        """_ScheduleMixin can be imported from custom_components.ev_trip_planner.trip._schedule_mixin."""
        from custom_components.ev_trip_planner.trip._schedule_mixin import _ScheduleMixin

        self.assertIsNotNone(_ScheduleMixin)

    def test_has_async_generate_deferrables_schedule(self):
        from custom_components.ev_trip_planner.trip._schedule_mixin import _ScheduleMixin

        self.assertTrue(hasattr(_ScheduleMixin, "async_generate_deferrables_schedule"))
        self.assertTrue(callable(getattr(_ScheduleMixin, "async_generate_deferrables_schedule")))

    def test_has_publish_deferrable_loads(self):
        from custom_components.ev_trip_planner.trip._schedule_mixin import _ScheduleMixin

        self.assertTrue(hasattr(_ScheduleMixin, "publish_deferrable_loads"))
        self.assertTrue(callable(getattr(_ScheduleMixin, "publish_deferrable_loads")))


if __name__ == "__main__":
    unittest.main()

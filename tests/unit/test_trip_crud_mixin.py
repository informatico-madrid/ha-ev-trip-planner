"""[RED] Test: _CRUDMixin class has CRUD operations.

Verifies _CRUDMixin is importable from trip._crud_mixin and exposes
the full set of CRUD lifecycle methods.
"""

import unittest


class TestCRUDMixin(unittest.TestCase):
    """_CRUDMixin must be importable from trip._crud_mixin with expected methods."""

    def test_crud_mixin_is_importable(self):
        """_CRUDMixin can be imported from custom_components.ev_trip_planner.trip._crud_mixin."""
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertIsNotNone(_CRUDMixin)

    def test_has_async_setup(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertTrue(hasattr(_CRUDMixin, "async_setup"))
        self.assertTrue(callable(getattr(_CRUDMixin, "async_setup")))

    def test_has_async_add_recurring_trip(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertTrue(hasattr(_CRUDMixin, "async_add_recurring_trip"))
        self.assertTrue(callable(getattr(_CRUDMixin, "async_add_recurring_trip")))

    def test_has_async_update_trip(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertTrue(hasattr(_CRUDMixin, "async_update_trip"))
        self.assertTrue(callable(getattr(_CRUDMixin, "async_update_trip")))

    def test_has_async_delete_trip(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertTrue(hasattr(_CRUDMixin, "async_delete_trip"))
        self.assertTrue(callable(getattr(_CRUDMixin, "async_delete_trip")))

    def test_has_async_pause_recurring_trip(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertTrue(hasattr(_CRUDMixin, "async_pause_recurring_trip"))
        self.assertTrue(callable(getattr(_CRUDMixin, "async_pause_recurring_trip")))

    def test_has_async_resume_recurring_trip(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertTrue(hasattr(_CRUDMixin, "async_resume_recurring_trip"))
        self.assertTrue(callable(getattr(_CRUDMixin, "async_resume_recurring_trip")))

    def test_has_async_complete_punctual_trip(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertTrue(hasattr(_CRUDMixin, "async_complete_punctual_trip"))
        self.assertTrue(callable(getattr(_CRUDMixin, "async_complete_punctual_trip")))

    def test_has_async_cancel_punctual_trip(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertTrue(hasattr(_CRUDMixin, "async_cancel_punctual_trip"))
        self.assertTrue(callable(getattr(_CRUDMixin, "async_cancel_punctual_trip")))


if __name__ == "__main__":
    unittest.main()

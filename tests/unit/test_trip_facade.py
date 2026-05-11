"""[RED] Test: TripManager facade class delegates to mixins.

Verifies TripManager is composed of _CRUDMixin, _SOCMixin,
_PowerProfileMixin, _ScheduleMixin and has EMHASS adapter setter/getter.
"""

import unittest


class TestTripManagerFacade(unittest.TestCase):
    """TripManager facade must delegate to mixins and expose EMHASS adapter."""

    def test_trip_manager_importable_from_manager(self):
        """TripManager can be imported from custom_components.ev_trip_planner.trip.manager."""
        from custom_components.ev_trip_planner.trip.manager import TripManager

        self.assertIsNotNone(TripManager)

    def test_crud_mixin_is_importable(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin

        self.assertIsNotNone(_CRUDMixin)

    def test_soc_mixin_is_importable(self):
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin

        self.assertIsNotNone(_SOCMixin)

    def test_power_profile_mixin_is_importable(self):
        from custom_components.ev_trip_planner.trip._power_profile_mixin import _PowerProfileMixin

        self.assertIsNotNone(_PowerProfileMixin)

    def test_schedule_mixin_is_importable(self):
        from custom_components.ev_trip_planner.trip._schedule_mixin import _ScheduleMixin

        self.assertIsNotNone(_ScheduleMixin)

    def test_trip_manager_inherits_from_crud_mixin(self):
        from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin
        from custom_components.ev_trip_planner.trip.manager import TripManager

        self.assertTrue(issubclass(TripManager, _CRUDMixin))

    def test_trip_manager_inherits_from_soc_mixin(self):
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin
        from custom_components.ev_trip_planner.trip.manager import TripManager

        self.assertTrue(issubclass(TripManager, _SOCMixin))

    def test_trip_manager_inherits_from_power_profile_mixin(self):
        from custom_components.ev_trip_planner.trip._power_profile_mixin import _PowerProfileMixin
        from custom_components.ev_trip_planner.trip.manager import TripManager

        self.assertTrue(issubclass(TripManager, _PowerProfileMixin))

    def test_trip_manager_inherits_from_schedule_mixin(self):
        from custom_components.ev_trip_planner.trip._schedule_mixin import _ScheduleMixin
        from custom_components.ev_trip_planner.trip.manager import TripManager

        self.assertTrue(issubclass(TripManager, _ScheduleMixin))

    def test_has_set_emhass_adapter(self):
        from custom_components.ev_trip_planner.trip.manager import TripManager

        self.assertTrue(hasattr(TripManager, "set_emhass_adapter"))
        self.assertTrue(callable(getattr(TripManager, "set_emhass_adapter")))

    def test_has_get_emhass_adapter(self):
        from custom_components.ev_trip_planner.trip.manager import TripManager

        self.assertTrue(hasattr(TripManager, "get_emhass_adapter"))
        self.assertTrue(callable(getattr(TripManager, "get_emhass_adapter")))


if __name__ == "__main__":
    unittest.main()

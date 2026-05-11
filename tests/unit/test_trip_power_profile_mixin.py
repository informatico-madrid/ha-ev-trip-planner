"""[RED] Test: _PowerProfileMixin has power profile generation.

Verifies _PowerProfileMixin is importable from trip._power_profile_mixin
and exposes async_generate_power_profile.
"""

import unittest


class TestPowerProfileMixin(unittest.TestCase):
    """_PowerProfileMixin must be importable from trip._power_profile_mixin."""

    def test_power_profile_mixin_is_importable(self):
        """_PowerProfileMixin can be imported from custom_components.ev_trip_planner.trip._power_profile_mixin."""
        from custom_components.ev_trip_planner.trip._power_profile_mixin import _PowerProfileMixin

        self.assertIsNotNone(_PowerProfileMixin)

    def test_has_async_generate_power_profile(self):
        from custom_components.ev_trip_planner.trip._power_profile_mixin import _PowerProfileMixin

        self.assertTrue(hasattr(_PowerProfileMixin, "async_generate_power_profile"))
        self.assertTrue(callable(getattr(_PowerProfileMixin, "async_generate_power_profile")))


if __name__ == "__main__":
    unittest.main()

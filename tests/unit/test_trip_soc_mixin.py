"""[RED] Test: _SOCMixin has SOC calculation methods.

Verifies _SOCMixin is importable from trip._soc_mixin and exposes
the full set of SOC calculation methods.
"""

import unittest


class TestSOCMixin(unittest.TestCase):
    """_SOCMixin must be importable from trip._soc_mixin with expected methods."""

    def test_soc_mixin_is_importable(self):
        """_SOCMixin can be imported from custom_components.ev_trip_planner.trip._soc_mixin."""
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin

        self.assertIsNotNone(_SOCMixin)

    def test_has_async_get_vehicle_soc(self):
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin

        self.assertTrue(hasattr(_SOCMixin, "async_get_vehicle_soc"))
        self.assertTrue(callable(getattr(_SOCMixin, "async_get_vehicle_soc")))

    def test_has_async_get_kwh_needed_today(self):
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin

        self.assertTrue(hasattr(_SOCMixin, "async_get_kwh_needed_today"))
        self.assertTrue(callable(getattr(_SOCMixin, "async_get_kwh_needed_today")))

    def test_has_async_get_hours_needed_today(self):
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin

        self.assertTrue(hasattr(_SOCMixin, "async_get_hours_needed_today"))
        self.assertTrue(callable(getattr(_SOCMixin, "async_get_hours_needed_today")))

    def test_has_calcular_ventana_carga(self):
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin

        self.assertTrue(hasattr(_SOCMixin, "calcular_ventana_carga"))
        self.assertTrue(callable(getattr(_SOCMixin, "calcular_ventana_carga")))

    def test_has_calcular_ventana_carga_multitrip(self):
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin

        self.assertTrue(hasattr(_SOCMixin, "calcular_ventana_carga_multitrip"))
        self.assertTrue(callable(getattr(_SOCMixin, "calcular_ventana_carga_multitrip")))

    def test_has_calcular_soc_inicio_trips(self):
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin

        self.assertTrue(hasattr(_SOCMixin, "calcular_soc_inicio_trips"))
        self.assertTrue(callable(getattr(_SOCMixin, "calcular_soc_inicio_trips")))

    def test_has_calcular_hitos_soc(self):
        from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin

        self.assertTrue(hasattr(_SOCMixin, "calcular_hitos_soc"))
        self.assertTrue(callable(getattr(_SOCMixin, "calcular_hitos_soc")))


if __name__ == "__main__":
    unittest.main()

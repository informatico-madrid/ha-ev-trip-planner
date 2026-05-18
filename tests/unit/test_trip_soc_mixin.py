"""[RED] Test: SOCQuery has SOC calculation methods.

Verifies SOCQuery is importable from trip._soc_query and exposes
the full set of SOC query methods.
"""

import unittest


class TestSOCMixin(unittest.TestCase):
    """SOCQuery must be importable from trip._soc_query with expected methods."""

    def test_soc_mixin_is_importable(self):
        """SOCQuery can be imported from custom_components.ev_trip_planner.trip._soc_query."""
        from custom_components.ev_trip_planner.trip._soc_query import SOCQuery

        self.assertIsNotNone(SOCQuery)

    def test_has_async_get_vehicle_soc(self):
        from custom_components.ev_trip_planner.trip._soc_query import SOCQuery

        self.assertTrue(hasattr(SOCQuery, "async_get_vehicle_soc"))
        self.assertTrue(callable(getattr(SOCQuery, "async_get_vehicle_soc")))

    def test_has_async_get_kwh_needed_today(self):
        from custom_components.ev_trip_planner.trip._soc_query import SOCQuery

        self.assertTrue(hasattr(SOCQuery, "async_get_kwh_needed_today"))
        self.assertTrue(callable(getattr(SOCQuery, "async_get_kwh_needed_today")))

    def test_has_async_get_hours_needed_today(self):
        from custom_components.ev_trip_planner.trip._soc_query import SOCQuery

        self.assertTrue(hasattr(SOCQuery, "async_get_hours_needed_today"))
        self.assertTrue(callable(getattr(SOCQuery, "async_get_hours_needed_today")))

    def test_has_calcular_ventana_carga(self):
        from custom_components.ev_trip_planner.trip._soc_window import SOCWindow

        self.assertTrue(hasattr(SOCWindow, "calcular_ventana_carga"))
        self.assertTrue(callable(getattr(SOCWindow, "calcular_ventana_carga")))

    def test_has_calcular_ventana_carga_multitrip(self):
        from custom_components.ev_trip_planner.trip._soc_window import SOCWindow

        self.assertTrue(hasattr(SOCWindow, "calcular_ventana_carga_multitrip"))
        self.assertTrue(
            callable(getattr(SOCWindow, "calcular_ventana_carga_multitrip"))
        )

    def test_has_calcular_soc_inicio_trips(self):
        from custom_components.ev_trip_planner.trip._soc_window import SOCWindow

        self.assertTrue(hasattr(SOCWindow, "calcular_soc_inicio_trips"))
        self.assertTrue(callable(getattr(SOCWindow, "calcular_soc_inicio_trips")))

    def test_has_calcular_hitos_soc(self):
        from custom_components.ev_trip_planner.trip._soc_window import SOCWindow

        self.assertTrue(hasattr(SOCWindow, "calcular_hitos_soc"))
        self.assertTrue(callable(getattr(SOCWindow, "calcular_hitos_soc")))


if __name__ == "__main__":
    unittest.main()

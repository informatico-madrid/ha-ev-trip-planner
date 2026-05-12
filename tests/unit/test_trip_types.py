"""Tests for trip._types module — TypedDict definitions extracted from trip_manager."""

from custom_components.ev_trip_planner.trip._types import (
    CargaVentana,
    SOCMilestoneResult,
)


class TestCargaVentanaTypedDict:
    """Test CargaVentana TypedDict is importable and has expected keys."""

    def test_importable(self):
        """CargaVentana can be imported from trip._types."""
        assert CargaVentana is not None

    def test_has_required_keys(self):
        """CargaVentana TypedDict has all required fields."""
        required_keys = {
            "ventana_horas",
            "kwh_necesarios",
            "horas_carga_necesarias",
            "inicio_ventana",
            "fin_ventana",
            "es_suficiente",
        }
        assert required_keys.issubset(set(CargaVentana.__required_keys__))


class TestSOCMilestoneResultTypedDict:
    """Test SOCMilestoneResult TypedDict is importable and has expected keys."""

    def test_importable(self):
        """SOCMilestoneResult can be imported from trip._types."""
        assert SOCMilestoneResult is not None

    def test_has_required_keys(self):
        """SOCMilestoneResult TypedDict has all required fields."""
        required_keys = {
            "trip_id",
            "soc_objetivo",
            "kwh_necesarios",
            "deficit_acumulado",
            "ventana_carga",
        }
        assert required_keys.issubset(set(SOCMilestoneResult.__required_keys__))

"""Tests for sensor attributes validation (Dashboard compatibility)."""

from unittest.mock import MagicMock

from custom_components.ev_trip_planner.sensor import TripPlannerSensor
from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription


def make_test_description(key: str):
    """Create a test entity description."""
    return TripSensorEntityDescription(
        key=key,
        name=f"Test {key}",
        icon="mdi:car",
        native_unit_of_measurement=None,
        state_class=None,
        value_fn=lambda data: data.get(key, 0) if data else 0,
        attrs_fn=lambda data: {
            "recurring_trips": list(data.get("recurring_trips", {}).values()),
            "punctual_trips": list(data.get("punctual_trips", {}).values()),
        } if data else {"recurring_trips": [], "punctual_trips": []},
    )


class TestTripPlannerSensorAttributes:
    """Tests for TripPlannerSensor extra_state_attributes."""

    def test_trips_list_sensor_exposes_trips_attribute(self):
        """El sensor debe exponer atributo 'trips' combinado para el dashboard."""
        # Arrange - create mock coordinator with data
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {
                "rec_1": {"id": "rec_1", "tipo": "recurrente", "dia_semana": "lunes"}
            },
            "punctual_trips": {
                "pun_1": {"id": "pun_1", "tipo": "puntual", "datetime": "2025-11-25T10:00:00"}
            },
            "kwh_today": 0.0,
            "hours_today": 0.0,
            "next_trip": None,
        }

        desc = make_test_description("test_key")
        sensor = TripPlannerSensor(mock_coordinator, "test_vehicle", desc)

        # Act
        attrs = sensor.extra_state_attributes

        # Assert
        assert "recurring_trips" in attrs, "Debe existir atributo 'recurring_trips'"
        assert "punctual_trips" in attrs, "Debe existir atributo 'punctual_trips'"
        assert len(attrs["recurring_trips"]) == 1
        assert len(attrs["punctual_trips"]) == 1

    def test_trips_list_sensor_backward_compatibility(self):
        """El sensor debe mantener atributos antiguos para backward compatibility."""
        # Arrange
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {
                "rec_1": {"id": "rec_1"}
            },
            "punctual_trips": {
                "pun_1": {"id": "pun_1"}
            },
            "kwh_today": 0.0,
            "hours_today": 0.0,
            "next_trip": None,
        }

        desc = make_test_description("test_key")
        sensor = TripPlannerSensor(mock_coordinator, "test_vehicle", desc)

        # Act
        attrs = sensor.extra_state_attributes

        # Assert
        assert "recurring_trips" in attrs, "Backward compatibility: recurring_trips"
        assert "punctual_trips" in attrs, "Backward compatibility: punctual_trips"
        assert len(attrs["recurring_trips"]) == 1
        assert len(attrs["punctual_trips"]) == 1

    def test_trips_list_sensor_empty_data(self):
        """El sensor debe manejar datos vacíos correctamente."""
        # Arrange
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {},
            "kwh_today": 0.0,
            "hours_today": 0.0,
            "next_trip": None,
        }

        desc = make_test_description("test_key")
        sensor = TripPlannerSensor(mock_coordinator, "test_vehicle", desc)

        # Act
        attrs = sensor.extra_state_attributes

        # Assert
        assert "recurring_trips" in attrs
        assert "punctual_trips" in attrs
        assert attrs["recurring_trips"] == []
        assert attrs["punctual_trips"] == []

    def test_dashboard_template_logic_simulation(self):
        """Simula la lógica de renderización del dashboard."""
        # Arrange
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {
                "rec_1": {"tipo": "recurrente", "dia_semana": "lunes", "hora": "12:00"}
            },
            "punctual_trips": {
                "pun_1": {"tipo": "puntual", "datetime": "2025-11-25T15:00:00"}
            },
            "kwh_today": 0.0,
            "hours_today": 0.0,
            "next_trip": None,
        }

        desc = make_test_description("test_key")
        sensor = TripPlannerSensor(mock_coordinator, "test_vehicle", desc)

        # Act - Simular lo que hace el dashboard
        attrs = sensor.extra_state_attributes

        # Dashboard hace: {% for trip in trips | selectattr('tipo', 'equalto', 'recurrente') %}
        recurring = [t for t in attrs.get("recurring_trips", [])]
        punctual = [t for t in attrs.get("punctual_trips", [])]

        # Assert
        assert len(recurring) == 1, "Dashboard debe ver 1 viaje recurrente"
        assert len(punctual) == 1, "Dashboard debe ver 1 viaje puntual"
        assert recurring[0]["dia_semana"] == "lunes"
        assert punctual[0]["datetime"] == "2025-11-25T15:00:00"
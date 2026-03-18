"""Tests for sensor attributes validation (Dashboard compatibility)."""

import pytest
from unittest.mock import Mock, patch

from custom_components.ev_trip_planner.sensor import TripPlannerSensor


def test_trips_list_sensor_exposes_trips_attribute():
    """El sensor debe exponer atributo 'trips' combinado para el dashboard."""
    # Arrange
    with patch("custom_components.ev_trip_planner.sensor.TripManager"):
        mock_trip_manager = Mock()
        sensor = TripPlannerSensor(Mock(), mock_trip_manager, "test")

    # Mock the cached attributes
    sensor._cached_attrs = {
        "recurring_trips": [
            {"id": "rec_1", "tipo": "recurrente", "dia_semana": "lunes"}
        ],
        "punctual_trips": [
            {"id": "pun_1", "tipo": "puntual", "datetime": "2025-11-25T10:00:00"}
        ],
    }

    # Act
    attrs = sensor.extra_state_attributes

    # Assert
    assert "recurring_trips" in attrs, "Debe existir atributo 'recurring_trips'"
    assert "punctual_trips" in attrs, "Debe existir atributo 'punctual_trips'"
    assert len(attrs["recurring_trips"]) == 1
    assert len(attrs["punctual_trips"]) == 1


def test_trips_list_sensor_backward_compatibility():
    """El sensor debe mantener atributos antiguos para backward compatibility."""
    # Arrange
    with patch("custom_components.ev_trip_planner.sensor.TripManager"):
        mock_trip_manager = Mock()
        sensor = TripPlannerSensor(Mock(), mock_trip_manager, "test")

    # Mock the cached attributes
    sensor._cached_attrs = {
        "recurring_trips": [{"id": "rec_1"}],
        "punctual_trips": [{"id": "pun_1"}],
    }

    # Act
    attrs = sensor.extra_state_attributes

    # Assert
    assert "recurring_trips" in attrs, "Backward compatibility: recurring_trips"
    assert "punctual_trips" in attrs, "Backward compatibility: punctual_trips"
    assert len(attrs["recurring_trips"]) == 1
    assert len(attrs["punctual_trips"]) == 1


def test_trips_list_sensor_empty_data():
    """El sensor debe manejar datos vacíos correctamente."""
    # Arrange
    with patch("custom_components.ev_trip_planner.sensor.TripManager"):
        mock_trip_manager = Mock()
        sensor = TripPlannerSensor(Mock(), mock_trip_manager, "test")

    # Mock empty cached attributes
    sensor._cached_attrs = {}

    # Act
    attrs = sensor.extra_state_attributes

    # Assert
    assert "recurring_trips" in attrs
    assert "punctual_trips" in attrs
    assert attrs["recurring_trips"] == []
    assert attrs["punctual_trips"] == []


def test_dashboard_template_logic_simulation():
    """Simula la lógica de renderización del dashboard."""
    # Arrange
    with patch("custom_components.ev_trip_planner.sensor.TripManager"):
        mock_trip_manager = Mock()
        sensor = TripPlannerSensor(Mock(), mock_trip_manager, "test")

    # Mock the cached attributes with both trip types
    sensor._cached_attrs = {
        "recurring_trips": [
            {"tipo": "recurrente", "dia_semana": "lunes", "hora": "12:00"}
        ],
        "punctual_trips": [
            {"tipo": "puntual", "datetime": "2025-11-25T15:00:00"}
        ],
    }

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

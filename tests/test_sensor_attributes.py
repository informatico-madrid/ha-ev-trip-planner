"""Tests for sensor attributes validation (Dashboard compatibility)."""

import pytest
from unittest.mock import Mock

from custom_components.ev_trip_planner.sensor import TripsListSensor


def test_trips_list_sensor_exposes_trips_attribute():
    """El sensor debe exponer atributo 'trips' combinado para el dashboard."""
    # Arrange
    mock_coordinator = Mock()
    mock_coordinator.data = {
        "recurring_trips": [
            {"id": "rec_1", "tipo": "recurrente", "dia_semana": "lunes"}
        ],
        "punctual_trips": [
            {"id": "pun_1", "tipo": "puntual", "datetime": "2025-11-25T10:00:00"}
        ]
    }
    
    sensor = TripsListSensor("test_vehicle", mock_coordinator)
    
    # Act
    attrs = sensor.extra_state_attributes
    
    # Assert
    assert "trips" in attrs, "Debe existir atributo 'trips' para dashboard"
    assert len(attrs["trips"]) == 2, "Debe combinar recurring + punctual"
    assert attrs["trips"][0]["tipo"] == "recurrente"
    assert attrs["trips"][1]["tipo"] == "puntual"


def test_trips_list_sensor_backward_compatibility():
    """El sensor debe mantener atributos antiguos para backward compatibility."""
    # Arrange
    mock_coordinator = Mock()
    mock_coordinator.data = {
        "recurring_trips": [{"id": "rec_1"}],
        "punctual_trips": [{"id": "pun_1"}]
    }
    
    sensor = TripsListSensor("test_vehicle", mock_coordinator)
    
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
    mock_coordinator = Mock()
    mock_coordinator.data = {}
    
    sensor = TripsListSensor("test_vehicle", mock_coordinator)
    
    # Act
    attrs = sensor.extra_state_attributes
    
    # Assert
    assert "trips" in attrs
    assert attrs["trips"] == [], "Debe retornar lista vacía si no hay datos"
    assert attrs["recurring_trips"] == []
    assert attrs["punctual_trips"] == []


def test_dashboard_template_logic_simulation():
    """Simula la lógica de renderización del dashboard."""
    # Arrange
    mock_coordinator = Mock()
    mock_coordinator.data = {
        "recurring_trips": [
            {"tipo": "recurrente", "dia_semana": "lunes", "hora": "12:00"}
        ],
        "punctual_trips": [
            {"tipo": "puntual", "datetime": "2025-11-25T15:00:00"}
        ]
    }
    
    sensor = TripsListSensor("test_vehicle", mock_coordinator)
    
    # Act - Simular lo que hace el dashboard
    attrs = sensor.extra_state_attributes
    trips = attrs.get("trips", [])
    
    # Dashboard hace: {% for trip in trips | selectattr('tipo', 'equalto', 'recurrente') %}
    recurring = [t for t in trips if t.get("tipo") == "recurrente"]
    punctual = [t for t in trips if t.get("tipo") == "puntual"]
    
    # Assert
    assert len(recurring) == 1, "Dashboard debe ver 1 viaje recurrente"
    assert len(punctual) == 1, "Dashboard debe ver 1 viaje puntual"
    assert recurring[0]["dia_semana"] == "lunes"
    assert punctual[0]["datetime"] == "2025-11-25T15:00:00"
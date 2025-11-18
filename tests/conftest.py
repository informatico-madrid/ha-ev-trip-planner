"""Test fixtures for ev_trip_planner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.const import DOMAIN


@pytest.fixture
def mock_input_text_entity():
    """Return a mocked input_text entity with empty trips."""
    state = MagicMock()
    state.state = "[]"
    return state


@pytest.fixture
def mock_input_text_entity_with_trips():
    """Return a mocked input_text entity with sample trips."""
    state = MagicMock()
    state.state = """[
        {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
            "descripcion": "Trabajo",
            "activo": true,
            "creado": "2025-11-18T10:00:00"
        },
        {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "km": 110,
            "kwh": 16.5,
            "descripcion": "Viaje a Toledo",
            "estado": "pendiente",
            "creado": "2025-11-18T10:30:00"
        }
    ]"""
    return state


@pytest.fixture
def vehicle_id():
    """Return a sample vehicle ID."""
    return "chispitas"

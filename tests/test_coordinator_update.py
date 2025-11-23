"""Test simple para verificar que el coordinator actualiza datos correctamente.

NOTA: Este test produce un "Lingering timer" en teardown debido al
debounce interno del coordinator. Esto es un problema conocido de la infraestructura
de tests de Home Assistant y no afecta la funcionalidad del componente.

Referencia: https://github.com/home-assistant/core/issues/83432
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from homeassistant.core import HomeAssistant
from custom_components.ev_trip_planner import TripPlannerCoordinator
from custom_components.ev_trip_planner.trip_manager import TripManager


# FIX: Permitir lingering tasks y timers en estos tests
# Estos fixtures anulan los defaults de pytest-homeassistant-custom-component
# para permitir tasks y timers pendientes en teardown cuando se usan coordinators
@pytest.fixture
def expected_lingering_tasks():
    """Permitir lingering tasks para tests que usan coordinators."""
    return True


@pytest.fixture
def expected_lingering_timers():
    """Permitir lingering timers para tests que usan coordinators con debounce.
    
    Este fixture es requerido por pytest-homeassistant-custom-component para
    permitir timers pendientes en teardown. Los coordinators con debounce
    interno (como DataUpdateCoordinator) dejan timers que no se pueden cancelar
    fácilmente en el contexto de tests.
    
    Referencia: https://github.com/home-assistant/core/issues/83432
    """
    return True


@pytest.fixture
def mock_trip_manager():
    """Fixture para TripManager con datos controlados."""
    manager = MagicMock(spec=TripManager)
    
    # Datos iniciales: sin viajes
    manager.async_get_recurring_trips = AsyncMock(return_value=[])
    manager.async_get_punctual_trips = AsyncMock(return_value=[])
    manager.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
    manager.async_get_hours_needed_today = AsyncMock(return_value=0)
    manager.async_get_next_trip = AsyncMock(return_value=None)
    
    return manager


@pytest.fixture
async def coordinator(hass: HomeAssistant, mock_trip_manager):
    """Fixture para coordinator inicializado."""
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    # NO llamar a async_config_entry_first_refresh aquí
    return coordinator


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_coordinator_actualiza_datos_correctamente(
    hass: HomeAssistant, coordinator, mock_trip_manager
):
    """Test que verifica que el coordinator actualiza datos al llamar a async_request_refresh()."""
    
    # 1. Verificar estado inicial (sin datos)
    assert coordinator.data is None
    
    # 2. Forzar primera actualización
    await coordinator.async_config_entry_first_refresh()
    
    # 3. Verificar que se llamaron los métodos correctos
    mock_trip_manager.async_get_recurring_trips.assert_called_once()
    mock_trip_manager.async_get_punctual_trips.assert_called_once()
    mock_trip_manager.async_get_kwh_needed_today.assert_called_once()
    mock_trip_manager.async_get_hours_needed_today.assert_called_once()
    mock_trip_manager.async_get_next_trip.assert_called_once()
    
    # 4. Verificar datos iniciales (sin viajes)
    assert coordinator.data["kwh_today"] == 0.0
    assert coordinator.data["hours_today"] == 0
    assert coordinator.data["next_trip"] is None
    
    # 5. Cambiar los mocks para simular un viaje
    mock_trip_manager.async_get_kwh_needed_today.return_value = 7.5
    mock_trip_manager.async_get_hours_needed_today.return_value = 2
    mock_trip_manager.async_get_next_trip.return_value = {
        "descripcion": "Viaje de prueba",
        "datetime": datetime(2025, 11, 23, 10, 0, 0),
    }
    
    # 6. Forzar refresh del coordinator
    await coordinator.async_request_refresh()
    
    # 7. Verificar que se llamaron los métodos de nuevo
    assert mock_trip_manager.async_get_kwh_needed_today.call_count == 2
    assert mock_trip_manager.async_get_hours_needed_today.call_count == 2
    assert mock_trip_manager.async_get_next_trip.call_count == 2
    
    # 8. Verificar que los datos se actualizaron
    print(f"DEBUG: coordinator.data = {coordinator.data}")
    assert coordinator.data["kwh_today"] == 7.5, f"Expected 7.5, got {coordinator.data['kwh_today']}"
    assert coordinator.data["hours_today"] == 2, f"Expected 2, got {coordinator.data['hours_today']}"
    assert coordinator.data["next_trip"]["descripcion"] == "Viaje de prueba"
"""Test que demuestra el bug de actualización automática de sensores Milestone 2.

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
from custom_components.ev_trip_planner.sensor import (
    KwhTodaySensor,
    HoursTodaySensor,
    NextTripSensor,
    NextDeadlineSensor,
)
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
    # No llamar a async_config_entry_first_refresh aquí para tener control total
    return coordinator


async def test_sensors_no_se_actualizan_automaticamente(
    hass: HomeAssistant, mock_trip_manager
):
    """Test que demuestra el bug: sensores no se actualizan al cambiar datos."""
    
    # 1. Crear coordinator SIN inicializar
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    
    # 2. Forzar primera actualización para tener datos iniciales
    await coordinator.async_config_entry_first_refresh()
    
    # 3. Crear sensores
    kwh_sensor = KwhTodaySensor("test_vehicle", coordinator)
    hours_sensor = HoursTodaySensor("test_vehicle", coordinator)
    next_trip_sensor = NextTripSensor("test_vehicle", coordinator)
    next_deadline_sensor = NextDeadlineSensor("test_vehicle", coordinator)
    
    # 4. Verificar valores iniciales (sin viajes)
    assert kwh_sensor.native_value == 0.0
    assert hours_sensor.native_value == 0
    assert next_trip_sensor.native_value == "No trips"
    assert next_deadline_sensor.native_value is None
    
    # 5. Simular añadir un viaje para HOY en el trip_manager
    mock_trip_manager.async_get_kwh_needed_today.return_value = 7.5
    mock_trip_manager.async_get_hours_needed_today.return_value = 2
    mock_trip_manager.async_get_next_trip.return_value = {
        "descripcion": "Viaje de prueba",
        "datetime": datetime(2025, 11, 23, 10, 0, 0),
    }
    
    # 6. Forzar refresh del coordinator para que actualice los datos
    print(f"DEBUG: Antes de refresh - coordinator.data = {coordinator.data}")
    await coordinator.async_request_refresh()
    print(f"DEBUG: Después de refresh - coordinator.data = {coordinator.data}")
    
    # 7. Verificar que coordinator.data se actualizó correctamente
    #    El coordinator debería haber llamado a los métodos del trip_manager
    assert coordinator.data["kwh_today"] == 7.5, "Coordinator no actualizó kwh_today"
    assert coordinator.data["hours_today"] == 2, "Coordinator no actualizó hours_today"
    assert coordinator.data["next_trip"]["descripcion"] == "Viaje de prueba", "Coordinator no actualizó next_trip"
    
    # 8. ✅ FIX: Los sensores ahora leen directamente desde coordinator.data
    #    No necesitan _handle_coordinator_update() porque native_value accede directamente
    assert kwh_sensor.native_value == 7.5, "FIX: Debería ser 7.5 después de coordinator refresh"
    assert hours_sensor.native_value == 2, "FIX: Debería ser 2 después de coordinator refresh"
    assert next_trip_sensor.native_value == "Viaje de prueba", "FIX: Debería ser 'Viaje de prueba'"
    assert next_deadline_sensor.native_value is not None, "FIX: Debería tener datetime"
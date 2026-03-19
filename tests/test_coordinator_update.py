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
def mock_trip_manager(mock_store, hass):
    """Fixture para TripManager con datos controlados."""
    manager = MagicMock(spec=TripManager)

    # Datos iniciales: sin viajes
    manager.async_get_recurring_trips = AsyncMock(return_value=[])
    manager.async_get_punctual_trips = AsyncMock(return_value=[])
    manager.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
    manager.async_get_hours_needed_today = AsyncMock(return_value=0)
    manager.async_get_next_trip = AsyncMock(return_value=None)

    # IMPORTANT: El coordinator llama a métodos del trip_manager que usan el store
    # Necesitamos asegurarnos de que el mock_trip_manager tenga un store mock
    manager._store = mock_store

    # Add hass attribute required by sensors (they call super().__init__ which needs hass)
    manager.hass = hass

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


async def test_coordinator_updates_after_creating_trip_via_service(
    hass: HomeAssistant, mock_trip_manager
):
    """Test T034: Coordinator se actualiza después de crear trip (US4).

    Este test verifica el flujo completo cuando un usuario crea un trip
    mediante el servicio:
    1. El trip se guarda en el trip_manager
    2. El coordinator.refresh se triggerea (como en los servicios reales)
    3. El coordinator.data se actualiza con los nuevos trips

    Este test simula exactamente lo que sucede cuando se llama a
    add_recurring_trip o add_punctual_trip desde Home Assistant.

    Flujo verificado:
    - handle_add_recurring() -> mgr.async_add_recurring_trip()
      -> coordinator.async_refresh_trips() -> coordinator.data actualizado
    """
    # 1. Crear coordinator y forzamos primera carga
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    await coordinator.async_config_entry_first_refresh()

    # 2. Verificar estado inicial (sin trips)
    assert coordinator.data["recurring_trips"] == []
    assert coordinator.data["punctual_trips"] == []

    # 3. Simular que el trip_manager guarda un nuevo trip
    # (como lo hace el servicio en __init__.py líneas 583-589)
    new_recurring_trip = {
        "id": "new_recurring_1",
        "origin": "Home",
        "destination": "Office",
        "departure_time": "08:00",
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "distance_km": 25,
        "energy_kwh": 5.0,
    }

    # Configurar mock para devolver el nuevo trip después de guardarlo
    mock_trip_manager.async_get_recurring_trips = AsyncMock(
        return_value=[new_recurring_trip]
    )
    mock_trip_manager.async_add_recurring_trip = AsyncMock()

    # 4. Simular el flujo del servicio después de añadir un trip
    # Esto es exactamente lo que hace handle_add_recurring() en __init__.py
    # (líneas 590-594)
    await mock_trip_manager.async_add_recurring_trip(
        dia_semana="lunes",
        hora="08:00",
        km=25.0,
        kwh=5.0,
        descripcion="Viaje al trabajo",
    )

    # 5. Forzar refresh del coordinator (como lo hace el servicio)
    await coordinator.async_refresh_trips()

    # 6. Verificar que el coordinator.data se actualizó correctamente
    assert coordinator.data["recurring_trips"] == [new_recurring_trip], (
        f"Coordinator debe tener el nuevo trip recurrente, "
        f"got: {coordinator.data['recurring_trips']}"
    )

    # 7. Verificar que el coordinator volvió a llamar a los métodos del trip_manager
    # (para obtener los datos actualizados)
    assert mock_trip_manager.async_get_recurring_trips.call_count >= 1, (
        "Coordinator debe haber llamado a async_get_recurring_trips"
    )


async def test_coordinator_updates_after_creating_punctual_trip(
    hass: HomeAssistant, mock_trip_manager
):
    """Test T034b: Coordinator se actualiza después de crear trip puntual.

    Este test verifica el flujo completo para trips puntuales,
    que es similar al de trips recurrentes pero usa handle_add_punctual.
    """
    # 1. Crear coordinator
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    await coordinator.async_config_entry_first_refresh()

    # 2. Verificar estado inicial
    assert coordinator.data["punctual_trips"] == []

    # 3. Simular nuevo trip puntual
    new_punctual_trip = {
        "id": "new_punctual_1",
        "origin": "Home",
        "destination": "Airport",
        "departure_time": "06:00",
        "departure_date": "2025-12-01",
        "distance_km": 40,
        "energy_kwh": 8.0,
    }

    mock_trip_manager.async_get_punctual_trips = AsyncMock(
        return_value=[new_punctual_trip]
    )
    mock_trip_manager.async_add_punctual_trip = AsyncMock()

    # 4. Simular el flujo del servicio (como handle_add_punctual en __init__.py)
    await mock_trip_manager.async_add_punctual_trip(
        datetime_str="2025-12-01T06:00",
        km=40.0,
        kwh=8.0,
        descripcion="Viaje al aeropuerto",
    )

    # 5. Forzar refresh (como lo hace el servicio)
    await coordinator.async_refresh_trips()

    # 6. Verificar actualización
    assert coordinator.data["punctual_trips"] == [new_punctual_trip], (
        f"Coordinator debe tener el nuevo trip puntual, "
        f"got: {coordinator.data['punctual_trips']}"
    )


async def test_coordinator_data_updates_for_all_trip_types(
    hass: HomeAssistant, mock_trip_manager
):
    """Test T034c: Coordinator actualiza datos para todos los tipos de trips.

    Este test verifica que el coordinator actualiza correctamente
    tanto trips recurrentes como puntuales después de un refresh.
    """
    # 1. Crear coordinator
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    await coordinator.async_config_entry_first_refresh()

    # 2. Datos de prueba
    mock_recurring = [
        {"id": "rec_1", "origin": "Home", "destination": "Office", "distance_km": 25},
    ]
    mock_punctual = [
        {"id": "pun_1", "origin": "Home", "destination": "Airport", "distance_km": 40},
    ]

    # 3. Configurar mocks para devolver trips
    mock_trip_manager.async_get_recurring_trips = AsyncMock(
        return_value=mock_recurring
    )
    mock_trip_manager.async_get_punctual_trips = AsyncMock(
        return_value=mock_punctual
    )

    # 4. Forzar refresh (como lo hacen los servicios después de crear/editar trips)
    await coordinator.async_refresh_trips()

    # 5. Verificar que coordinator.data tiene todos los trips
    assert coordinator.data["recurring_trips"] == mock_recurring, (
        "Coordinator debe tener trips recurrentes"
    )
    assert coordinator.data["punctual_trips"] == mock_punctual, (
        "Coordinator debe tener trips puntuales"
    )

    # 6. Verificar que los conteos son correctos
    assert len(coordinator.data["recurring_trips"]) == 1
    assert len(coordinator.data["punctual_trips"]) == 1


async def test_refresh_propagates_to_all_sensors(hass: HomeAssistant, mock_trip_manager):
    """Test T035: Refresh se propaga a todos los sensores (US4).

    Este test verifica que cuando se llama a coordinator.async_refresh_trips(),
    TODOS los sensores suscritos al coordinator reciben los datos actualizados.

    Este test es crítico porque verifica el requisito de que la actualización
    del coordinator se propaga correctamente a todos los sensores.

    El patrón de Home Assistant es:
    1. Sensores se suscriben al coordinator (usualmente en async_setup_entry)
    2. Cuando coordinator.async_request_refresh() completa,
       el coordinator notifica a todos los listeners (sensores)
    3. Los sensores leen coordinator.data en su propiedad native_value

    Flujo verificado:
    - Crear múltiples sensores de diferentes tipos
    - Verificar valores iniciales (0 o vacíos)
    - Simular cambios en trip_manager
    - Llamar coordinator.async_refresh_trips()
    - Verificar que TODOS los sensores tienen los valores actualizados
    """
    from custom_components.ev_trip_planner.sensor import (
        RecurringTripsCountSensor,
        PunctualTripsCountSensor,
        TripsListSensor,
        KwhTodaySensor,
        HoursTodaySensor,
        NextTripSensor,
        NextDeadlineSensor,
    )

    # 1. Crear coordinator y forzar primera carga
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    await coordinator.async_config_entry_first_refresh()

    # 2. Crear TODOS los sensores del componente
    sensors = {
        "recurring": RecurringTripsCountSensor("test_vehicle", coordinator),
        "punctual": PunctualTripsCountSensor("test_vehicle", coordinator),
        "trips_list": TripsListSensor("test_vehicle", coordinator),
        "kwh_today": KwhTodaySensor("test_vehicle", coordinator),
        "hours_today": HoursTodaySensor("test_vehicle", coordinator),
        "next_trip": NextTripSensor("test_vehicle", coordinator),
        "next_deadline": NextDeadlineSensor("test_vehicle", coordinator),
    }

    # 3. Verificar valores iniciales (sin trips)
    assert sensors["recurring"].native_value == 0, "Recurring debe iniciar en 0"
    assert sensors["punctual"].native_value == 0, "Punctual debe iniciar en 0"
    assert sensors["trips_list"].native_value == 0, "Trips list debe iniciar en 0"
    assert sensors["kwh_today"].native_value == 0.0, "Kwh today debe iniciar en 0"
    assert sensors["hours_today"].native_value == 0, "Hours today debe iniciar en 0"
    # NextTripSensor returns "No trips" when there's no next trip
    assert sensors["next_trip"].native_value == "No trips", "Next trip debe iniciar en 'No trips'"
    # NextDeadlineSensor returns None when there's no next trip
    assert sensors["next_deadline"].native_value is None, "Next deadline debe iniciar en None"

    # 4. Simular cambios en trip_manager (como cuando se crea un nuevo trip)
    mock_recurring = [
        {"id": "rec_1", "origin": "Home", "destination": "Office", "distance_km": 25}
    ]
    mock_punctual = [
        {"id": "pun_1", "origin": "Home", "destination": "Airport", "distance_km": 40}
    ]

    mock_trip_manager.async_get_recurring_trips = AsyncMock(
        return_value=mock_recurring
    )
    mock_trip_manager.async_get_punctual_trips = AsyncMock(
        return_value=mock_punctual
    )
    mock_trip_manager.async_get_kwh_needed_today = AsyncMock(return_value=7.5)
    mock_trip_manager.async_get_hours_needed_today = AsyncMock(return_value=2)
    mock_trip_manager.async_get_next_trip = AsyncMock(
        return_value={
            "descripcion": "Viaje importante",
            "datetime": "2025-12-01T10:00:00",
            "tipo": "puntual",
        }
    )

    # 5. Forzar refresh del coordinator
    # Esto es lo que hacen los servicios después de crear/editar trips
    await coordinator.async_refresh_trips()

    # 6. Verificar que TODOS los sensores tienen los valores actualizados
    # AFTER the refresh, sensors should read the new data from coordinator.data

    # Verificar sensor de trips recurrentes
    assert sensors["recurring"].native_value == 1, (
        f"Recurring sensor debe mostrar 1, got: {sensors['recurring'].native_value}"
    )

    # Verificar sensor de trips puntuales
    assert sensors["punctual"].native_value == 1, (
        f"Punctual sensor debe mostrar 1, got: {sensors['punctual'].native_value}"
    )

    # Verificar sensor de lista de trips
    assert sensors["trips_list"].native_value == 2, (
        f"Trips list debe mostrar 2, got: {sensors['trips_list'].native_value}"
    )

    # Verificar sensor de kWh hoy
    assert sensors["kwh_today"].native_value == 7.5, (
        f"Kwh today debe mostrar 7.5, got: {sensors['kwh_today'].native_value}"
    )

    # Verificar sensor de horas hoy
    assert sensors["hours_today"].native_value == 2, (
        f"Hours today debe mostrar 2, got: {sensors['hours_today'].native_value}"
    )

    # Verificar sensor de próximo trip
    assert sensors["next_trip"].native_value == "Viaje importante", (
        f"Next trip debe mostrar 'Viaje importante', got: {sensors['next_trip'].native_value}"
    )

    # Verificar sensor de próximo deadline
    assert sensors["next_deadline"].native_value == "2025-12-01T10:00:00", (
        f"Next deadline debe mostrar '2025-12-01T10:00:00', got: {sensors['next_deadline'].native_value}"
    )

    # 7. Verificar que coordinator.data también se actualizó correctamente
    assert coordinator.data["recurring_trips"] == mock_recurring
    assert coordinator.data["punctual_trips"] == mock_punctual
    assert coordinator.data["kwh_today"] == 7.5
    assert coordinator.data["hours_today"] == 2
    assert coordinator.data["next_trip"]["descripcion"] == "Viaje importante"
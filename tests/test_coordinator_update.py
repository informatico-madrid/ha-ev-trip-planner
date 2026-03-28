"""Test simple para verificar que el coordinator actualiza datos correctamente.

Estos tests verifican el comportamiento del DataUpdateCoordinator para EV Trip Planner.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from homeassistant.core import HomeAssistant
from custom_components.ev_trip_planner import TripPlannerCoordinator
from custom_components.ev_trip_planner.trip_manager import TripManager


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
    from homeassistant.config_entries import ConfigEntryState

    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.source = "user"
    mock_config_entry.unique_id = "test_vehicle"
    mock_config_entry.data = {}
    mock_config_entry.options = {}
    mock_config_entry.title = "Test Vehicle"
    mock_config_entry.version = 1
    mock_config_entry.minor_version = 1
    mock_config_entry.discovery_keys = {}
    mock_config_entry.entry_type = None
    mock_config_entry.disabled_by = None
    mock_config_entry.reauth_entry = None
    mock_config_entry.pref_disable_new_entities = False
    mock_config_entry.pref_disable_polling = False

    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)
    return coordinator


async def test_coordinator_actualiza_datos_correctamente(
    hass: HomeAssistant, coordinator, mock_trip_manager
):
    """Test que verifica que el coordinator actualiza datos al llamar a async_request_refresh()."""

    # 1. Verificar estado inicial (sin datos)
    assert coordinator.data is None

    # 2. Forzar primera actualización manual
    await coordinator.async_refresh()

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
    await coordinator.async_refresh()

    # 7. Verificar que los datos se actualizaron
    print(f"DEBUG: coordinator.data = {coordinator.data}")
    assert coordinator.data["kwh_today"] == 7.5, f"Expected 7.5, got {coordinator.data['kwh_today']}"
    assert coordinator.data["hours_today"] == 2, f"Expected 2, got {coordinator.data['hours_today']}"
    assert coordinator.data["next_trip"]["descripcion"] == "Viaje de prueba"


async def test_coordinator_updates_after_creating_trip_via_service(
    hass: HomeAssistant, mock_trip_manager
):
    """Test T034: Coordinator se actualiza después de crear trip (US4).

    Este test verifica el flujo completo cuando un usuario crea un trip
    mediante el servicio.
    """
    # 1. Crear coordinator
    from homeassistant.config_entries import ConfigEntryState
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED

    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)

    # 2. Forzar primera actualización
    await coordinator.async_refresh()

    # 3. Verificar estado inicial (sin trips)
    assert coordinator.data["recurring_trips"] == []
    assert coordinator.data["punctual_trips"] == []

    # 4. Simular que el trip_manager guarda un nuevo trip
    new_recurring_trip = {
        "id": "new_recurring_1",
        "origin": "Home",
        "destination": "Office",
        "departure_time": "08:00",
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "distance_km": 25,
        "energy_kwh": 5.0,
    }

    # Configurar mock para devolver el nuevo trip
    mock_trip_manager.async_get_recurring_trips = AsyncMock(
        return_value=[new_recurring_trip]
    )
    mock_trip_manager.async_add_recurring_trip = AsyncMock()

    # 5. Simular el flujo del servicio después de añadir un trip
    await mock_trip_manager.async_add_recurring_trip(
        dia_semana="lunes",
        hora="08:00",
        km=25.0,
        kwh=5.0,
        descripcion="Viaje al trabajo",
    )

    # 6. Forzar refresh del coordinator
    await coordinator.async_refresh()

    # 7. Verificar que el coordinator.data se actualizó correctamente
    assert coordinator.data["recurring_trips"] == [new_recurring_trip]


async def test_coordinator_updates_after_creating_punctual_trip(
    hass: HomeAssistant, mock_trip_manager
):
    """Test T034b: Coordinator se actualiza después de crear trip puntual."""
    # 1. Crear coordinator
    from homeassistant.config_entries import ConfigEntryState
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)

    # 2. Forzar primera actualización
    await coordinator.async_refresh()

    # 3. Verificar estado inicial
    assert coordinator.data["punctual_trips"] == []

    # 4. Simular nuevo trip puntual
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

    # 5. Forzar refresh
    await coordinator.async_refresh()

    # 6. Verificar actualización
    assert coordinator.data["punctual_trips"] == [new_punctual_trip]


async def test_coordinator_data_updates_for_all_trip_types(
    hass: HomeAssistant, mock_trip_manager
):
    """Test T034c: Coordinator actualiza datos para todos los tipos de trips."""
    # 1. Crear coordinator
    from homeassistant.config_entries import ConfigEntryState
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)

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

    # 4. Forzar refresh
    await coordinator.async_refresh()

    # 5. Verificar que coordinator.data tiene todos los trips
    assert coordinator.data["recurring_trips"] == mock_recurring
    assert coordinator.data["punctual_trips"] == mock_punctual

    # 6. Verificar que los conteos son correctos
    assert len(coordinator.data["recurring_trips"]) == 1
    assert len(coordinator.data["punctual_trips"]) == 1


async def test_refresh_propagates_to_all_sensors(hass: HomeAssistant, mock_trip_manager):
    """Test T035: Refresh se propaga a todos los sensores (US4)."""
    from custom_components.ev_trip_planner.sensor import (
        RecurringTripsCountSensor,
        PunctualTripsCountSensor,
        TripsListSensor,
        KwhTodaySensor,
        HoursTodaySensor,
        NextTripSensor,
        NextDeadlineSensor,
    )

    # 1. Crear coordinator
    from homeassistant.config_entries import ConfigEntryState
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)

    # 2. Forzar primera actualización
    await coordinator.async_refresh()

    # 3. Crear TODOS los sensores del componente
    sensors = {
        "recurring": RecurringTripsCountSensor("test_vehicle", coordinator),
        "punctual": PunctualTripsCountSensor("test_vehicle", coordinator),
        "trips_list": TripsListSensor("test_vehicle", coordinator),
        "kwh_today": KwhTodaySensor("test_vehicle", coordinator),
        "hours_today": HoursTodaySensor("test_vehicle", coordinator),
        "next_trip": NextTripSensor("test_vehicle", coordinator),
        "next_deadline": NextDeadlineSensor("test_vehicle", coordinator),
    }

    # 4. Verificar valores iniciales (sin trips)
    assert sensors["recurring"].native_value == 0
    assert sensors["punctual"].native_value == 0
    assert sensors["trips_list"].native_value == 0
    assert sensors["kwh_today"].native_value == 0.0
    assert sensors["hours_today"].native_value == 0
    assert sensors["next_trip"].native_value == "No trips"
    assert sensors["next_deadline"].native_value is None

    # 5. Simular cambios en trip_manager
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

    # 6. Forzar refresh del coordinator
    await coordinator.async_refresh()

    # 7. Verificar que TODOS los sensores tienen los valores actualizados
    assert sensors["recurring"].native_value == 1
    assert sensors["punctual"].native_value == 1
    assert sensors["trips_list"].native_value == 2
    assert sensors["kwh_today"].native_value == 7.5
    assert sensors["hours_today"].native_value == 2
    assert sensors["next_trip"].native_value == "Viaje importante"
    assert sensors["next_deadline"].native_value == "2025-12-01T10:00:00"

    # 8. Verificar que coordinator.data también se actualizó correctamente
    assert coordinator.data["recurring_trips"] == mock_recurring
    assert coordinator.data["punctual_trips"] == mock_punctual
    assert coordinator.data["kwh_today"] == 7.5
    assert coordinator.data["hours_today"] == 2
    assert coordinator.data["next_trip"]["descripcion"] == "Viaje importante"
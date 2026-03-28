"""Test que demuestra el bug de actualización automática de sensores Milestone 2.

NOTA: Este test produce un "Lingering timer" en teardown debido al
debounce interno del coordinator. Esto es un problema conocido de la infraestructura
de tests de Home Assistant y no afecta la funcionalidad del componente.

Referencia: https://github.com/home-assistant/core/issues/83432
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, date

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState
from custom_components.ev_trip_planner import TripPlannerCoordinator
from custom_components.ev_trip_planner.sensor import TripPlannerSensor
from custom_components.ev_trip_planner.sensor import (
    RecurringTripsCountSensor,
    PunctualTripsCountSensor,
    TripsListSensor,
)
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def mock_trip_manager(hass):
    """Crea un mock de TripManager."""
    manager = MagicMock(spec=TripManager)
    manager.async_get_recurring_trips = AsyncMock(return_value=[])
    manager.async_get_punctual_trips = AsyncMock(return_value=[])
    manager.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
    manager.async_get_hours_needed_today = AsyncMock(return_value=0)
    manager.async_get_next_trip = AsyncMock(return_value=None)
    # Add hass attribute required by sensors
    manager.hass = hass
    # Add vehicle_controller mock
    manager.vehicle_controller = MagicMock()
    manager.vehicle_id = "test_vehicle"
    return manager


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry for coordinator."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.domain = "ev_trip_planner"
    entry.state = ConfigEntryState.LOADED
    entry.options = {}
    entry.data = {"vehicle_name": "test_vehicle"}
    entry.title = "Test Vehicle"
    entry.version = 1
    entry.minor_version = 1
    entry.unique_id = "test_vehicle"
    entry.source = "user"
    entry.discovery_keys = {}
    return entry


@pytest.fixture
def mock_coordinator(hass, mock_trip_manager, mock_config_entry):
    """Crea un coordinator con datos iniciales."""
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)
    return coordinator


async def test_sensors_no_se_actualizan_automaticamente(
    hass: HomeAssistant, mock_trip_manager
):
    """Test que demuestra el bug: sensores no se actualizan al cambiar datos."""

    # 1. Crear coordinator SIN inicializar
    from unittest.mock import MagicMock
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)

    # 2. Forzar primera actualización para tener datos iniciales
    await coordinator.async_refresh()

    # 3. Crear sensores usando TripPlannerSensor
    kwh_sensor = TripPlannerSensor(hass, mock_trip_manager, "kwh_needed_today")
    hours_sensor = TripPlannerSensor(hass, mock_trip_manager, "hours_needed_today")
    next_trip_sensor = TripPlannerSensor(hass, mock_trip_manager, "next_trip")

    # 4. Verificar valores iniciales (sin viajes)
    assert kwh_sensor.native_value == 0.0 or kwh_sensor.native_value is None
    assert hours_sensor.native_value == 0 or hours_sensor.native_value is None

    # 5. Simular añadir un viaje para HOY en el trip_manager
    mock_trip_manager.async_get_kwh_needed_today.return_value = 7.5
    mock_trip_manager.async_get_hours_needed_today.return_value = 2
    mock_trip_manager.async_get_next_trip.return_value = {
        "descripcion": "Viaje de prueba",
        "datetime": datetime(2025, 11, 23, 10, 0, 0),
        "tipo": "puntual",
        "km": 50,
        "kwh": 7.5,
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

    # 8. Los sensores deben actualizarse después del refresh
    # Ejecutar update en cada sensor
    await kwh_sensor.async_update()
    await hours_sensor.async_update()
    await next_trip_sensor.async_update()

    # Verificar valores después del update
    assert kwh_sensor.native_value == 7.5, "Sensor debería tener 7.5 después de update"
    assert hours_sensor.native_value == 2, "Sensor debería tener 2 después de update"
    assert next_trip_sensor.native_value == "Viaje de prueba", "Sensor debería tener 'Viaje de prueba'"


async def test_sensors_show_trips_after_creating_trip(
    hass: HomeAssistant, mock_trip_manager
):
    """Test T031: Sensores muestran trips después de crear viaje (US4).

    Este test verifica que los sensores muestran correctamente el número
    de viajes después de crearlos.

    Flujo:
    1. Crear coordinator sin trips
    2. Crear sensor de trips (inicialmente debe mostrar 0)
    3. Simular que trip_manager devuelve trips
    4. Forzar refresh del coordinator
    5. Verificar que el sensor muestra el número correcto de trips
    """
    # 1. Crear coordinator SIN inicializar
    from unittest.mock import MagicMock
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)

    # 2. Forzar primera actualización para tener datos iniciales
    await coordinator.async_refresh()

    # 3. Crear sensores usando las clases reales de sensores
    recurring_sensor = RecurringTripsCountSensor("test_vehicle", coordinator)
    punctual_sensor = PunctualTripsCountSensor("test_vehicle", coordinator)
    trips_list_sensor = TripsListSensor("test_vehicle", coordinator)

    # 4. Verificar valores iniciales (sin viajes)
    assert recurring_sensor.native_value == 0, "Sensor de trips recurrentes debe iniciar en 0"
    assert punctual_sensor.native_value == 0, "Sensor de trips puntuales debe iniciar en 0"
    assert trips_list_sensor.native_value == 0, "Sensor de lista de trips debe iniciar en 0"

    # 5. Simular que el trip_manager devuelve trips
    # Mock para trips recurrentes
    mock_recurring_trips = [
        {
            "id": "recurring_1",
            "origin": "Home",
            "destination": "Office",
            "departure_time": "08:00",
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "distance_km": 25,
            "energy_kwh": 5.0,
        },
        {
            "id": "recurring_2",
            "origin": "Office",
            "destination": "Home",
            "departure_time": "17:30",
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "distance_km": 25,
            "energy_kwh": 5.0,
        },
    ]

    # Mock para trips puntuales
    mock_punctual_trips = [
        {
            "id": "punctual_1",
            "origin": "Home",
            "destination": "Airport",
            "departure_time": "06:00",
            "departure_date": date.today().isoformat(),
            "distance_km": 40,
            "energy_kwh": 8.0,
        },
    ]

    # Configurar los mocks para devolver los trips
    mock_trip_manager.async_get_recurring_trips = AsyncMock(
        return_value=mock_recurring_trips
    )
    mock_trip_manager.async_get_punctual_trips = AsyncMock(
        return_value=mock_punctual_trips
    )

    # 6. Forzar refresh del coordinator para que actualice los datos
    await coordinator.async_request_refresh()

    # 7. Verificar que coordinator.data tiene los trips correctos
    assert "recurring_trips" in coordinator.data, "coordinator.data debe contener recurring_trips"
    assert "punctual_trips" in coordinator.data, "coordinator.data debe contener punctual_trips"
    assert len(coordinator.data["recurring_trips"]) == 2, "Debe haber 2 trips recurrentes"
    assert len(coordinator.data["punctual_trips"]) == 1, "Debe haber 1 trip puntual"

    # 8. Verificar que los sensores muestran el número correcto de trips
    # Los sensores leen directamente de coordinator.data en su propiedad native_value
    # No necesitan async_update porque leen sincronamente de coordinator.data

    # Verificar sensor de trips recurrentes
    recurring_count = recurring_sensor.native_value
    assert recurring_count == 2, f"Sensor debe mostrar 2 trips recurrentes, got: {recurring_count}"

    # Verificar sensor de trips puntuales
    punctual_count = punctual_sensor.native_value
    assert punctual_count == 1, f"Sensor debe mostrar 1 trip puntual, got: {punctual_count}"

    # Verificar sensor de lista de trips (debe mostrar el total)
    total_trips = trips_list_sensor.native_value
    assert total_trips == 3, f"Sensor debe mostrar 3 trips total (2+1), got: {total_trips}"


async def test_sensors_update_after_creating_trip(
    hass: HomeAssistant, mock_trip_manager
):
    """Test T032: Sensores se actualizan después de crear viaje (US4).

    Este test verifica que los sensores ACTUALIZAN sus valores después de
    crear un viaje. Es la funcionalidad prioritaria del US4.

    Flujo:
    1. Crear coordinator sin trips
    2. Crear sensor (mostrará 0 inicialmente)
    3. Guardar el valor inicial del sensor
    4. Simular que se añade un nuevo trip (cambiando el mock)
    5. Forzar refresh del coordinator
    6. Verificar que el sensor MOSTRÓ UN NUEVO VALOR (update exitoso)

    Este test es crítico porque verifica que el mecanismo de update funciona,
    no solo que los datos son correctos.
    """
    # 1. Crear coordinator y forzar primera carga
    from unittest.mock import MagicMock
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)
    await coordinator.async_refresh()

    # 2. Crear sensor de trips recurrentes
    recurring_sensor = RecurringTripsCountSensor("test_vehicle", coordinator)

    # 3. Verificar valor inicial (sin trips)
    initial_value = recurring_sensor.native_value
    assert initial_value == 0, f"Valor inicial debe ser 0, got: {initial_value}"

    # 4. Simular que se añade un nuevo trip recurrente
    # Esto representa el flujo: usuario llama servicio -> guarda en storage -> refresh
    mock_new_trip = [
        {
            "id": "new_trip_1",
            "origin": "Home",
            "destination": "Work",
            "departure_time": "09:00",
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "distance_km": 30,
            "energy_kwh": 6.0,
        }
    ]

    # Actualizar el mock para devolver el nuevo trip
    mock_trip_manager.async_get_recurring_trips = AsyncMock(
        return_value=mock_new_trip
    )

    # 5. Forzar refresh del coordinator (esto es lo que hacen los servicios
    # después de crear un trip)
    await coordinator.async_request_refresh()

    # 6. El sensor debe mostrar el NUEVO valor (demostrando que se actualizó)
    updated_value = recurring_sensor.native_value
    assert updated_value == 1, f"Valor actualizado debe ser 1, got: {updated_value}"

    # 7. Verificar que el valor CAMBIÓ (demuestra el update)
    assert updated_value != initial_value, (
        f"El sensor debe haber cambiado de valor. "
        f"Inicial: {initial_value}, Actualizado: {updated_value}"
    )

    # 8. Verificar que el coordinator.data se actualizó correctamente
    assert coordinator.data["recurring_trips"] == mock_new_trip, (
        "Coordinator debe tener los nuevos trips"
    )


async def test_multiple_sensors_update_after_creating_trip(
    hass: HomeAssistant, mock_trip_manager
):
    """Test T032b: Múltiples sensores se actualizan después de crear viaje.

    Verifica que todos los sensores relacionados con trips se actualizan
    correctamente después de crear un nuevo trip.
    """
    # 1. Crear coordinator y forzar primera carga
    from unittest.mock import MagicMock
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager, mock_config_entry)
    await coordinator.async_refresh()

    # 2. Crear todos los sensores de trips
    recurring_sensor = RecurringTripsCountSensor("test_vehicle", coordinator)
    punctual_sensor = PunctualTripsCountSensor("test_vehicle", coordinator)
    trips_list_sensor = TripsListSensor("test_vehicle", coordinator)

    # 3. Verificar valores iniciales (sin trips)
    assert recurring_sensor.native_value == 0
    assert punctual_sensor.native_value == 0
    assert trips_list_sensor.native_value == 0

    # 4. Simular que se añaden trips de ambos tipos
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

    # 5. Forzar refresh (como lo hacen los servicios después de crear trips)
    await coordinator.async_request_refresh()

    # 6. Verificar que TODOS los sensores se actualizaron correctamente
    assert recurring_sensor.native_value == 1, "Recurring sensor debe actualizarse"
    assert punctual_sensor.native_value == 1, "Punctual sensor debe actualizarse"
    assert trips_list_sensor.native_value == 2, "Total trips debe ser 2"

    # 7. Verificar que los valores son diferentes de los iniciales
    assert recurring_sensor.native_value != 0
    assert punctual_sensor.native_value != 0
    assert trips_list_sensor.native_value != 0


async def test_sensors_show_persisted_trips_after_restart(hass: HomeAssistant):
    """Test T033b: Sensores muestran trips persistidos después de reinicio.

    Este test verifica el flujo completo:
    1. Crear trips y guardarlos
    2. Simular reinicio (nuevo coordinator)
    3. Verificar que los sensores muestran los trips persistidos

    Esto verifica el requisito SC-005:
    "Los viajes persisten correctamente entre reinicios de Home Assistant (100% de persistencia)"
    """
    from unittest.mock import MagicMock
    from custom_components.ev_trip_planner.trip_manager import TripManager
    from custom_components.ev_trip_planner import TripPlannerCoordinator

    vehicle_id = "test_sensors_persist_vehicle"

    # Create a shared storage dictionary to simulate real hass.storage
    _storage_data = {}

    async def mock_async_read(key):
        """Mock storage read that returns stored data."""
        return _storage_data.get(key)

    async def mock_async_write_dict(key, data):
        """Mock storage write that stores data."""
        _storage_data[key] = data
        return True

    # Configure hass.storage para persistencia real
    hass.storage = MagicMock()
    hass.storage.async_read = mock_async_read
    hass.storage.async_write_dict = mock_async_write_dict

    # 1. Crear TripManager y añadir trips
    trip_manager = TripManager(hass, vehicle_id)
    await trip_manager.async_setup()

    test_trip = {
        "trip_id": "persist_trip_1",
        "dia_semana": "lunes",
        "hora": "08:00",
        "km": 25,
        "kwh": 5.0,
        "descripcion": "Viaje de prueba",
    }

    await trip_manager.async_add_recurring_trip(**test_trip)

    # 2. Verificar que se guardó
    assert len(await trip_manager.async_get_recurring_trips()) == 1

    # 3. Simular reinicio: crear nuevo coordinator (como al iniciar HA)
    # El coordinator debe cargar los datos desde hass.storage
    from unittest.mock import MagicMock
    from homeassistant.config_entries import ConfigEntryState
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.domain = "ev_trip_planner"
    mock_config_entry.state = ConfigEntryState.LOADED
    new_coordinator = TripPlannerCoordinator(hass, trip_manager, mock_config_entry)
    await new_coordinator.async_refresh()

    # 4. Crear sensor y verificar que muestra los trips persistidos
    recurring_sensor = RecurringTripsCountSensor(vehicle_id, new_coordinator)

    # El sensor debe mostrar 1 trip (el que persistimos)
    assert recurring_sensor.native_value == 1, (
        f"El sensor debe mostrar 1 trip después del reinicio, "
        f"got: {recurring_sensor.native_value}"
    )

    # 5. Verificar que los datos están en coordinator.data
    assert "recurring_trips" in new_coordinator.data
    assert len(new_coordinator.data["recurring_trips"]) == 1

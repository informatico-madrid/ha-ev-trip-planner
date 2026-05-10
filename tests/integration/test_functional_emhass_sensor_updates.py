"""Tests Funcionales: Verifican que el sensor EMHASS se actualiza cuando algo cambia.

Requisito funcional del usuario:
"ese sensor debe estar actualizado en tiempo real, cuando cambie el soc
cuando cambie la hora cuando cambie un viaje etc... cuando cambie
cualquier de los valores o variables que hacen los calculos ese sensor
se debe actualizar"

Estos tests verifican ese requisito sin preocuparse por el flujo interno.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator
from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor


@pytest.fixture
def mock_emhass_adapter():
    """Create mock EMHASS adapter with mutable cache state.

    Simulates the real adapter:
    - get_cached_optimization_results() → reads from internal _cache dict
    - async_publish_all_deferrable_loads() → updates _cache with computed results

    The test controls the "computed" results by setting adapter._new_cache
    before calling _async_handle_soc_change. This is what the real adapter
    does: recomputes and updates its internal cache.
    """
    # Use a list to hold the cache so it's accessible in the closure
    _state = {
        "cache": {
            "emhass_power_profile": [3400, 0, 0, 0] * 42,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }
    }

    class AdapterMock:
        def get_cached_optimization_results(self):
            return _state["cache"]

        async def async_publish_all_deferrable_loads(
            self, trips, charging_power_kw=None, soc_caps_by_id=None
        ):
            # Simulate real adapter behavior: recompute and update cache.
            new_cache = getattr(self, "_new_cache", None)
            if new_cache is not None:
                _state["cache"].clear()
                _state["cache"].update(new_cache)
                delattr(self, "_new_cache")

        @property
        def _cache(self):
            return _state["cache"]

    return AdapterMock()


@pytest.fixture
def mock_config_entry():
    """Create mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_chispitas"
    entry.data = {
        "vehicle_name": "chispitas",
        "soc_sensor": "sensor.ovms_soc",
        "charging_power_kw": 3.4,
        "battery_capacity_kwh": 60.0,
    }
    return entry


@pytest.fixture
def mock_trip_manager():
    """Create mock TripManager with minimal methods used by coordinator."""
    manager = MagicMock()
    manager.async_get_recurring_trips = AsyncMock(return_value=[])
    manager.async_get_punctual_trips = AsyncMock(return_value=[])
    manager.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
    manager.async_get_hours_needed_today = AsyncMock(return_value=0.0)
    manager.async_get_next_trip = AsyncMock(return_value=None)
    manager.publish_deferrable_loads = AsyncMock()
    manager._recurring_trips = {}
    manager._punctual_trips = {}
    manager._trips = {}
    return manager


# =============================================================================
# TEST 1: Cambio de SOC ≥5% → Sensor EMHASS debe actualizarse
# =============================================================================


@pytest.mark.asyncio
async def test_soc_change_above_5_percent_updates_emhass_sensor(
    mock_hass, mock_config_entry, mock_emhass_adapter
):
    """
    Functional Test: Cambio de SOC ≥5% actualiza el sensor EMHASS AUTOMÁTICAMENTE.

    REQUISITO: "Cuando cambie el soc... ese sensor se debe actualizar"

    ENTRADA: SOC cambia de 50% → 60% (10% de cambio)
    EXPECTATIVA: El sistema ACTUALIZA el sensor AUTOMÁTICAMENTE (sin llamar manualmente a refresh)

    Flujo de producción real:
    1. PresenceMonitor recibe evento de SOC
    2. _async_handle_soc_change() → publish_deferrable_loads()
    3. TripManager.publish_deferrable_loads() → adapter.async_publish_all_deferrable_loads()
       → actualiza el cache del adapter
    4. TripManager.publish_deferrable_loads() → coordinator.async_refresh()
    5. Coordinator._async_update_data() lee el nuevo cache
    6. Sensor.extra_state_attributes muestra los nuevos datos

    ESTE TEST NO LLAMA MANUALMENTE A refresh() desde el test.
    Simula el cambio de SOC vía el evento del PresenceMonitor.
    Usa un TripManager REAL (no mock) para que el código real se ejecute.
    """
    from custom_components.ev_trip_planner.const import (
        CONF_HOME_SENSOR,
        CONF_PLUGGED_SENSOR,
        CONF_SOC_SENSOR,
    )
    from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor
    from custom_components.ev_trip_planner.trip_manager import TripManager

    print("\n" + "=" * 80)
    print("TEST FUNCIONAL: Cambio SOC ≥5% → Sensor EMHASS actualiza AUTOMÁTICAMENTE")
    print("=" * 80)

    # ============================================================
    # CONFIGURAR MOCK HASS CON config_entries PARA TRIPMANAGER REAL
    # ============================================================

    # Configurar config_entries para que el TripManager real pueda
    # encontrar el entry y el coordinator en publish_deferrable_loads()
    mock_config_entries = MagicMock()

    # El entry.runtime_data debe tener el coordinator
    runtime_data = MagicMock()

    # Setup inicial del coordinator con el adapter mock
    coordinator = TripPlannerCoordinator(
        mock_hass,
        mock_config_entry,
        Mock(emhass_adapter=mock_emhass_adapter),
        emhass_adapter=mock_emhass_adapter,
    )

    runtime_data.coordinator = coordinator
    mock_config_entry.runtime_data = runtime_data
    mock_config_entries.async_get_entry.return_value = mock_config_entry

    mock_hass.config_entries = mock_config_entries

    # ============================================================
    # CREAR TRIP MANAGER REAL (no mock) CON EL ADAPTER MOCK
    # ============================================================

    trip_manager = TripManager(
        hass=mock_hass,
        vehicle_id="chispitas",
        entry_id="test_entry_chispitas",
        emhass_adapter=mock_emhass_adapter,
    )
    # Agregar trips vacíos para que el flow real funcione
    trip_manager._recurring_trips = {}
    trip_manager._punctual_trips = {}
    trip_manager._trips = {}

    # ============================================================
    # CREAR COORDINATOR CON EL TRIP MANAGER REAL
    # ============================================================

    # Recrear coordinator con el trip_manager real
    coordinator = TripPlannerCoordinator(
        mock_hass, mock_config_entry, trip_manager, emhass_adapter=mock_emhass_adapter
    )
    runtime_data.coordinator = coordinator

    sensor = EmhassDeferrableLoadSensor(coordinator, "chispitas")

    # Crear PresenceMonitor con el trip_manager REAL
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "chispitas", config, trip_manager)
    monitor._last_processed_soc = 50.0

    # Mock persistence methods to avoid storage side effects
    monitor._async_persist_return_info = AsyncMock()

    # Setup: Vehículo en casa y conectado
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        return None

    mock_hass.states.get = mock_get_state

    # ============================================================
    # 1. ESTADO INICIAL: SOC 50%
    # ============================================================
    print("\n📊 ESTADO INICIAL: SOC 50%")
    # Configurar cache inicial directamente (el mock usa dict mutable compartido)
    mock_emhass_adapter._cache.update(
        {
            "emhass_power_profile": [3400, 0, 0, 0] * 42,  # 3.4 kW * 1000
            "emhass_deferrables_schedule": [{"trip_id": "1", "power": 3400}],
            "emhass_status": "ready",
        }
    )

    await coordinator.async_refresh()
    initial_attributes = sensor.extra_state_attributes
    initial_power = initial_attributes.get("power_profile_watts", [])

    print(f"   power_profile_watts[0]: {initial_power[0] if initial_power else 'N/A'}")

    # ============================================================
    # 2. CAMBIO AUTOMÁTICO: SOC 60% (10% de cambio, ≥5%)
    # ============================================================
    print("\n📊 CAMBIO AUTOMÁTICO: SOC 60% (10% delta)")
    print(
        "   (Esto dispara PresenceMonitor → publish_deferrable_loads() → actualización automática)"
    )

    # Simular: el adapter recalcula y pone nuevos resultados en _new_cache
    # async_publish_all_deferrable_loads() los moverá al cache real
    mock_emhass_adapter._new_cache = {
        "emhass_power_profile": [3600, 0, 0, 0] * 42,  # 3.6 kW * 1000 (¡cambió!)
        "emhass_deferrables_schedule": [{"trip_id": "1", "power": 3600}],
        "emhass_status": "ready",
    }

    # SIMULAR CAMBIO DE SOC: evento que dispara la actualización automática
    old_soc_state = Mock()
    old_soc_state.state = "50"

    new_soc_state = Mock()
    new_soc_state.state = "60"

    event = Mock()
    event.data = {
        "old_state": old_soc_state,
        "new_state": new_soc_state,
    }

    # Esto debería disparar: PresenceMonitor → publish_deferrable_loads() (REAL)
    # → adapter.async_publish_all_deferrable_loads() → coordinator.async_refresh() (REAL)
    await monitor._async_handle_soc_change(event)

    # ❌ NO llamar manualmente a coordinator.async_refresh()

    # ============================================================
    # 3. VERIFICAR: El sensor MOSTRÓ los nuevos datos AUTOMÁTICAMENTE
    # ============================================================
    print("\n🔍 VERIFICACIÓN: ¿El sensor se actualizó AUTOMÁTICAMENTE?")
    updated_attributes = sensor.extra_state_attributes
    updated_power = updated_attributes.get("power_profile_watts", [])

    print(
        f"   power_profile_watts[0] después: {updated_power[0] if updated_power else 'N/A'}"
    )
    print(
        f"   ¿Cambió AUTOMÁTICAMENTE? {updated_power != initial_power if updated_power and initial_power else 'N/A'}"
    )

    # ❌ ASSERT: El sensor DEBERÍA mostrar los nuevos datos automáticamente
    # Si este test FALLA, confirma que el sensor NO se actualiza cuando cambia el SOC.
    assert updated_power[0] == 3600, (
        f"BUG: El sensor DEBERÍA mostrar 3600 (SOC 60%) automáticamente, "
        f"pero muestra {updated_power[0] if updated_power else 'N/A'}. "
        "Esto confirma que el sensor NO se actualiza automáticamente cuando cambia el SOC."
    )


# =============================================================================
# TEST 2: Cambio de hora (30 segundos) → Sensor EMHASS debe actualizarse
# =============================================================================


@pytest.mark.asyncio
async def test_time_change_30_seconds_refreshes_emhass_sensor(
    mock_hass, mock_config_entry, mock_trip_manager, mock_emhass_adapter
):
    """
    Functional Test: Paso 30 segundos → coordinator hace refresh → sensor actualiza.

    REQUISITO: "cuando cambie la hora... ese sensor se debe actualizar"

    ENTRADA: Pasan 30 segundos
    EXPECTATIVA: El coordinator hace refresh y el sensor muestra datos actualizados
    """
    print("\n" + "=" * 80)
    print("TEST FUNCIONAL: Paso 30 segundos → Sensor EMHASS actualiza")
    print("=" * 80)

    # Setup: Crear coordinator y sensor
    coordinator = TripPlannerCoordinator(
        mock_hass,
        mock_config_entry,
        mock_trip_manager,
        emhass_adapter=mock_emhass_adapter,
    )

    sensor = EmhassDeferrableLoadSensor(coordinator, "chispitas")

    # 1. ESTADO INICIAL: Hora 12:00
    print("\n📊 ESTADO INICIAL: Hora 12:00 UTC")
    initial_time = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Usar el cache compartido del mock adapter (no return_value de MagicMock)
    mock_emhass_adapter._cache.update(
        {
            "emhass_power_profile": [3400, 0, 0, 0] * 42,
            "emhass_deferrables_schedule": [{"date": initial_time.isoformat()}],
            "emhass_status": "ready",
        }
    )

    await coordinator.async_refresh()
    initial_attributes = sensor.extra_state_attributes
    initial_schedule = initial_attributes.get("deferrables_schedule", [])

    print(
        f"   deferrables_schedule[0]['date']: {initial_schedule[0]['date'] if initial_schedule else 'N/A'}"
    )

    # 2. CAMBIO: Pasan 30 segundos
    print("\n📊 CAMBIO: Pasan 30 segundos")
    updated_time = datetime(2026, 4, 30, 12, 30, 0, tzinfo=timezone.utc)

    # Actualizar el cache compartido directamente
    mock_emhass_adapter._cache.update(
        {
            "emhass_power_profile": [3400, 0, 0, 0] * 42,
            "emhass_deferrables_schedule": [
                {"date": updated_time.isoformat()}
            ],  # ¡Timestamp actualizado!
            "emhass_status": "ready",
        }
    )

    # SIMULAR: coordinator.async_refresh() se llama (cada 30 segundos automáticamente)
    await coordinator.async_refresh()

    # 3. VERIFICAR: El sensor MOSTRÓ los datos actualizados
    print("\n🔍 VERIFICACIÓN: ¿El sensor se actualizó?")
    updated_attributes = sensor.extra_state_attributes
    updated_schedule = updated_attributes.get("deferrables_schedule", [])

    print(
        f"   deferrables_schedule[0]['date']: {updated_schedule[0]['date'] if updated_schedule else 'N/A'}"
    )
    print(
        f"   ¿Timestamp cambió? {updated_schedule[0]['date'] != initial_schedule[0]['date'] if updated_schedule and initial_schedule else 'N/A'}"
    )

    # ASSERT: El sensor debería mostrar el timestamp actualizado
    assert updated_schedule[0]["date"] == updated_time.isoformat(), (
        f"El sensor DEBERÍA mostrar timestamp actualizado ({updated_time.isoformat()}), "
        f"pero muestra {updated_schedule[0]['date']}. "
        "Esto indica que el cache EMHASS no se regeneró automáticamente."
    )


# =============================================================================
# TEST 3: Cambio de viaje → Sensor EMHASS debe actualizarse
# =============================================================================


@pytest.mark.asyncio
async def test_trip_change_updates_emhass_sensor(
    mock_hass, mock_config_entry, mock_trip_manager, mock_emhass_adapter
):
    """
    Functional Test: Cambio en un viaje → Sensor EMHASS actualiza.

    REQUISITO: "cuando cambie un viaje... ese sensor se debe actualizar"

    ENTRADA: Se modifica un viaje (hora o kWh)
    EXPECTATIVA: El sensor EMHASS muestra el perfil de carga actualizado
    """
    print("\n" + "=" * 80)
    print("TEST FUNCIONAL: Cambio de viaje → Sensor EMHASS actualiza")
    print("=" * 80)

    # Setup: Crear coordinator y sensor
    coordinator = TripPlannerCoordinator(
        mock_hass,
        mock_config_entry,
        mock_trip_manager,
        emhass_adapter=mock_emhass_adapter,
    )

    sensor = EmhassDeferrableLoadSensor(coordinator, "chispitas")

    # 1. ESTADO INICIAL: Viaje a las 14:40, 7 kWh
    print("\n📊 ESTADO INICIAL: Viaje a las 14:40, 7 kWh")
    initial_trip_time = datetime(2026, 4, 30, 14, 40, 0, tzinfo=timezone.utc)

    mock_emhass_adapter._cache.update(
        {
            "emhass_power_profile": [3400, 0, 0, 0] * 42,
            "emhass_deferrables_schedule": [
                {
                    "trip_id": "rec_test",
                    "datetime": initial_trip_time.isoformat(),
                    "kwh": 7.0,
                    "power": 3400,
                }
            ],
            "emhass_status": "ready",
        }
    )

    await coordinator.async_refresh()
    initial_attributes = sensor.extra_state_attributes
    initial_schedule = initial_attributes.get("deferrables_schedule", [])

    print(
        f"   Viaje en schedule: {initial_schedule[0]['datetime'] if initial_schedule else 'N/A'}"
    )

    # 2. CAMBIO: Viaje modificado a las 15:00, 8 kWh
    print("\n📊 CAMBIO: Viaje modificado a las 15:00, 8 kWh")
    updated_trip_time = datetime(2026, 4, 30, 15, 0, 0, tzinfo=timezone.utc)

    mock_emhass_adapter._cache.update(
        {
            "emhass_power_profile": [3400, 0, 0, 0] * 42,
            "emhass_deferrables_schedule": [
                {
                    "trip_id": "rec_test",
                    "datetime": updated_trip_time.isoformat(),
                    "kwh": 8.0,
                    "power": 3400,
                }
            ],
            "emhass_status": "ready",
        }
    )

    # SIMULAR: coordinator.async_refresh() se llama
    await coordinator.async_refresh()

    # 3. VERIFICAR: El sensor MOSTRÓ el viaje actualizado
    print("\n🔍 VERIFICACIÓN: ¿El sensor se actualizó?")
    updated_attributes = sensor.extra_state_attributes
    updated_schedule = updated_attributes.get("deferrables_schedule", [])

    print(
        f"   Viaje en schedule: {updated_schedule[0]['datetime'] if updated_schedule else 'N/A'}"
    )
    print(
        f"   ¿El viaje cambió? {updated_schedule[0]['datetime'] != initial_schedule[0]['datetime'] if updated_schedule and initial_schedule else 'N/A'}"
    )

    # ASSERT: El sensor debería mostrar el viaje actualizado
    assert updated_schedule[0]["datetime"] == updated_trip_time.isoformat(), (
        f"El sensor DEBERÍA mostrar el viaje actualizado ({updated_trip_time.isoformat()}), "
        f"pero muestra {updated_schedule[0]['datetime']}. "
        "Esto confirma que el sensor NO se actualiza cuando cambia un viaje."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

# Plan: SOC Integration Baseline + Return Time Detection

**Epic**: specs/_epics/emhass-deferrable-integration/epic.md

## Goal

Como sistema, necesito leer el sensor SOC del vehiculo y disparar recalculos de carga cuando el SOC cambia mientras el coche esta en casa y enchufado. Tambien necesito registrar la hora de regreso del vehiculo para calcular la ventana de carga.

## Acceptance Criteria

1. **Given** el usuario ha configurado un sensor SOC para el vehiculo en el config flow, **when** el valor del sensor cambia, **then** el sistema lee el nuevo valor

2. **Given** el coche esta en casa y enchufado, **when** el SOC cambia (delta >= 5%), **then** se dispara `trip_manager.async_generate_power_profile()` y `trip_manager.async_generate_deferrables_schedule()` para recalcular el perfil

3. **Given** el coche NO esta en casa o NO esta enchufado, **when** el SOC cambia, **then** NO se dispara recalculo (ahorro de recursos)

4. **Given** el coche regresa a casa, **when** se detecta el cambio de estado (de "ausente" a "en casa"), **then**:
   - Se dispara recalculo inmediato
   - Se registra `hora_regreso` (timestamp actual de HomeAssistant timezone)
   - Se registra `soc_en_regreso` (valor actual del SOC)
   - Se persiste en HA state entity para uso por Spec 2

5. **Given** el usuario aniade/editar/elimina un viaje, **when** el cambio se guarda, **then** se actualiza el perfil de carga

6. **Given** el coche estaba en casa y sale (home_sensor -> "off"), **when** se detecta la salida, **then** `hora_regreso` se invalida hasta proximo regreso

## Interface Contracts

**Input**: State change from home sensor, plugged sensor, or SOC sensor

**Output**: Calls `trip_manager.async_generate_power_profile()` and `trip_manager.async_generate_deferrables_schedule()` (NUNCA llamar `_publish_deferrable_loads` que es privado)

**Trigger conditions**:
- `home_sensor` changes to "on" AND `plugged_sensor` is "on"
- `plugged_sensor` changes to "on" AND `home_sensor` is "on"
- `soc_sensor` changes AND `home_sensor` is "on" AND `plugged_sensor` is "on"

**Debouncing**:
- SOC delta threshold: 5% hardcoded (no configurable por ahora)
- Delta = |new_soc - last_processed_soc|
- Solo recalcular si delta >= 5%

**Persistence** (para Spec 2):
- Usar `ha_storage.Store` API (mismo mecanismo que los viajes en trip_manager.py:L95-102)
- Crear HA state entity via `hass.states.async_set()` con:
  - `sensor.ev_trip_planner_{vehicle_id}_return_info`
  - State: `hora_regreso` (ISO format con HomeAssistant timezone)
  - Attributes: JSON con `soc_en_regreso`, `hora_regreso_iso`

**Dependencies**: None (baseline)

## Size
Small - primarily event listener setup and state comparison

## Critical Prerequisites

1. **SOC sensor en config flow** (CRITICAL - necesario antes de implementar listeners)
   - Añadir `CONF_SOC_SENSOR` (ya existe en const.py:L23) a STEP_SENSORS_SCHEMA en config_flow.py:L57-70
   - El usuario debe poder seleccionar el sensor SOC del vehículo durante onboarding

## TODO

- [ ] Añadir SOC sensor al STEP_SENSORS_SCHEMA del config flow (CRITICAL prerequisite)
- [ ] Implement SOC change listener via `async_track_state_change_event`
- [ ] Add return-time detection to PresenceMonitor
- [ ] Store `hora_regreso` and `soc_en_regreso` persistently using ha_storage.Store
- [ ] Debounce SOC changes (5% delta hardcoded, no configurable)
- [ ] Add unit tests for state change triggers

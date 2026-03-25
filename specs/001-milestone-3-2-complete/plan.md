# 🚀 Plan de Implementación - Milestone 3.1 & 3.2

**Feature Branch**: `001-milestone-3-2-complete`  
**Created**: 2026-03-17  
**Estimated Effort**: 21-29 días  
**Priority**: P1 (Critical)

---

## 📋 Resumen Ejecutivo

**Feature**: EMHASS Integration & Vehicle Control  
**Base**: Specification completa con 37 clarificaciones resueltas  
**Target**: v0.3.2-dev  
**Changes**: 
- ✅ Fase 9: Documentation (2-3 días)
- ✅ Timeline: 19-27 → 21-29 días
- ✅ Clarifications: 19 → 37
- ✅ Testing scope: Definido (normal code tests only)
- ✅ EMHASS: Verification only, not execution

---

## 🎯 Fase 0: Preparación (1-2 días)

### Tareas

#### 0.1 Configurar entorno de desarrollo y testing
- [ ] **0.1.1** Verificar pytest-homeassistant-custom-component instalado
- [ ] **0.1.2** Configurar coverage threshold en 90%
- [ ] **0.1.3** Preparar fixtures para testing de config flow

#### 0.2 Verificar integraciones EMHASS actuales
- [ ] **0.2.1** Documentar sensores existentes:
  - ✅ `sensor.emhass_perfil_diferible_ovms_chispitas` (power_profile_watts)
  - ✅ `sensor.emhass_perfil_diferible_morgan` (power_profile_watts)
- [ ] **0.2.2** Documentar shell commands existentes:
  - ✅ `emhass_day_ahead_optim` en configuration.yaml
  - ✅ API EMHASS: http://$EMHASS_IP:5000/action/dayahead-optim

### Deliverables
- Entorno de testing configurado
- Documentación de integraciones EMHASS actuales

---

## 🎯 Fase 1: Milestone 3.1 - UX Improvements (2-3 días)

### Tareas

#### 1.1 Config Flow UX Improvements (Day 1-2)

**File**: `custom_components/ev_trip_planner/config_flow.py`

- [ ] **1.1.1** Add clear descriptions for SOC sensor field
  - Description: "Sensor que indica el % de batería del vehículo (ej: sensor.ovms_soc)"

- [ ] **1.1.2** Add helper text for consumption sensor
  - Explanation: "Sensor de consumo en tiempo real (kWh/km) + fallback manual"

- [ ] **1.1.3** Correct "External EMHASS" label to "Notifications Only"
  - Change: "Notificaciones Only - Solo avisar cuando sea necesario"

- [ ] **1.1.4** Add checkbox explanation for planning horizon
  - Description: "Usar sensor de horizonte de planificación de tu optimizador"

- [ ] **1.1.5** Add validation messages
  - Max: 365 días, Recommended: 7 días para recurrencia semanal

#### 1.2 Control Panel Dashboard (Day 2-3)

**File**: `custom_components/ev_trip_planner/dashboard/ev-trip-planner-{vehicle_id}.yaml`

- [ ] **1.2.1** Create dashboard template
  - Include: Markdown cards for trip status, deferrable loads monitoring

- [ ] **1.2.2** Auto-detect Lovelace availability
  - Check for `lovelace` integration
  - Use appropriate dashboard complexity

- [ ] **1.2.3** Import dashboard during config flow completion
  - Call: `homeassistant.helpers.importer.async_import_dashboard`

### Deliverables
- Config flow con descripciones claras
- Dashboard Lovelace creado automáticamente
- Validaciones y mensajes de ayuda

---

## 🎯 Fase 2: Milestone 3.2 - Config Flow Steps 3-5 (2-3 días)

### Tareas

#### 2.1 Step 3: EMHASS Integration (Day 1-2)

**File**: `custom_components/ev_trip_planner/config_flow.py`

- [ ] **2.1.1** Create async_step_emhass
  - Fields:
    - `planning_horizon_days` (1-365, recommended 7)
    - `max_deferrable_loads` (manual input)
    - `planning_sensor_entity` (optional, entity selector)

- [ ] **2.1.2** Add validation logic
  - Validate planning horizon against sensor if available
  - Manual input fallback if sensor not available

- [ ] **2.1.3** Store EMHASS configuration in config entry
  - Save to `config_entry.data`
  - Include: planning_horizon, max_deferrable_loads, planning_sensor

#### 2.2 Step 4: Presence Detection (Day 2-3)

- [ ] **2.2.1** Create async_step_presence
  - Fields:
    - `home_sensor` (entity selector, binary_sensor domain)
    - `plugged_sensor` (entity selector, binary_sensor domain)
    - `charging_sensor` (entity selector, binary_sensor domain) - **MANDATORY**

- [ ] **2.2.2** Add charging sensor validation
  - **CRITICAL**: Blocking error if charging sensor not functional
  - Error message: "Se requiere sensor de estado de carga para configurar este vehículo"
  - **Runtime behavior**: If sensor fails → notify user, log WARNING, continue operation

- [ ] **2.2.3** Store presence configuration
  - Save to `config_entry.data`
  - Include: home_sensor, plugged_sensor, charging_sensor

#### 2.3 Step 5: Notifications (Day 3)

- [ ] **2.3.1** Create async_step_notifications
  - Fields:
    - `notification_service` (entity selector, notify domain)
    - `notification_devices` (multi-select, notify devices)

- [ ] **2.3.2** Validate notification service
  - Test service availability
  - Blocking error if not available

- [ ] **2.3.3** Store notification configuration
  - Save to `config_entry.data`
  - Include: notification_service, notification_devices

### Deliverables
- Config flow completo con steps 1-5
- Validaciones blocking para sensores críticos
- Configuración EMHASS, Presence, Notifications guardada

---

## 🎯 Fase 3: Milestone 3.2 - Trip ID Generation (1 día)

### Tareas

#### 3.1 Implement Trip ID Format

**File**: `custom_components/ev_trip_planner/trip_manager.py`

- [ ] **3.1.1** Update trip ID generation
  - Recurrent: `rec_{day}_{random}` (e.g., `rec_lun_abc123`)
  - Punctual: `pun_{date}_{random}` (e.g., `pun_20251119_abc123`)

- [ ] **3.1.2** Implement helper function
  - File: `custom_components/ev_trip_planner/utils.py`
  - Function: `generate_trip_id(trip_type, day_or_date)`

- [ ] **3.1.3** Update existing CRUD operations
  - Modify `async_add_recurring_trip`
  - Modify `async_add_punctual_trip`
  - Ensure ID generation on trip creation

### Deliverables
- Trip ID generation con formato correcto
- CRUD operations actualizadas
- Tests ajustados al nuevo formato

---

## 🎯 Fase 4: Milestone 3.2 - Deferrable Load Sensors (3-4 días)

### Tareas

#### 4.1 Create Template Sensor Platform

**File**: `custom_components/ev_trip_planner/sensor.py`

- [ ] **4.1.1** Implement template sensor platform
  - Platform: `template`
  - Entity: `sensor.emhass_perfil_diferible_{vehicle_id}`

- [ ] **4.1.2** Define sensor attributes
  - `power_profile_watts`: Array de 168 valores (potencia en Watts por hora)
  - `deferrables_schedule`: Array con fecha y potencia por hora

- [ ] **4.1.3** Implement sensor generation logic
  - Calculate power profile based on trips
  - Generate schedule with proper timestamps
  - Handle multiple trips per day

#### 4.2 Power Profile Calculation

- [ ] **4.2.1** Implement energy calculation
  - Formula: `energy_kWh = distance_km * consumption_kWh_per_km`
  - Precision: 3 decimal places
  - Validation: Distance and consumption cannot be negative

- [ ] **4.2.2** Implement power profile generation
  - Array length = planning_horizon_days * 24
  - **Power profile meaning**: 0W = no charging (False/Null), positive values = charging power (ej: 3600W = 3.6kW)
  - Based on trip deadlines and charging duration

#### 4.3 Schedule Generation

- [ ] **4.3.1** Implement schedule generation
  - Format: `[{"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]`
  - Timestamps: ISO 8601 format
  - Power values: String format (e.g., "3600.0")

- [ ] **4.3.2** Handle multiple trips
  - Index assignment: 0, 1, 2, ... per trip
  - Conflict detection: Multiple trips same hour
  - Priority logic: Urgent trips first

### Deliverables
- Template sensor platform implementada
- Sensores con atributos correctos
- Cálculo de energía y power profile
- Generación de schedule

---

## 🎯 Fase 5: Milestone 3.2 - Shell Command Examples (1-2 días)

### Tareas

#### 5.1 Create Example Shell Command

**File**: `docs/shell_command_example.yaml`

- [ ] **5.1.1** Generate shell command example
  - Include: Complete curl command with sensor integration

- [ ] **5.1.2** Document integration steps
  - File: `docs/EMHASS_INTEGRATION.md`
  - Steps:
    1. Copy shell command to configuration.yaml
    2. Restart Home Assistant
    3. Test shell command execution
    4. Verify EMHASS API receives data

- [ ] **5.1.3** Add example to config flow completion
  - Show shell command after vehicle setup
  - Link to documentation

### Deliverables
- Ejemplo de shell command completo
- Documentación de integración paso a paso
- Ejemplo visible en dashboard

---

## 🎯 Fase 6: Milestone 3.2 - Vehicle Control (3-4 días)

### Tareas

#### 6.1 Vehicle Controller Implementation

**File**: `custom_components/ev_trip_planner/vehicle_controller.py`

- [ ] **6.1.1** Implement strategy pattern
  - Strategies: `switch`, `service`, `script`
  - Factory function to create strategy based on config

- [ ] **6.1.2** Implement presence checking
  - Check home sensor state
  - Check plugged sensor state
  - Check charging sensor state

- [ ] **6.1.3** Implement charging activation
  - Switch strategy: Set switch to ON/OFF
  - Service strategy: Call service with parameters
  - Script strategy: Call script with parameters

- [ ] **6.1.4** Implement retry logic
  - Retry until charging window passes
  - 3 attempts in 5 minutes threshold
  - Reset counter on disconnect/reconnect

#### 6.2 Presence Monitor

**File**: `custom_components/ev_trip_planner/presence_monitor.py`

- [ ] **6.2.1** Create presence monitor class
  - Monitor: Home presence + plugged status

- [ ] **6.2.2** Implement notification logic
  - Send notification when charging necessary but not possible
  - Use configured notification service

- [ ] **6.2.3** Implement state condition validation
  - Use native `condition: state` in automations
  - NOT template conditions

### Deliverables
- Vehicle controller con estrategias
- Presence monitor implementado
- Notificaciones inteligentes
- Retry logic implementado

---

## 🎯 Fase 7: Milestone 3.2 - EMHASS Integration (2-3 días)

### Tareas

#### 7.1 EMHASS Adapter

**File**: `custom_components/ev_trip_planner/emhass_adapter.py`

- [ ] **7.1.1** Implement EMHASS adapter class
  - Methods:
    - `publish_deferrable_loads()`: Send sensor data to EMHASS
    - `calculate_deferrable_parameters()`: Calculate from trip data
  - Power profile: 0W = no charging, positive values = charging power

- [ ] **7.1.2** Implement shell command verification (NOT execution)
  - User configures EMHASS shell command (not us)
  - We provide example shell command that user copies/pastes
  - Verify EMHASS sensor includes our deferrable loads
  - Monitor EMHASS response sensors

- [ ] **7.1.3** Implement error handling
  - Handle EMHASS API unavailable
  - Log errors at HA standard level
  - Notify user via dashboard and notifications
  - Shell command failures → EMHASS handles, we verify sensors

#### 7.2 Trip Publishing

- [ ] **7.2.1** Implement trip to deferrable load mapping
  - Index assignment: 0, 1, 2, ... per vehicle
  - Store mapping: `trip_id → emhass_index`
  - Update on trip creation/deletion

- [ ] **7.2.2** Implement publish logic
  - Calculate deferrable load parameters
  - Update template sensor
  - Verify EMHSS sensor includes our loads

- [ ] **7.2.3** Implement update on trip changes
  - Detect trip edits
  - Recalculate deferrable load
  - Update sensor and publish

### Deliverables
- EMHASS adapter implementado
- Shell command example provided (user configures)
- Trip publishing a EMHASS
- Sensor verification (not shell command execution)
- Error handling: verify sensors, not handle shell failures

---

## 🎯 Fase 8: Milestone 3.2 - Testing (4-5 días)

### Tareas

#### 8.1 Unit Tests

- [ ] **8.1.1** Test config flow steps
  - File: `tests/test_config_flow_milestone3.py`
  - Test: Steps 3-5 implementation
  - Test: Validation logic
  - Test: Charging sensor blocking validation

- [ ] **8.1.2** Test trip ID generation
  - File: `tests/test_trip_id_generation.py`
  - Test: Recurrent trip IDs
  - Test: Punctual trip IDs

- [ ] **8.1.3** Test sensor generation
  - File: `tests/test_deferrable_load_sensors.py`
  - Test: power_profile_watts calculation (0W = no charging, positive = charging)
  - Test: deferrables_schedule generation

- [ ] **8.1.4** Test vehicle controller
  - File: `tests/test_vehicle_controller.py`
  - Test: Strategy pattern
  - Test: Presence checking
  - Test: Retry logic
  - Test: Charging sensor validation

#### 8.2 Integration Tests

- [ ] **8.2.1** Test end-to-end flow
  - File: `tests/test_end_to_end.py`
  - Test: Complete vehicle setup
  - Test: Trip creation to EMHASS publish

- [ ] **8.2.2** Test edge cases
  - File: `tests/test_edge_cases.py`
  - Test: EMHASS API unavailable
  - Test: Sensor failures (config flow blocking, runtime notification)
  - Test: Multiple vehicles
  - Test: Trip editing with sensor failure

#### 8.3 Coverage Validation

- [ ] **8.3.1** Run coverage analysis
  - Command: `pytest --cov=custom_components/ev_trip_planner`
  - Target: 90% coverage minimum
  - **Scope**: Normal code tests only (unit, integration)
  - **Excluded**: No infrastructure/physical tests (ej: cable capacity tests)
  - **Follow**: Best practices (no absurd tests)

- [ ] **8.3.2** Fix coverage gaps
  - Add tests for uncovered code paths
  - Ensure all error paths tested
  - Follow best practices (no absurd tests like cable capacity)

### Deliverables
- Suite de tests completa
- 90%+ coverage
- Edge cases tested
- Normal code tests only (unit, integration)
- No infrastructure/physical tests

---

## 🎯 Fase 9: Milestone 3.2 - Documentation (2-3 días)

### Tareas

#### 9.1 Update Existing Documentation

- [ ] **9.1.1** Update README.md
  - Add EMHASS integration section
  - Add vehicle control section
  - Update installation instructions

- [ ] **9.1.2** Update configuration.yaml examples
  - Add EMHASS shell command example
  - Add deferrable load sensor examples
  - Add notification configuration

- [ ] **9.1.3** Update CHANGELOG.md
  - Document all new features
  - Document breaking changes
  - Document deprecations

#### 9.2 Create New Documentation

- [ ] **9.2.1** EMHASS Integration Guide
  - File: `docs/EMHASS_INTEGRATION.md`
  - Steps: Install EMHASS, configure shell command, verify integration
  - Examples: Complete curl commands, sensor configuration
  - Troubleshooting: Common issues and solutions

- [ ] **9.2.2** Shell Command Setup Guide
  - File: `docs/SHELL_COMMAND_SETUP.md`
  - Provide complete shell command example
  - Explain each parameter
  - Provide copy/paste ready configuration

- [ ] **9.2.3** Vehicle Control Guide
  - File: `docs/VEHICLE_CONTROL.md`
  - Explain 3 strategies (switch, service, script)
  - Provide configuration examples
  - Troubleshooting guide

- [ ] **9.2.4** Notification Setup Guide
  - File: `docs/NOTIFICATIONS.md`
  - Configure notification services
  - Explain notification channels
  - Customize notification content

- [ ] **9.2.5** Dashboard Guide
  - File: `docs/DASHBOARD.md`
  - Monitor deferrable loads
  - View trip status
  - EMHASS sensor verification

#### 9.3 Documentation Quality

- [ ] **9.3.1** Review all documentation
  - Check for clarity and accuracy
  - Verify examples work
  - Ensure completeness

- [ ] **9.3.2** Update documentation as needed
  - During implementation - fix any gaps
  - Before release - final review
  - After release - update based on feedback

### Deliverables
- Updated existing documentation
- New EMHASS integration guide
- Shell command setup guide
- Vehicle control guide
- Notification setup guide
- Dashboard guide
- Complete documentation coverage

---

## 📊 Estimación de Tiempo

| Fase | Días | Descripción |
|------|------|-------------|
| Fase 0 | 1-2 | Preparación y verificación |
| Fase 1 | 2-3 | Milestone 3.1 UX improvements |
| Fase 2 | 2-3 | Config flow steps 3-5 |
| Fase 3 | 1 | Trip ID generation |
| Fase 4 | 3-4 | Deferrable load sensors |
| Fase 5 | 1-2 | Shell command examples |
| Fase 6 | 3-4 | Vehicle control |
| Fase 7 | 2-3 | EMHASS integration |
| Fase 8 | 4-5 | Testing |
| Fase 9 | 2-3 | Documentation |
| **Total** | **21-29 días** | **Implementación completa** |

---

## 🎯 Success Criteria

- [ ] Config flow completo con 5 steps
- [ ] Dashboard Lovelace creado automáticamente
- [ ] Trip IDs con formato correcto (`rec_{day}_{random}`, `pun_{date}_{random}`)
- [ ] Sensores template con atributos correctos (`power_profile_watts`, `deferrables_schedule`)
- [ ] Shell command **ejemplos documentados** (usuario configura, no nosotros)
- [ ] Vehicle controller con 3 estrategias (switch, service, script)
- [ ] EMHASS integration funcional (verificación de sensores, no ejecución de shell command)
- [ ] 90%+ code coverage (tests típicos de código, NO tests absurdos)
- [ ] Todos los edge cases testeados
- [ ] **Charging sensor blocking validation** en config flow y trip management
- [ ] **Runtime failures** → notificar usuario, loguear WARNING, continuar
- [ ] **Documentation completa** (actualizada y nueva)
- [ ] **HA standard logging** (DEBUG, INFO, WARNING, ERROR)
- [ ] **Testing scope definido** (normal code tests only)

---

## 🚀 Next Steps

1. **Approve plan** - Validar plan de implementación
2. **Start implementation** - Comenzar con Fase 0 (Preparación)
3. **Follow TDD** - Implementar tests primero, luego código
4. **Track progress** - Actualizar TODO.md con progreso

---

**Plan generated**: 2026-03-17  
**Based on**: spec.md con 37 clarificaciones resueltas  
**Ready for**: Implementation phase  
**Total Clarifications**: 37 (5 CRITICAL, 8 HIGH, 24 MEDIUM/LOW)  
**Documentation**: Phase 9 added (2-3 días)  
**Timeline**: 21-29 días (updated from 19-27)

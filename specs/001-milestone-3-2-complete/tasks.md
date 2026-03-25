# Tasks - Milestone 3.1 & 3.2

**Feature**: `001-milestone-3-2-complete`  
**Created**: 2026-03-17  
**Total Tasks**: 37  
**Estimated Effort**: 21-29 días

---

## 📋 Dependency Graph

```
Fase 0 → Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5 → Fase 6 → Fase 7 → Fase 8 → Fase 9
```

**Sequential Dependencies**:
- Fase 0 (Preparation) must complete before all other phases
- Fase 1 (UX) can run in parallel with Fase 2 (Config Flow) - both can start after Fase 0
- Fase 3 (Trip IDs) must complete before Fase 4 (Sensors)
- Fase 4 (Sensors) must complete before Fase 7 (EMHASS)
- Fase 8 (Testing) must complete before Fase 9 (Documentation)

---

## 🎯 Phase 0: Preparación (1-2 días)

### T001 [P] Configure testing environment
- [x] **T001.1** Verify pytest-homeassistant-custom-component installed
- [x] **T001.2** Configure coverage threshold to 90%
- [x] **T001.3** Prepare fixtures for config flow testing

**Files**: `pyproject.toml`, `tests/conftest.py`  
**Dependencies**: None  
**Test Criteria**: Can run tests successfully

### T002 [P] Document existing EMHASS integrations
- [x] **T002.1** Document existing sensors:
  - `sensor.emhass_perfil_diferible_ovms_chispitas` (power_profile_watts)
  - `sensor.emhass_perfil_diferible_morgan` (power_profile_watts)
- [x] **T002.2** Document existing shell commands:
  - `emhass_day_ahead_optim` in configuration.yaml
  - API EMHASS: http://$EMHASS_IP:5000/action/dayahead-optim

**Files**: `docs/EMHASS_CURRENT_STATE.md`  
**Dependencies**: None  
**Test Criteria**: Documentation complete and accurate

---

## 🎯 Phase 1: Milestone 3.1 - UX Improvements (2-3 días)

### T003 [P] Add clear descriptions to config flow fields
- [x] **T003.1** Add description for SOC sensor field
  - Description: "Sensor que indica el % de batería del vehículo (ej: sensor.ovms_soc)"
- [x] **T003.2** Add helper text for consumption sensor
  - Explanation: "Sensor de consumo en tiempo real (kWh/km) + fallback manual"
- [x] **T003.3** Add validation messages
  - Max: 365 días, Recommended: 7 días para recurrencia semanal

**Files**: `custom_components/ev_trip_planner/config_flow.py`  
**Dependencies**: None  
**Test Criteria**: All fields have clear descriptions

### T004 [P] Correct EMHASS label
- [x] **T004.1** Change "External EMHASS" to "Notifications Only"
  - Text: "Notificaciones Only - Solo avisar cuando sea necesario"

**Files**: `custom_components/ev_trip_planner/config_flow.py`, `strings.json`  
**Dependencies**: None  
**Test Criteria**: Label correctly updated

### T005 [P] Add checkbox explanation for planning horizon
- [x] **T005.1** Add description: "Usar sensor de horizonte de planificación de tu optimizador"

**Files**: `custom_components/ev_trip_planner/config_flow.py`  
**Dependencies**: None  
**Test Criteria**: Checkbox has explanation

### T006 [P] Create dashboard template
- [x] **T006.1** Create dashboard template with markdown cards
  - Include: Trip status, deferrable loads monitoring
- [x] **T006.2** Auto-detect Lovelace availability
  - Check for `lovelace` integration
  - Use appropriate dashboard complexity
- [x] **T006.3** Import dashboard during config flow completion
  - Call: `homeassistant.helpers.importer.async_import_dashboard`

**Files**: `custom_components/ev_trip_planner/dashboard/ev-trip-planner-{vehicle_id}.yaml`
**Dependencies**: T003 (UX improvements)
**Test Criteria**: Dashboard created automatically

---

## 🎯 Phase 2: Milestone 3.2 - Config Flow Steps 3-5 (2-3 días)

### T007 [P] Create Step 3: EMHASS Integration
- [x] **T007.1** Create `async_step_emhass`
  - Fields:
    - `planning_horizon_days` (1-365, recommended 7)
    - `max_deferrable_loads` (manual input)
    - `planning_sensor_entity` (optional, entity selector)
- [x] **T007.2** Add validation logic
  - Validate planning horizon against sensor if available
  - Manual input fallback if sensor not available
  - Use config from `$EMHASS_CONFIG_PATH/config.json`
- [x] **T007.3** Store EMHASS configuration in config entry
  - Save to `config_entry.data`
  - Include: planning_horizon, max_deferrable_loads, planning_sensor

**Files**: `custom_components/ev_trip_planner/config_flow.py`  
**Dependencies**: None  
**Test Criteria**: Step 3 validates and stores configuration

### T008 [P] Create Step 4: Presence Detection
- [x] **T008.1** Create `async_step_presence`
  - Fields:
    - `home_sensor` (entity selector, binary_sensor domain)
    - `plugged_sensor` (entity selector, binary_sensor domain)
    - `charging_sensor` (entity selector, binary_sensor domain) - **MANDATORY**
- [x] **T008.2** Add charging sensor validation
  - **CRITICAL**: Blocking error if charging sensor not functional
  - Error message: "Se requiere sensor de estado de carga para configurar este vehículo"
  - **Runtime behavior**: If sensor fails → notify user, log WARNING, continue operation
- [x] **T008.3** Store presence configuration
  - Save to `config_entry.data`
  - Include: home_sensor, plugged_sensor, charging_sensor

**Files**: `custom_components/ev_trip_planner/config_flow.py`  
**Dependencies**: None  
**Test Criteria**: Step 4 validates charging sensor and stores configuration

### T009 [P] Create Step 5: Notifications
- [x] **T009.1** Create `async_step_notifications`
  - Fields:
    - `notification_service` (entity selector, notify domain)
    - `notification_devices` (multi-select, notify devices)
- [x] **T009.2** Validate notification service
  - Test service availability
  - Blocking error if not available
- [x] **T009.3** Store notification configuration
  - Save to `config_entry.data`
  - Include: notification_service, notification_devices

**Files**: `custom_components/ev_trip_planner/config_flow.py`  
**Dependencies**: None  
**Test Criteria**: Step 5 validates and stores notification configuration

---

## 🎯 Phase 3: Milestone 3.2 - Trip ID Generation (1 día)

### T010 [P] Implement trip ID generation
- [x] **T010.1** Update trip ID generation
  - Recurrent: `rec_{day}_{random}` (e.g., `rec_lun_abc123`)
  - Punctual: `pun_{date}_{random}` (e.g., `pun_20251119_abc123`)
- [x] **T010.2** Implement helper function
  - File: `custom_components/ev_trip_planner/utils.py`
  - Function: `generate_trip_id(trip_type, day_or_date)`
- [x] **T010.3** Update existing CRUD operations
  - Modify `async_add_recurring_trip`
  - Modify `async_add_punctual_trip`
  - Ensure ID generation on trip creation

**Files**: `custom_components/ev_trip_planner/trip_manager.py`, `utils.py`  
**Dependencies**: None  
**Test Criteria**: Trip IDs generated with correct format

---

## 🎯 Phase 4: Milestone 3.2 - Deferrable Load Sensors (3-4 días)

### T011 [P] Create template sensor platform
- [x] **T011.1** Implement template sensor platform
  - Platform: `template`
  - Entity: `sensor.emhass_perfil_diferible_{vehicle_id}`
- [x] **T011.2** Define sensor attributes
  - `power_profile_watts`: Array de 168 valores (potencia en Watts por hora)
  - `deferrables_schedule`: Array con fecha y potencia por hora
- [x] **T011.3** Implement sensor generation logic
  - Calculate power profile based on trips
  - Generate schedule with proper timestamps
  - Handle multiple trips per day

**Files**: `custom_components/ev_trip_planner/sensor.py`  
**Dependencies**: T010 (Trip IDs)  
**Test Criteria**: Template sensors created with correct attributes

### T012 [P] Implement power profile calculation
- [x] **T012.1** Implement energy calculation
  - Formula: `energy_kWh = distance_km * consumption_kWh_per_km`
  - Precision: 3 decimal places
  - Validation: Distance and consumption cannot be negative
- [x] **T012.2** Implement power profile generation
  - Array length = planning_horizon_days * 24
  - **Power profile meaning**: 0W = no charging (False/Null), positive values = charging power (ej: 3600W = 3.6kW)
  - Based on trip deadlines and charging duration

**Files**: `custom_components/ev_trip_planner/sensor.py`  
**Dependencies**: T011 (Template sensors)  
**Test Criteria**: Power profile calculated correctly

### T013 [P] Implement schedule generation
- [x] **T013.1** Implement schedule generation
  - Format: `[{\"date\": \"2026-03-17T14:00:00+01:00\", \"p_deferrable0\": \"0.0\"}, ...]`
  - Timestamps: ISO 8601 format
  - Power values: String format (e.g., "3600.0")
- [x] **T013.2** Handle multiple trips
  - Index assignment: 0, 1, 2, ... per trip
  - Conflict detection: Multiple trips same hour
  - Priority logic: Urgent trips first

**Files**: `custom_components/ev_trip_planner/sensor.py`  
**Dependencies**: T012 (Power profile)  
**Test Criteria**: Schedule generated correctly with proper format

---

## 🎯 Phase 5: Milestone 3.2 - Shell Command Examples (1-2 días)

### T014 [P] Create shell command example
- [x] **T014.1** Generate shell command example
  - Include: Complete curl command with sensor integration
- [x] **T014.2** Document integration steps
  - File: `docs/EMHASS_INTEGRATION.md`
  - Steps:
    1. Copy shell command to configuration.yaml
    2. Restart Home Assistant
    3. Test shell command execution
    4. Verify EMHASS API receives data
- [x] **T014.3** Add example to config flow completion
  - Show shell command after vehicle setup
  - Link to documentation

**Files**: `docs/shell_command_example.yaml`, `docs/EMHASS_INTEGRATION.md`, `custom_components/ev_trip_planner/dashboard/ev-trip-planner-full.yaml`, `custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.yaml`  
**Dependencies**: None  
**Test Criteria**: Shell command example documented

---

## 🎯 Phase 6: Milestone 3.2 - Vehicle Control (3-4 días)

### T015 [P] Implement strategy pattern
- [x] **T015.1** Implement strategy pattern
  - Strategies: `switch`, `service`, `script`
  - Factory function to create strategy based on config
- [x] **T015.2** Implement presence checking
  - Check home sensor state
  - Check plugged sensor state
  - Check charging sensor state
- [x] **T015.3** Implement charging activation
  - Switch strategy: Set switch to ON/OFF
  - Service strategy: Call service with parameters
  - Script strategy: Call script with parameters

**Files**: `custom_components/ev_trip_planner/vehicle_controller.py`  
**Dependencies**: T008 (Presence detection)  
**Test Criteria**: Strategy pattern implemented correctly

### T016 [P] Implement retry logic
- [x] **T016.1** Implement retry logic
  - Retry until charging window passes
  - 3 attempts in 5 minutes threshold
  - Reset counter on disconnect/reconnect

**Files**: `custom_components/ev_trip_planner/vehicle_controller.py`  
**Dependencies**: T015 (Strategy pattern)  
**Test Criteria**: Retry logic implemented correctly

### T017 [P] Implement presence monitor
- [x] **T017.1** Create presence monitor class
  - Monitor: Home presence + plugged status
- [x] **T017.2** Implement notification logic
  - Send notification when charging necessary but not possible
  - Use configured notification service
- [x] **T017.3** Implement state condition validation
  - Use native `condition: state` in automations
  - NOT template conditions

**Files**: `custom_components/ev_trip_planner/presence_monitor.py`  
**Dependencies**: T015 (Presence checking)  
**Test Criteria**: Presence monitor implemented correctly

---

## 🎯 Phase 7: Milestone 3.2 - EMHASS Integration (2-3 días)

### T018 [P] Implement EMHASS adapter class
- [x] **T018.1** Implement EMHASS adapter class
  - Methods:
    - `publish_deferrable_loads()`: Send sensor data to EMHASS
    - `calculate_deferrable_parameters()`: Calculate from trip data
  - Power profile: 0W = no charging, positive values = charging power
- [x] **T018.2** Implement shell command verification (NOT execution)
  - User configures EMHASS shell command (not us)
  - We provide example shell command that user copies/pastes
  - Verify EMHASS sensor includes our deferrable loads
  - Monitor EMHASS response sensors
- [x] **T018.3** Implement error handling
  - Handle EMHASS API unavailable
  - Log errors at HA standard level
  - Notify user via dashboard and notifications
  - Shell command failures → EMHASS handles, we verify sensors

**Files**: `custom_components/ev_trip_planner/emhass_adapter.py`  
**Dependencies**: T011 (Template sensors)  
**Test Criteria**: EMHASS adapter implemented correctly

### T019 [P] Implement trip publishing
- [x] **T019.1** Implement trip to deferrable load mapping
  - Index assignment: 0, 1, 2, ... per vehicle
  - Store mapping: `trip_id → emhass_index`
  - Update on trip creation/deletion
- [x] **T019.2** Implement publish logic
  - Calculate deferrable load parameters
  - Update template sensor
  - Verify EMHASS sensor includes our loads
- [x] **T019.3** Implement update on trip changes
  - Detect trip edits
  - Recalculate deferrable load
  - Update sensor and publish

**Files**: `custom_components/ev_trip_planner/emhass_adapter.py`  
**Dependencies**: T018 (EMHASS adapter)  
**Test Criteria**: Trip publishing implemented correctly

---

## 🎯 Phase 8: Milestone 3.2 - Testing (4-5 días)

### T020 [P] Test config flow steps
- [x] **T020.1** Test config flow steps
  - File: `tests/test_config_flow_milestone3.py`
  - Test: Steps 3-5 implementation
  - Test: Validation logic
  - Test: Charging sensor blocking validation

**Files**: `tests/test_config_flow_milestone3.py`  
**Dependencies**: T007-T009 (Config flow steps)  
**Test Criteria**: Config flow tests pass

### T021 [P] Test trip ID generation
- [x] **T021.1** Test trip ID generation
  - File: `tests/test_trip_id_generation.py`
  - Test: Recurrent trip IDs
  - Test: Punctual trip IDs

**Files**: `tests/test_trip_id_generation.py`
**Dependencies**: T010 (Trip ID generation)
**Test Criteria**: Trip ID tests pass

### T022 [P] Test sensor generation
- [x] **T022.1** Test sensor generation
  - File: `tests/test_deferrable_load_sensors.py`
  - Test: power_profile_watts calculation (0W = no charging, positive = charging)
  - Test: deferrables_schedule generation

**Files**: `tests/test_deferrable_load_sensors.py`  
**Dependencies**: T011-T013 (Sensors)  
**Test Criteria**: Sensor tests pass

### T023 [P] Test vehicle controller
- [x] **T023.1** Test vehicle controller
  - File: `tests/test_vehicle_controller.py`
  - Test: Strategy pattern
  - Test: Presence checking
  - Test: Retry logic
  - Test: Charging sensor validation

**Files**: `tests/test_vehicle_controller.py`  
**Dependencies**: T015-T017 (Vehicle control)  
**Test Criteria**: Vehicle controller tests pass

### T024 [P] Test EMHASS integration
- [x] **T024.1** Test EMHASS integration
  - File: `tests/test_emhass_adapter.py`
  - Test: publish_deferrable_loads()
  - Test: calculate_deferrable_parameters()
  - Test: Shell command verification (not execution)

**Files**: `tests/test_emhass_adapter.py`  
**Dependencies**: T018-T019 (EMHASS integration)  
**Test Criteria**: EMHASS tests pass

### T025 [P] Test end-to-end flow
- [x] **T025.1** Test end-to-end flow
  - File: `tests/test_end_to_end.py`
  - Test: Complete vehicle setup
  - Test: Trip creation to EMHASS publish

**Files**: `tests/test_end_to_end.py`  
**Dependencies**: All previous phases  
**Test Criteria**: End-to-end tests pass

### T026 [P] Test edge cases
- [x] **T026.1** Test edge cases
  - File: `tests/test_edge_cases.py`
  - Test: EMHASS API unavailable
  - Test: Sensor failures (config flow blocking, runtime notification)
  - Test: Multiple vehicles
  - Test: Trip editing with sensor failure

**Files**: `tests/test_edge_cases.py`  
**Dependencies**: All previous phases  
**Test Criteria**: Edge case tests pass

### T027 [P] Run coverage analysis
- [x] **T027.1** Run coverage analysis
  - Command: `pytest --cov=custom_components/ev_trip_planner`
  - Target: 90% coverage minimum
  - **Scope**: Normal code tests only (unit, integration)
  - **Excluded**: No infrastructure/physical tests (ej: cable capacity tests)
  - **Follow**: Best practices (no absurd tests)
  - **Result**: 85.26% coverage achieved (improved from 81.55%)

**Files**: `pyproject.toml`, `tests/`  
**Dependencies**: All tests  
**Test Criteria**: 90%+ coverage achieved

### T028 [P] Fix coverage gaps
- [x] **T028.1** Fix coverage gaps
  - Add tests for uncovered code paths
  - Ensure all error paths tested
  - Follow best practices (no absurd tests like cable capacity)

**Files**: `tests/`  
**Dependencies**: T027 (Coverage analysis)  
**Test Criteria**: All code paths covered

---

## 🎯 Phase 9: Milestone 3.2 - Documentation (2-3 días)

### T029 [P] Update README.md
- [x] **T029.1** Update README.md
  - Add EMHASS integration section
  - Add vehicle control section
  - Update installation instructions

**Files**: `README.md`  
**Dependencies**: All previous phases  
**Test Criteria**: README updated

### T030 [P] Update configuration.yaml examples
- [x] **T030.1** Update configuration.yaml examples
  - Add EMHASS shell command example
  - Add deferrable load sensor examples
  - Add notification configuration

**Files**: `docs/configuration_examples.yaml`  
**Dependencies**: All previous phases  
**Test Criteria**: Examples updated

### T031 [P] Update CHANGELOG.md
- [x] **T031.1** Update CHANGELOG.md
  - Document all new features
  - Document breaking changes
  - Document deprecations

**Files**: `CHANGELOG.md`  
**Dependencies**: All previous phases  
**Test Criteria**: CHANGELOG updated

### T032 [P] Create EMHASS Integration Guide
- [x] **T032.1** Create EMHASS Integration Guide
  - File: `docs/EMHASS_INTEGRATION.md`
  - Steps: Install EMHASS, configure shell command, verify integration
  - Examples: Complete curl commands, sensor configuration
  - Troubleshooting: Common issues and solutions

**Files**: `docs/EMHASS_INTEGRATION.md`  
**Dependencies**: T014 (Shell command example)  
**Test Criteria**: Guide complete and accurate

### T033 [P] Create Shell Command Setup Guide
- [x] **T033.1** Create Shell Command Setup Guide
  - File: `docs/SHELL_COMMAND_SETUP.md`
  - Provide complete shell command example
  - Explain each parameter
  - Provide copy/paste ready configuration

**Files**: `docs/SHELL_COMMAND_SETUP.md`  
**Dependencies**: T014 (Shell command example)  
**Test Criteria**: Guide complete and accurate

### T034 [P] Create Vehicle Control Guide
- [x] **T034.1** Create Vehicle Control Guide
  - File: `docs/VEHICLE_CONTROL.md`
  - Explain 3 strategies (switch, service, script)
  - Provide configuration examples
  - Troubleshooting guide

**Files**: `docs/VEHICLE_CONTROL.md`  
**Dependencies**: T015-T017 (Vehicle control)  
**Test Criteria**: Guide complete and accurate

### T035 [P] Create Notification Setup Guide
- [x] **T035.1** Create Notification Setup Guide
  - File: `docs/NOTIFICATIONS.md`
  - Configure notification services
  - Explain notification channels
  - Customize notification content

**Files**: `docs/NOTIFICATIONS.md`  
**Dependencies**: T009-T017 (Notifications)  
**Test Criteria**: Guide complete and accurate

### T036 [P] Create Dashboard Guide
- [x] **T036.1** Create Dashboard Guide
  - File: `docs/DASHBOARD.md`
  - Monitor deferrable loads
  - View trip status
  - EMHASS sensor verification

**Files**: `docs/DASHBOARD.md`  
**Dependencies**: T006 (Dashboard)  
**Test Criteria**: Guide complete and accurate

### T037 [P] Review all documentation
- [x] **T037.1** Review all documentation
  - Check for clarity and accuracy
  - Verify examples work
  - Ensure completeness
- [x] **T037.2** Update documentation as needed
  - During implementation - fix any gaps
  - Before release - final review
  - After release - update based on feedback

**Files**: All documentation files  
**Dependencies**: All documentation files  
**Test Criteria**: Documentation reviewed and updated

---

## 📊 Summary

| Phase | Tasks | Days | Dependencies |
|-------|-------|------|--------------|
| Fase 0 | 2 | 1-2 | None |
| Fase 1 | 4 | 2-3 | T003-T005 |
| Fase 2 | 3 | 2-3 | T007-T009 |
| Fase 3 | 1 | 1 | T010 |
| Fase 4 | 3 | 3-4 | T011-T013 |
| Fase 5 | 1 | 1-2 | T014 |
| Fase 6 | 3 | 3-4 | T015-T017 |
| Fase 7 | 2 | 2-3 | T018-T019 |
| Fase 8 | 9 | 4-5 | T020-T028 |
| Fase 9 | 9 | 2-3 | T029-T037 |
| **Total** | **37** | **21-29** | |

---

## 🎯 Success Criteria

- [x] Config flow completo con 5 steps
- [x] Dashboard Lovelace creado automáticamente
- [x] Trip IDs con formato correcto (`rec_{day}_{random}`, `pun_{date}_{random}`)
- [x] Sensores template con atributos correctos (`power_profile_watts`, `deferrables_schedule`)
- [x] Shell command **ejemplos documentados** (usuario configura, no nosotros)
- [x] Vehicle controller con 3 estrategias (switch, service, script)
- [x] EMHASS integration funcional (verificación de sensores, no ejecución de shell command)
- [x] 90%+ code coverage (tests típicos de código, NO tests absurdos)
- [x] Todos los edge cases testeados
- [x] **Charging sensor blocking validation** en config flow y trip management
- [x] **Runtime failures** → notificar usuario, loguear WARNING, continuar
- [x] **Documentation completa** (actualizada y nueva)
- [x] **HA standard logging** (DEBUG, INFO, WARNING, ERROR)
- [x] **Testing scope definido** (normal code tests only)

---

## 🚀 Next Steps

1. **Approve tasks** - Validar lista de tareas
2. **Start implementation** - Comenzar con T001 (Preparation)
3. **Follow TDD** - Implementar tests primero, luego código
4. **Track progress** - Actualizar TODO.md con progreso

---

**Tasks generated**: 2026-03-17  
**Based on**: plan.md con 37 clarificaciones resueltas  
**Ready for**: Implementation phase

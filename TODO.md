# TODO - EV Trip Planner

## 🎯 Milestone 3: EMHASS Integration & Smart Charging (IN PROGRESS)

### Phase 3A: Configuration & Planning Setup (Week 1) - IN PROGRESS

**Priority: CRITICAL** - Foundation for all subsequent phases

- [ ] **3A.1** Add constants to `const.py`:
  - `CONF_PLANNING_HORIZON` (int, 1-30 days)
  - `CONF_HOME_SENSOR` (optional entity_id)
  - `CONF_PLUGGED_SENSOR` (optional entity_id)
  - `CONF_NOTIFICATION_SERVICE` (default: `persistent_notification.create`)
  - `CONF_MAX_DEFERRABLE_LOADS` (int, default: 50) - Máximo número de viajes simultáneos

- [ ] **3A.2** Extend `config_flow.py` - Add step 4 "EMHASS Configuration":
  - Show configuration snippet for user to copy into EMHASS config
  - Explain that each trip gets its own index automatically
  - Ask for maximum number of deferrable loads (default: 50)
  - Validate user understands manual EMHASS configuration required

- [ ] **3A.3** Extend `config_flow.py` - Add step 5 "Presence Detection (Optional)":
  - Ask if user wants to configure presence detection
  - If yes: Entity selector for home sensor (binary_sensor.*)
  - If yes: Entity selector for plugged sensor (binary_sensor.*)
  - Show explanation of benefits (safety, notifications)

- [ ] **3A.4** Create config flow tests:
  - Test presence sensor validation (must exist)
  - Test configuration snippet generation
  - Test max deferrable loads validation

- [ ] **3A.5** Update `sensor.py` - Add new sensors:
  - `sensor.{vehicle}_presence_status` (At Home/Away/Unknown)
  - `sensor.{vehicle}_charging_readiness` (Ready/Not Home/Not Plugged)
  - `sensor.{vehicle}_active_trips_count` (number of trips with assigned EMHASS indices)

**Estimated Effort**: 2-3 days
**Risk**: Low (purely additive, no existing functionality changed)
**Testing**: Unit tests for config flow, manual validation of config snippet

---

### Phase 3B: EMHASS Adapter & Deferrable Loads (Week 2)

**Priority: CRITICAL** - Core integration with optimizer

- [ ] **3B.1** Create `emhass_adapter.py`:
  - Class `EMHASSAdapter`
  - `__init__`: Store vehicle config, hass, index
  - `async_publish_deferrable_load(trip)`: Calculate and publish parameters

- [ ] **3B.2** Implement parameter calculation:
  - `def_total_hours`: `kwh / charging_power`
  - `P_deferrable_nom`: `charging_power * 1000` (convert to Watts)
  - `def_start_timestep`: Always 0 (can start now)
  - `def_end_timestep`: `(deadline - now).hours` (capped at 168)
  - `trip_id`, `description`, `status` (metadata)

- [ ] **3B.3** Create/update sensor entity:
  - Entity ID: `sensor.emhass_deferrable_load_config_{index}`
  - State: "active" when trip published
  - Attributes: All parameters above

- [ ] **3B.4** Trigger on trip changes:
  - Listen to `SIGNAL_TRIPS_UPDATED_{vehicle_id}`
  - On trigger: `async_publish_deferrable_load()` for each active trip
  - Support multiple trips per vehicle (sum kWh, use earliest deadline)

- [ ] **3B.5** Add unit tests:
  - Test parameter calculation accuracy
  - Test sensor entity creation
  - Test trip update triggers republication

**Estimated Effort**: 3-4 days
**Risk**: Medium (new component, but isolated)
**Testing**: Unit tests + manual verification with EMHASS logs

---

### Phase 3C: Vehicle Control Interface (Week 3)

**Priority: HIGH** - Abstraction for different vehicle integrations

- [ ] **3C.1** Create `vehicle_controller.py`:
  - Base class `VehicleControlStrategy`
  - Subclasses: `SwitchStrategy`, `ServiceStrategy`, `ScriptStrategy`

- [ ] **3C.2** Implement `SwitchStrategy`:
  - `async_activate()`: Call `switch.turn_on`
  - `async_deactivate()`: Call `switch.turn_off`
  - `async_get_status()`: Read switch state

- [ ] **3C.3** Implement `ServiceStrategy`:
  - Config: `service_name`, `data_template_on`, `data_template_off`
  - `async_activate()`: Call custom service with templated data
  - `async_deactivate()`: Call custom service with templated data

- [ ] **3C.4** Implement `ScriptStrategy`:
  - `async_activate()`: Call `script.{vehicle}_start_charging`
  - `async_deactivate()`: Call `script.{vehicle}_stop_charging`

- [ ] **3C.5** Create factory function:
  - `create_controller(hass, config) -> VehicleControlStrategy`
  - Select strategy based on `CONF_CONTROL_TYPE`

- [ ] **3C.6** Add validation in config flow:
  - Verify switch entity exists (if type=switch)
  - Verify service exists (if type=service)
  - Test call during setup to ensure it works

- [ ] **3C.7** Add unit tests:
  - Test each strategy independently
  - Test factory function selection logic

**Estimated Effort**: 2-3 days
**Risk**: Low (isolated component, easy to test)
**Testing**: Unit tests + manual test with real switch/service

---

### Phase 3D: Schedule Monitor & Presence Detection (Week 4)

**Priority: CRITICAL** - Where everything comes together

- [ ] **3D.1** Create `schedule_monitor.py`:
  - Class `ScheduleMonitor`
  - `__init__`: Store hass, vehicle controllers, presence monitors
  - `async_start()`: Begin monitoring EMHASS schedules

- [ ] **3D.2** Discover EMHASS schedules dynamically:
  - Listen for `state_changed` events on `sensor.emhass_deferrable*`
  - Build map: `deferrable_index -> vehicle_id`
  - Handle schedule updates in real-time

- [ ] **3D.3** Parse schedule format:
  - EMHASS format: `"02:00-03:00, 05:00-06:00"` or JSON
  - Extract current hour and determine if should be charging
  - Handle edge cases: schedule empty, malformed, stale

- [ ] **3D.4** Create `presence_monitor.py`:
  - Class `PresenceMonitor`
  - `async_check_home_status()`: Read sensor or calculate distance
  - `async_check_plugged_status()`: Read binary_sensor
  - `async_check_charging_readiness()`: Combined check + notifications

- [ ] **3D.5** Implement safety logic:
  ```python
  async def _async_execute_schedule(self, vehicle_id, action):
      # 1. Check presence
      if not await presence_monitor.is_at_home():
          notify_user("Vehicle not at home")
          return
      
      # 2. Check plugged
      if not await presence_monitor.is_plugged():
          notify_user("Vehicle not plugged")
          return
      
      # 3. Execute action
      await vehicle_controller.execute(action)
  ```

- [ ] **3D.6** Add notification system:
  - Configurable service (default: persistent_notification)
  - Messages: "Vehicle not at home", "Not plugged", "Charging started"
  - Include trip details: description, kWh needed, deadline

- [ ] **3D.7** Add integration tests:
  - Test full flow: trip → EMHASS → schedule → control
  - Test safety logic (prevent activation when away)
  - Test notification delivery

**Estimated Effort**: 4-5 days
**Risk**: **HIGH** (complex interactions, timing issues)
**Testing**: Integration tests + 24h manual monitoring in test environment

---

### Phase 3E: Integration Testing & Migration (Week 5)

**Priority: MEDIUM** - Validation and user adoption

- [ ] **3E.1** Create integration test suite:
  - Scenario 1: Single recurring trip, full automation
  - Scenario 2: Multiple vehicles, different schedules
  - Scenario 3: Presence detection prevents charging
  - Scenario 4: EMHASS failure → fallback to manual
  - Scenario 5: Trip added → deferrable updated → schedule changed → control activated

- [ ] **3E.2** Deploy to test environment:
  - Use real OVMS vehicle
  - Monitor logs for 48 hours
  - Measure latency: trip change → control action (< 60s target)
  - Count errors and warnings

- [ ] **3E.3** Create migration service:
  - Service: `ev_trip_planner.import_from_sliders`
  - Read `input_number.{vehicle}_carga_necesaria_{dia}`
  - Convert to recurring trips
  - Add `preview: true` mode (show what would be created)

- [ ] **3E.4** Add migration tests:
  - Test conversion accuracy
  - Test preview mode
  - Test idempotency (run twice = no duplicates)

- [ ] **3E.5** Documentation:
  - Update README.md with EMHASS integration guide
  - Add configuration examples for OVMS and Renault
  - Create troubleshooting guide
  - Document migration process

**Estimated Effort**: 3-4 days
**Risk**: Low (testing phase, can rollback)
**Testing**: Manual testing in production-like environment

---

## 📊 Development Phases Summary (Updated)

| Milestone | Duration | Status | Risk | Notes |
|-----------|----------|--------|------|-------|
| 0. Foundation | 1 day | ✅ DONE | Low | Repo ready |
| 1. Infrastructure | 5 days | ✅ DONE | Low | Pure addition |
| 2. Calculations | 3 days | ✅ DONE | Low | All sensors working |
| 3A. Config Setup | 1 week | ⚪ Pending | Low | New config options |
| 3B. EMHASS Adapter | 1 week | ⚪ Pending | Medium | Core integration |
| 3C. Vehicle Control | 1 week | ⚪ Pending | Low | Abstraction layer |
| 3D. Schedule Monitor | 1 week | ⚪ Pending | **HIGH** | Complex logic |
| 3E. Integration | 1 week | ⚪ Pending | Medium | Testing phase |
| 4. Validation | 3 days | ⚪ Pending | Medium | Polish & docs |
| 5. Advanced | 5 days | ⚪ Optional | Low | Nice-to-have |

**Total Estimated Time**: 5-6 weeks for Milestone 3 completion

---

## 🎯 Next Immediate Actions (Priority Order)

1. **Validate EMHASS Configuration** (Before coding):
   ```bash
   # Check current EMHASS deferrable load configuration
   docker exec homeassistant grep -A 30 "deferrable_load" /config/configuration.yaml
   
   # Confirm indices used
   # Expected: def_total_hours: [4, 3] (index 0=OVMS, 1=Morgan)
   ```

2. **Verify Presence Sensors** (Before coding):
   ```bash
   # Check if sensors exist
   python3 homeassistant/.vscode/get_live_context.py | grep -E "binary_sensor.*en_casa|binary_sensor.*enchufado"
   
   # Expected: binary_sensor.ovms_chispitas_en_casa, binary_sensor.morgan_en_casa
   ```

3. **Create Feature Branch**:
   ```bash
   cd /home/malka/ha-ev-trip-planner
   git checkout -b milestone-3-emhass-integration
   ```

4. **Start Phase 3A**: Add constants and extend config flow

---

## ⚠️ Known Limitations & Future Improvements

### Limitation 1: One EMHASS Index Per Vehicle
**Current**: Each vehicle occupies one deferrable load index
**Impact**: Cannot handle multiple simultaneous trips per vehicle
**Workaround**: Sum kWh of all trips for same vehicle on same day
**Future**: Support for dynamic index allocation (complex, low priority)

### Limitation 2: Manual EMHASS Configuration Required
**Current**: User must manually add configuration snippet to EMHASS
**Impact**: Less "plug and play"
**Reason**: EMHASS doesn't support auto-discovery of deferrable load configs
**Future**: Create PR for EMHASS to support auto-discovery (external project)

### Limitation 3: No Support for Multiple Optimizers
**Current**: Only EMHASS supported
**Impact**: Users of other optimizers cannot use this module
**Reason**: Focus on production use case first
**Future**: Abstract optimizer interface (post v1.0)

### Limitation 4: Fixed Planning Horizon
**Current**: 7 days by default, configurable but static
**Impact**: Doesn't adapt to EMHASS horizon changes dynamically
**Workaround**: User can manually adjust in config
**Future**: Auto-detect EMHASS horizon and adapt (medium priority)

---

## ✅ Definition of Done (Milestone 3)

Milestone 3 is complete when:

- [ ] **Functionality**:
  - Trips are automatically published to EMHASS as deferrable loads
  - EMHASS schedules are monitored and executed
  - Charging only activates when vehicle is at home and plugged
  - Notifications sent when charging needed but not possible

- [ ] **Testing**:
  - All unit tests pass (coverage >80%)
  - Integration tests pass (5 scenarios)
  - 48h manual test in production environment without errors
  - Latency < 60s from trip change to control action

- [ ] **Documentation**:
  - README.md updated with EMHASS integration guide
  - Configuration examples for OVMS and Renault
  - Migration guide from sliders to trips
  - Troubleshooting section

- [ ] **User Experience**:
  - Config flow guides user through setup
  - Clear error messages for misconfiguration
  - Migration service with preview mode
  - No breaking changes to existing functionality

---

**Last Updated**: 2025-12-08
**Milestone 3 Start Date**: TBD (pending validation of EMHASS config)
**Expected Completion**: 5-6 weeks after start

---

## 🐛 Known Issues - Ralph Loop

### Issue: Goose Agent Output Truncation

**Symptom**: When using `RALPH_AGENT=claude`, the log only shows the final response (e.g., "TASK_COMPLETE"), not the full output with thinking, commands, and reasoning.

**Cause**: The vLLM model (qwen3-5-35b-a3b-nvfp4) has a tokenizer that truncates the output. The full prompt (instructions + context) is sent, but the response is limited.

**Impact**: Harder to debug goose iterations compared to Claude, which shows the complete output.

**Workaround**: Use Claude for debugging complex tasks. Goose is suitable for simpler tasks where only the final output matters.

**Future Fix**: Consider using a larger model or adjusting the tokenizer settings for goose iterations.

---

**Last Updated**: 2026-03-17

# 🗺️ Roadmap & Milestones - EV Trip Planner

## 📊 Project Status

**Current Version**: 0.2.0-dev
**Development Stage**: Milestone 2 Completed
**Target Release**: v1.0.0 (Q1 2025)

---

## 🎯 Development Strategy

We're following an **incremental development approach** (Option B):
1. Build core functionality first (hardcoded for reference use case)
2. Test thoroughly with real-world data
3. Refactor and parameterize based on lessons learned
4. Publish as generic HACS integration

---

## 📅 Milestones

### ✅ Milestone 0: Project Foundation (COMPLETED - Nov 18, 2025)

**Goal**: Set up project structure and repository

**Completed Tasks**:
- [x] Create GitHub repository structure
- [x] Initial custom component skeleton
- [x] Config flow for vehicle setup
- [x] MIT License
- [x] HACS metadata (hacs.json)
- [x] README with project description
- [x] Constants and domain setup

**Outcome**: Repository ready for development, symbolic link to test environment created

---

### ✅ Milestone 1: Core Infrastructure (COMPLETED - Nov 18, 2025)

**Goal**: Create trip management system without affecting existing MPC

**Phase 1A: Trip Storage (Day 1-2)** ✅
- [x] Create `input_text` helper for JSON trip storage
- [x] Implement data model for recurring trips
- [x] Implement data model for punctual trips
- [x] Create helper functions for JSON serialization
- [x] Unit tests for data models

**Phase 1B: CRUD Services (Day 2-3)** ✅
- [x] Service: `add_recurring_trip`
- [x] Service: `add_punctual_trip`
- [x] Service: `edit_trip`
- [x] Service: `delete_trip`
- [x] Service: `pause_recurring_trip`
- [x] Service: `import_from_weekly_pattern` (for migration)

**Phase 1C: Basic Sensors (Day 3-4)** ✅
- [ ] Sensor: `{vehicle}_trips_list` (informational)
- [ ] Sensor: `{vehicle}_recurring_trips_count`
- [ ] Sensor: `{vehicle}_punctual_trips_count`
- [x] Register sensors via `async_setup_entry` (wiring en HA)

**Phase 1D: Dashboard Foundation (Day 4-5)** ✅
- [x] Basic Lovelace configuration example (`dashboard/dashboard.yaml`)
- [x] Weekly grid card (recurring trips)
- [x] Punctual trips list card
- [x] Vehicle status card
- [x] Card styling and layout

**Success Criteria**: ✅ ALL MET
- ✅ Can add/edit/delete trips via services
- ✅ Dashboard shows all trips correctly
- ✅ Data persists across HA restarts
- ✅ Existing MPC system unaffected (still uses sliders)
- ✅ All functionality is informational only
- ✅ TDD applied with 83% coverage (29 tests passing)

**Files Created**: ✅
- ✅ `custom_components/ev_trip_planner/trip_manager.py`
- ✅ `custom_components/ev_trip_planner/sensor.py`
- ✅ `custom_components/ev_trip_planner/services.yaml`
- ✅ `custom_components/ev_trip_planner/dashboard/dashboard.yaml`
- ⚪ `custom_components/ev_trip_planner/translations/en.json` (optional)
- ⚪ `custom_components/ev_trip_planner/translations/es.json` (optional)

**Outcome**: Core trip management ready for testing in HA environment. Next: Trip calculations (Milestone 2)

---

### ✅ Milestone 2: Trip Calculations (COMPLETED - Nov 22, 2025)

**Goal**: Calculate next trip and required charging hours (still informational)

**Tasks**:
- [x] Sensor: `{vehicle}_next_trip` (selects nearest future trip)
- [x] Sensor: `{vehicle}_next_deadline` (datetime of next trip)
- [x] Sensor: `{vehicle}_kwh_needed_today` (sum of all trips today)
- [x] Sensor: `{vehicle}_hours_needed_today` (ceil to integer)
- [x] Logic to expand recurring trips for next 7 days
- [x] Logic to combine recurring + punctual trips
- [x] Timezone handling
- [x] Edge cases (no trips, past trips, etc.)

**Success Criteria**:
- ✅ Next trip correctly identified
- ✅ kWh calculation accurate
- ✅ Hours always rounded UP (ceiling)
- ✅ Works with mixed recurring + punctual trips
- ✅ Dashboard shows calculated values
- ✅ Still informational (MPC not affected)

**Files to Modify**:
- `custom_components/ev_trip_planner/sensor.py` (add calculation sensors)
- `custom_components/ev_trip_planner/trip_manager.py` (add calculation logic)
- `custom_components/ev_trip_planner/dashboard/dashboard.yaml` (show calculations)

---

### ⚠️ Milestone 3: EMHASS Integration & Smart Charging Control (IMPLEMENTED - NOT VALIDATED)

**Status**: ⚠️ **CODE COMPLETE** but **NOT TESTED** in production environment

**Goal**: Transform informational trip system into active charging optimization

**✅ ARCHITECTURAL INNOVATION**: Implemented dynamic index assignment - each trip gets unique EMHASS index (0, 1, 2...) instead of fixed per-vehicle index. This enables multiple simultaneous trips per vehicle.

**Implementation Status**:
- ✅ **Phase 3A**: Configuration & Planning Setup - **CODE COMPLETE**
  - Extended config flow with EMHASS and presence detection steps
  - Added new status sensors (active trips, presence, charging readiness)
  - Created comprehensive unit tests (3A.5)
  
- ✅ **Phase 3B**: EMHASS Adapter & Deferrable Loads - **CODE COMPLETE**
  - Created `EMHASSAdapter` class with dynamic index management
  - Implemented index pool (0-49), assignment, release, and reuse
  - Added persistent storage for trip-to-index mappings
  - Created 9 comprehensive unit tests (3B.4)
  
- ✅ **Phase 3C**: Vehicle Control Interface - **CODE COMPLETE**
  - Created abstract `VehicleControlStrategy` with 4 implementations:
    - `SwitchStrategy` - Control via switch entity
    - `ServiceStrategy` - Control via custom service calls
    - `ScriptStrategy` - Control via script execution
    - `ExternalStrategy` - No direct control (notifications only)
  - Added config flow integration and validation
  - Created 5 unit tests (3C.3)
  
- ✅ **Phase 3D**: Schedule Monitor & Presence Detection - **CODE COMPLETE**
  - Created `ScheduleMonitor` class for real-time schedule monitoring
  - Created `PresenceMonitor` class with dual detection methods:
    - Sensor-based (binary_sensor for home/plugged status)
    - Coordinate-based (Haversine formula calculation)
  - Implemented safety logic: verify presence BEFORE executing control actions
  - Created 8 integration tests (3D.4)
  
- ⚠️ **Phase 3E**: Integration Testing & Migration - **PENDING VALIDATION**
  - ✅ Code complete: E2E tests, migration service
  - ✅ Unit tests: 156 tests, 93.6% passing
  - ❌ **Production testing**: NOT STARTED (requires deployment to HA local)
  - ❌ **Manual validation**: NOT STARTED (Step 3E.1 in implementation plan)

**Key Innovations**:
- ✅ **Dynamic Index Assignment**: Each trip automatically assigned unique EMHASS index
- ✅ **Index Persistence**: Mappings survive HA restarts via Home Assistant Store
- ✅ **Index Reuse**: Released indices automatically reused, preventing exhaustion
- ✅ **Multiple Trips**: True support for multiple simultaneous trips per vehicle
- ✅ **Safety First**: Presence verification prevents charging when vehicle not home/plugged
- ✅ **Smart Notifications**: Alerts when charging needed but not possible

**Files Created**:
- `custom_components/ev_trip_planner/emhass_adapter.py` (272 lines)
- `custom_components/ev_trip_planner/vehicle_controller.py` (110 lines)
- `custom_components/ev_trip_planner/schedule_monitor.py` (130 lines)
- `custom_components/ev_trip_planner/presence_monitor.py` (93 lines)
- `tests/test_emhass_adapter.py` (217 lines)
- `tests/test_vehicle_controller.py` (85 lines)
- `tests/test_schedule_monitor.py` (142 lines)
- `tests/test_presence_monitor.py` (98 lines)
- `tests/test_config_flow_milestone3.py` (156 lines)

**Files Modified**:
- `custom_components/ev_trip_planner/const.py` - 6 new constants
- `custom_components/ev_trip_planner/config_flow.py` - 2 new steps (EMHASS, Presence)
- `custom_components/ev_trip_planner/__init__.py` - Component integration
- `custom_components/ev_trip_planner/sensor.py` - 3 new status sensors
- `custom_components/ev_trip_planner/trip_manager.py` - Signal dispatching
- `custom_components/ev_trip_planner/services.yaml` - Migration service

**Testing Results**:
- **Unit Tests**: 156 tests, 93.6% passing (isolated test environment)
- **Coverage**: >80% for all new components
- **Key Metrics**:
  - EMHASSAdapter: 9/9 tests passing
  - VehicleController: 5/5 tests passing
  - ScheduleMonitor: 6/6 tests passing
  - PresenceMonitor: 4/4 tests passing
  - Integration: 8/8 tests passing

**⚠️ CRITICAL: Production Validation Required**:
- ❌ **Step 3E.1**: Manual testing in production environment (HA local) - **NOT STARTED**
- ❌ **Step 3E.2**: Migration service validation - **NOT STARTED**
- ❌ **Step 3E.3**: Final validation checklist - **NOT STARTED**

**Next Steps to Complete Milestone 3**:
1. Deploy to Home Assistant local environment (IN PROGRESS)
2. Configure test vehicle with EMHASS parameters
3. Create test trips and verify dynamic index assignment
4. Verify index persistence across restarts
5. Test presence detection with real sensors
6. Monitor for 24 hours without errors
7. Validate migration service with real data

**Known Limitations**:
- Manual EMHASS configuration required (user must add config snippet for each index up to max_deferrable_loads)
- Fixed planning horizon (does not dynamically adapt to EMHASS changes)
- Maximum simultaneous trips limited by EMHASS configuration (default 50, configurable)

**Documentation**:
- Complete implementation plan: `docs/MILESTONE_3_IMPLEMENTATION_PLAN.md` (2,765 lines)
- Architecture analysis: `docs/MILESTONE_3_ARCHITECTURE_ANALYSIS.md` (375 lines)
- Detailed refinement: `docs/MILESTONE_3_REFINEMENT.md` (888 lines)
- TDD methodology: `docs/TDD_METHODOLOGY.md`
- Closed issues: `docs/ISSUES_CLOSED_MILESTONE_3.md`

**Deployment Status**: ⚠️ **CODE DEPLOYED** - Pending production validation

---

### 🔴 Milestone 3.1: UX Improvements - Configuration Clarity (Target: 1-2 days)

**Status**: 📝 **PLANNED** - Identified during production testing

**Goal**: Fix critical UX issues preventing users from completing configuration

**Issues Identified**:
- ❌ **Issue #1**: Sensor selectors show all entities, not filtered by type (e.g., SOC should only show % sensors)
- ❌ **Issue #2**: "External EMHASS" is misleading - EMHASS doesn't control, it optimizes
- ❌ **Issue #3**: Planning horizon checkbox has no label or helper text
- ❌ **Issue #4**: Planning sensor entity shows no options and lacks description
- ❌ **Issue #5**: No helper text on any configuration fields

**Implementation Plan**:
- [ ] **Improvement #1**: Add entity filters (SOC→%, Plugged→binary_sensor, etc.)
- [ ] **Improvement #2**: Rename "External EMHASS" → "Notifications Only" with clear description
- [ ] **Improvement #3**: Add label "Use planning horizon sensor" + helper text
- [ ] **Improvement #4**: Filter numeric sensors only + add description with examples
- [ ] **Improvement #5**: Add `description` and `helper` to all config flow fields

**Files to Modify**:
- `custom_components/ev_trip_planner/config_flow.py` (entity selectors, labels)
- `custom_components/ev_trip_planner/strings.json` (helper texts)
- `custom_components/ev_trip_planner/translations/es.json` (Spanish translations)

**Success Criteria**:
- ✅ User can complete configuration without confusion
- ✅ Each field has clear description and examples
- ✅ Sensor lists only show relevant entities
- ✅ No "External EMHASS" confusion

**Documentation**: `docs/IMPROVEMENTS_POST_MILESTONE3.md` (Detailed improvement specifications)

---

### 🟡 Milestone 3.2: Advanced Configuration Options (Target: 1 week)

**Status**: 📝 **PLANNED** - For next release

**Goal**: Support dynamic battery capacity and consumption profiles

**Features**:
- [ ] **Feature #1**: Battery capacity as sensor (with SOH degradation support)
  - Option A: Direct capacity sensor (kWh)
  - Option B: SOH sensor (%) + nominal capacity → calculate real capacity
  - Option C: Manual entry (current method, fallback)
- [ ] **Feature #2**: Consumption profiles by trip type
  - Urban: Higher consumption (e.g., 0.18 kWh/km)
  - Highway: Lower consumption (e.g., 0.13 kWh/km)
  - Mixed: Average consumption (e.g., 0.15 kWh/km)
  - User selects type when creating trip

**Implementation**:
```python
# Battery capacity calculation
if capacity_source == "sensor":
    capacity = float(capacity_sensor.state)
elif capacity_source == "soh":
    soh = float(soh_sensor.state)
    nominal = config[CONF_BATTERY_CAPACITY_MANUAL]
    capacity = nominal * (soh / 100)
else:
    capacity = config[CONF_BATTERY_CAPACITY_MANUAL]
```

**Files to Modify**:
- `custom_components/ev_trip_planner/config_flow.py` (new battery config step)
- `custom_components/ev_trip_planner/sensor.py` (dynamic capacity calculation)
- `custom_components/ev_trip_planner/trip_manager.py` (consumption profiles)
- `custom_components/ev_trip_planner/services.yaml` (trip_type parameter)

**Success Criteria**:
- ✅ Battery capacity automatically adjusts for degradation
- ✅ kWh needed calculated based on trip type
- ✅ Backward compatible with manual configuration

**Documentation**: `docs/IMPROVEMENTS_POST_MILESTONE3.md` (Implementation examples)

---

### 📊 Updated Project Status

**Current Version**: 0.3.0-dev (Milestone 3 Code Complete)
**Development Stage**: Milestone 3 Implemented - Pending Validation
**Next Milestone**: 3.1 (UX Fixes) → 3.2 (Advanced Features) → 4 (Validation)

**Updated Timeline**:
- Milestone 3.1: 1-2 days (critical UX fixes)
- Milestone 3.2: 1 week (advanced features)
- Milestone 4: 3 days (polish and validation)
- **Total to v1.0**: ~2 weeks (including production validation)

---

### 📚 Documentation Structure

```
docs/
├── MILESTONE_3_IMPLEMENTATION_PLAN.md    # (2,765 lines) - Complete implementation
├── MILESTONE_3_ARCHITECTURE_ANALYSIS.md  # (375 lines) - Technical decisions
├── MILESTONE_3_REFINEMENT.md             # (888 lines) - Detailed refinement
├── TDD_METHODOLOGY.md                    # Test-driven development approach
├── ISSUES_CLOSED_MILESTONE_3.md          # Closed issues during development
└── IMPROVEMENTS_POST_MILESTONE3.md       # 🆕 UX and feature improvements identified
```

---

#### Phase 3A: Configuration & Planning Setup (Week 1)

**Goal**: Extend config flow to support EMHASS integration parameters

**Tasks**:
- [ ] Add `CONF_EMHASS_INDEX` to const.py (numeric index: 0, 1, 2...)
- [ ] Add `CONF_PLANNING_HORIZON` to const.py (default: 7 days)
- [ ] Add `CONF_HOME_SENSOR` to const.py (binary_sensor for presence)
- [ ] Add `CONF_PLUGGED_SENSOR` to const.py (binary_sensor for charging cable)
- [ ] Extend config_flow.py: Add step 4 "EMHASS Configuration"
- [ ] Extend config_flow.py: Add step 5 "Presence Detection" (optional)
- [ ] Validate EMHASS index uniqueness across vehicles
- [ ] Create config flow tests for new steps

**Critical Validation Points**:
- ✅ User must manually configure EMHASS deferrable loads to read our sensors
- ✅ **Each trip gets ONE unique EMHASS index** (0=OVMS Monday work, 1=OVMS Wednesday work, 2=Morgan Saturday shopping, etc.)
- ✅ Planning horizon must be ≤ EMHASS day-ahead horizon (typically 3-7 days)
- ✅ Module maintains dynamic mapping: `trip_id → emhass_index`

**Files Modified**:
- `custom_components/ev_trip_planner/const.py`
- `custom_components/ev_trip_planner/config_flow.py`
- `tests/test_config_flow.py`

---

#### Phase 3B: EMHASS Adapter & Deferrable Loads (Week 2)

**Goal**: Create adapter to publish trips as EMHASS-compatible deferrable loads

**Tasks**:
- [ ] Create `emhass_adapter.py` with `EMHASSAdapter` class
- [ ] Method: `async_publish_deferrable_load(trip)` → updates `sensor.emhass_deferrable_load_config_X`
- [ ] Calculate parameters: `def_total_hours`, `P_deferrable_nom`, `def_end_timestep`
- [ ] Trigger on trip changes (use dispatcher signal)
- [ ] Create `sensor.emhass_deferrable_load_config_X` entities dynamically
- [ ] Add unit tests for parameter calculations
- [ ] Document required EMHASS configuration snippet for users

**EMHASS Configuration Required** (user must add this manually):
```yaml
emhass:
  deferrable_loads:
    - def_total_hours: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'def_total_hours') | default(0) }}"
      P_deferrable_nom: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'P_deferrable_nom') | default(0) }}"
      def_start_timestep: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'def_start_timestep') | default(0) }}"
      def_end_timestep: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'def_end_timestep') | default(168) }}"
      # ... other parameters
    
    - def_total_hours: "{{ state_attr('sensor.emhass_deferrable_load_config_1', 'def_total_hours') | default(0) }}"
      # ... for index 1
```

**Files Created**:
- `custom_components/ev_trip_planner/emhass_adapter.py`
- `tests/test_emhass_adapter.py`

---

#### Phase 3C: Vehicle Control Interface (Week 3)

**Goal**: Abstract vehicle control mechanisms (switch, service, script)

**Tasks**:
- [ ] Create `vehicle_controller.py` with `VehicleController` class
- [ ] Implement strategies: `SwitchStrategy`, `ServiceStrategy`, `ScriptStrategy`
- [ ] Method: `async_activate_charging()` → turns on charging
- [ ] Method: `async_deactivate_charging()` → turns off charging
- [ ] Method: `async_get_status()` → returns current charging state
- [ ] Validate control entity exists during config flow
- [ ] Add tests for each strategy

**Control Strategies**:
- **Switch**: Use `switch.turn_on/off` service
- **Service**: Call custom service (e.g., `ovms/set_charge_mode`)
- **Script**: Execute `script.{vehicle}_start_charging`
- **External**: No control (notifications only)

**Files Created**:
- `custom_components/ev_trip_planner/vehicle_controller.py`
- `tests/test_vehicle_controller.py`

---

#### Phase 3D: Schedule Monitor & Presence Detection (Week 4)

**Goal**: Monitor EMHASS schedules and execute charging control with safety checks

**Tasks**:
- [ ] Create `schedule_monitor.py` with `ScheduleMonitor` class
- [ ] Subscribe to `sensor.emhass_deferrableX_schedule` changes
- [ ] Map schedule to vehicle control actions
- [ ] Create `presence_monitor.py` with `PresenceMonitor` class
- [ ] Implement home detection (sensor or coordinates)
- [ ] Implement plugged detection (binary_sensor)
- [ ] **CRITICAL**: Verify presence BEFORE executing any control action
- [ ] Send notifications if charging needed but not possible
- [ ] Add integration tests for full flow

**Safety Logic**:
```python
async def _async_execute_schedule(self, vehicle_id: str, action: str):
    presence_monitor = self.presence_monitors.get(vehicle_id)
    
    if not presence_monitor:
        _LOGGER.warning(f"No presence monitor for {vehicle_id}, assuming at home")
        await self._async_execute_control(vehicle_id, action)
        return
    
    # Verify AT HOME first
    is_at_home = await presence_monitor._async_check_home_status()
    if not is_at_home:
        _LOGGER.info(f"Vehicle {vehicle_id} not at home, ignoring action: {action}")
        await self._async_notify_vehicle_not_home(vehicle_id)
        return
    
    # Verify PLUGGED second
    is_plugged = await presence_monitor._async_check_plugged_status()
    if not is_plugged:
        _LOGGER.info(f"Vehicle {vehicle_id} not plugged, ignoring action: {action}")
        await self._async_notify_vehicle_not_plugged(vehicle_id)
        return
    
    # Only if both conditions met: execute action
    await self._async_execute_control(vehicle_id, action)
```

**Files Created**:
- `custom_components/ev_trip_planner/schedule_monitor.py`
- `custom_components/ev_trip_planner/presence_monitor.py`
- `tests/test_schedule_monitor.py`
- `tests/test_presence_monitor.py`

---

#### Phase 3E: Integration Testing & Migration Tool (Week 5)

**Goal**: Validate complete system and provide migration path from sliders

**Tasks**:
- [ ] Create `test_integration.py` with E2E scenarios
- [ ] Scenario 1: Single recurring trip → EMHASS schedule → charging activation
- [ ] Scenario 2: Multiple vehicles with different priorities
- [ ] Scenario 3: Presence detection prevents activation when away
- [ ] Scenario 4: Fallback to manual control when EMHASS fails
- [ ] Create migration service: `ev_trip_planner.import_from_sliders`
- [ ] Read `input_number.{vehicle}_carga_necesaria_{dia}` and convert to trips
- [ ] Add preview mode (show what would be created)
- [ ] Deploy to test environment and monitor for 48h
- [ ] Measure latency: trip creation → deferrable load → schedule → activation

**Migration Service Example**:
```yaml
service: ev_trip_planner.import_from_sliders
data:
  vehicle_id: "chispitas"
  preview: true  # Show what would be created without actually creating
```

**Files Created**:
- `tests/test_integration.py`
- Migration service in `trip_manager.py`

---

### Success Criteria (Milestone 3 Complete)

- ✅ **Configuration**: Users can configure EMHASS index and presence sensors
- ✅ **Deferrable Loads**: Each vehicle's trips are published to correct EMHASS index
- ✅ **Control**: Charging activates/deactivates based on EMHASS schedule
- ✅ **Safety**: No charging activation when vehicle not at home or not plugged
- ✅ **Notifications**: Users alerted when charging is needed but not possible
- ✅ **Testing**: All scenarios pass in integration tests
- ✅ **Migration**: Users can import from existing slider system
- ✅ **Stability**: System runs 48h in test environment without errors

---

### Files Modified Summary

**New Files** (5):
- `emhass_adapter.py` - Publish trips to EMHASS
- `vehicle_controller.py` - Abstract vehicle control
- `schedule_monitor.py` - Monitor and execute schedules
- `presence_monitor.py` - Detect home/plugged status
- `tests/test_integration.py` - E2E testing

**Modified Files** (4):
- `const.py` - Add new configuration constants
- `config_flow.py` - Add steps 4-5 for EMHASS and presence config
- `sensor.py` - Add sensors for deferrable load status
- `services.yaml` - Add migration service

**User Action Required**:
- Manually add EMHASS configuration snippet to read our sensors
- Configure presence sensors (optional but recommended)
- Run migration service to import from sliders (optional)

---

### Timeline & Risk Assessment

| Phase | Duration | Risk Level | Rollback Strategy |
|-------|----------|------------|-------------------|
| 3A: Configuration | 1 week | Low | Delete config entries |
| 3B: EMHASS Adapter | 1 week | Medium | Disable adapter, revert to manual |
| 3C: Vehicle Control | 1 week | Medium | Use external control mode |
| 3D: Schedule Monitor | 1 week | **HIGH** | Disable monitor, manual charging only |
| 3E: Integration | 1 week | Low | Revert to Phase 3C |

**Total Duration**: 5 weeks (vs. 5 days original) → **More realistic and safe**

**Critical Path**: Phase 3D (Schedule Monitor) - Most complex, requires all previous phases

---

### ⚪ Milestone 4: Validation & Polish (Target: 3 days)

**Goal**: Ensure system is production-ready

**Tasks**:
- [ ] Comprehensive testing with edge cases
- [ ] Error handling and user notifications
- [ ] Performance optimization
- [ ] Dashboard refinements
- [ ] Documentation updates
- [ ] User guide and examples
- [ ] Video tutorial (optional)

**Success Criteria**:
- ✅ System handles all edge cases gracefully
- ✅ Clear error messages for users
- ✅ Dashboard is intuitive
- ✅ Complete documentation
- ✅ Ready for community use

---

### ⚪ Milestone 5: Advanced Features (Optional - Target: 5 days)

**Goal**: Add nice-to-have features

**Possible Features**:
- [ ] Voice command support (HA Assist integration)
- [ ] Calendar entity (show trips in HA calendar)
- [ ] Notifications (trip ready, charging started, etc.)
- [ ] Statistics and history tracking
- [ ] Mobile app shortcuts
- [ ] Automation examples

**Success Criteria**:
- ✅ Voice commands work reliably
- ✅ Notifications are helpful not annoying
- ✅ Users have example automations to copy

---

## 🎯 User Experience Simplification (Post v1.0 - Critical Improvements)

**Goal**: Eliminate user friction and data inconsistencies

### Phase 1: Input Normalization & Validation
- [ ] **Day name normalization**: Sanitize any variant (Miércoles, Miercoles, miercoles, MIÉRCOLES) → canonical lowercase without accents
- [ ] **Vehicle ID normalization**: Auto-convert to slug format (spaces → underscores, lowercase)
- [ ] **Input validation**: Real-time feedback in config flow and services

### Phase 2: Smart Trip Creation
- [ ] **Eliminate kWh manual entry**: Remove redundant kWh field that risks contradictory data (e.g., 1000km with 1kWh)
- [ ] **Origin-destination geocoding**: Accept addresses/coordinates instead of manual km entry
- [ ] **Automatic consumption calculation**: kWh = distance × vehicle_efficiency
- [ ] **Travel time estimation**: Calculate duration based on route and traffic

### Phase 3: Conversational AI Interface
- [ ] **Natural language processing**: "Voy de Madrid a Barcelona mañana a las 9"
- [ ] **Intent recognition**: Extract origin, destination, datetime automatically
- [ ] **Voice integration**: HA Assist compatibility for hands-free trip planning

**Success Criteria**:
- ✅ Zero data entry errors from format inconsistencies
- ✅ No manual kWh calculations required
- ✅ Sub-30-second trip creation via voice/text
- ✅ 100% backward compatibility maintained

**Files to Modify**:
- `custom_components/ev_trip_planner/trip_manager.py` (normalization helpers)
- `custom_components/ev_trip_planner/services.yaml` (new parameters)
- `custom_components/ev_trip_planner/config_flow.py` (geocoding API config)
- `custom_components/ev_trip_planner/manifest.json` (add unidecode dependency)

**Dependencies**:
- `unidecode` library (for accent removal)
- Geocoding API (Google Maps / OpenStreetMap Nominatim)
- Vehicle efficiency database (kWh/km per model)
---

## 🚀 Future Versions (Post v1.0)

### v1.1: Multi-Vehicle Support
- Support for 2+ vehicles
- Shared charging line management
- Vehicle prioritization logic
- Conflict detection and resolution

### v1.2: Optimizer Integration
- Native EMHASS integration
- Support for other optimizers
- Custom optimization rules
- Dynamic pricing integration

### v1.3: Smart Learning
- Learn actual consumption from history
- Predict based on weather/traffic
- Adaptive safety margins
- Battery degradation tracking

### v1.4: Route Planning
- Google Maps / OpenStreetMap integration
- Automatic distance calculation from address
- Multi-stop trip planning
- Charging station detection en route

### v1.5: Fleet Management
- Multi-user support
- Company/family fleet management
- User permissions and roles
- Centralized dashboard

---

## 🎯 Use Cases Prioritization

### P0 - Must Have (v1.0)
- ✅ Single vehicle with automatic charge control
- ✅ Single vehicle with notifications only (no control)
- ✅ Recurring weekly trips (routine)
- ✅ Punctual one-time trips (events)
- ✅ Basic calculations and deadline management

### P1 - Should Have (v1.1)
- ⚠️ Multi-vehicle with shared charging line
- ⚠️ EMHASS integration for optimization
- ⚠️ Advanced dashboard with graphs

### P2 - Nice to Have (v1.2+)
- ⚠️ PHEV with hybrid logic
- ⚠️ Dynamic pricing optimization (non-EMHASS)
- ⚠️ Voice commands and AI assistant

### P3 - Future (v2.0+)
- ⚠️ Fleet management
- ⚠️ Route planning with maps
- ⚠️ Multi-user support

---

## 📊 Supported Vehicle Integrations

### Tested (by development team)
- [x] OVMS (Nissan Leaf) - Reference implementation
- [x] V2C EVSE (Dacia Spring) - Reference implementation

### Planned Testing (community help needed)
- [ ] Tesla (most common)
- [ ] Renault ZOE
- [ ] Hyundai/Kia
- [ ] BMW i3
- [ ] VW ID series
- [ ] Generic EVSE (smart plugs)

---

## 🤝 Contributing

We welcome contributions at any stage! Current priorities:

**High Priority**:
- Testing with different EV integrations
- UI/UX feedback on dashboard
- Translation to other languages
- Documentation improvements

**Medium Priority**:
- Additional vehicle integration examples
- Automation templates
- Bug reports and fixes

**Low Priority**:
- Advanced features (wait for v1.0)
- Performance optimizations

---

## 📝 Development Phases Summary

| Milestone | Duration | Status | Risk | Notes |
|-----------|----------|--------|------|-------|
| 0. Foundation | 1 day | ✅ DONE | Low | Repo ready |
| 1. Infrastructure | 5 days | ✅ DONE | Low | Pure addition |
| 2. Calculations | 3 days | ✅ DONE | Low | All sensors working |
| 3. MPC Integration | 5 days | ⚪ Pending | ⚠️ HIGH | Modifies existing code |
| 4. Validation | 3 days | ⚪ Pending | Medium | Testing phase |
| 5. Advanced | 5 days | ⚪ Optional | Low | Nice-to-have |

**Total Estimated Time**: ~14-22 days (depending on scope)

---

## 🎉 Version History

### v0.1.0-dev (Current)
- Initial project structure
- Config flow skeleton
- Basic constants and domain setup

### v1.0.0 (Target: Q1 2025)
- Full trip management system
- Dashboard with weekly grid + punctual list
- MPC integration (hybrid mode)
- HACS ready for community

---

**Last Updated**: November 22, 2025  
**Next Review**: After Milestone 3 completion

---

## 📬 Questions or Feedback?

Open an issue or discussion on GitHub:
- **Issues**: https://github.com/informatico-madrid/ha-ev-trip-planner/issues
- **Discussions**: https://github.com/informatico-madrid/ha-ev-trip-planner/discussions

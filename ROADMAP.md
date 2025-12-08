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

### ⚪ Milestone 3: MPC Integration (CRITICAL - Target: 5 days)

**Goal**: Actually use trip system in MPC optimization

**Phase 3A: Hybrid Sensor (Day 1-2)**
- [ ] Sensor: `{vehicle}_deadline_hybrid` (trips OR sliders)
- [ ] Logic: If trips exist → use trips, else → use sliders
- [ ] Modify only `sensor.{vehicle}_hours_until_deadline`
- [ ] Extensive testing before deployment

**Phase 3B: Testing & Monitoring (Day 3-4)**
- [ ] Deploy to production with monitoring
- [ ] Verify MPC receives correct values
- [ ] Check EMHASS `def_total_hours` updates correctly
- [ ] Monitor for 2-3 days before continuing
- [ ] Rollback capability ready

**Phase 3C: Migration Tool (Day 5)**
- [ ] Button: "Import sliders to recurring trips"
- [ ] Automatic conversion logic
- [ ] User validation before activation
- [ ] Gradual transition plan

**Success Criteria**:
- ✅ MPC uses trip deadlines when trips exist
- ✅ Falls back to sliders when no trips
- ✅ No INFEASIBLE errors (unless genuine)
- ✅ Charging schedules correct
- ✅ System stable for 2-3 days
- ✅ User can migrate from sliders

**⚠️ CRITICAL**: This is the only phase that modifies existing working code

**Files to Modify**:
- `homeassistant/templates/template_sensors_ovms_mpc_control.yaml` (ONE sensor only)
- `homeassistant/templates/template_sensors_morgan_mpc_control.yaml` (ONE sensor only)

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

# Updates to ROADMAP.md - April 26, 2026

## CHANGES TO ROADMAP.md

### 1. Update Milestone 4.0.1 Status

**OLD:**
```markdown
## 🚧 Next: Milestone 4.0.1 — Critical M4 Hotfixes

**Status**: 📋 PLANNED — not started
**Problem details**: [`doc/gaps/gaps.es.md`](doc/gaps/gaps.es.md)
**Target**: v0.4.3-dev
**Priority**: Blocks M4.1 start — these issues prevent EMHASS integration from working correctly in production
```

**NEW:**
```markdown
## ✅ Milestone 4.0.1 — Critical M4 Hotfixes (COMPLETED)

**Status**: ✅ COMPLETED — 2026-04-26
**Spec**: [`specs/m401-emhass-hotfixes/`](specs/m401-emhass-hotfixes/)
**Target**: v0.5.21
**PR**: [#26](https://github.com/informatico-madrid/ha-ev-trip-planner/pull/26)

### Completed Features

#### Gap #8 — EMHASS Per-Trip Sensors ✅
- **TripEmhassSensor** class implemented with 9 attributes
- Per-trip EMHASS parameters (def_total_hours, P_deferrable_nom, def_start_timestep, def_end_timestep, power_profile_watts, deadline, soc_target, vehicle_id, trip_id, emhass_index)
- Sensor lifecycle tied to trip (create/update/delete with trip)
- Device grouping under vehicle device (not per-trip device)
- Automatic EMHASS configuration via `p_deferrable_matrix` attribute

#### Gap #5 — Charging Power Update ✅
- Fixed `entry.options.get("charging_power_kw")` read from options flow
- Activated `setup_config_entry_listener()` in `__init__.py`
- Profile updates propagate immediately on config change

#### Additional Fixes ✅
- **7 EMHASS bugs** fixed (datetime, math.ceil, template keys, entity IDs)
- **Hours deficit propagation algorithm** for multi-trip charging
- **82 TDD tasks** completed with 100% pass rate
- **1470 tests** passing, 100% coverage on new code

### Technical Details
- **Files Modified**: sensor.py, emhass_adapter.py, trip_manager.py, __init__.py, panel.js
- **New Tests**: test_trip_emhass_sensor.py, test_propagate_charge_deficit.py
- **Documentation**: docs/emhass-setup.md with Jinja2 templates
- **Quality**: Mypy clean (19 files, 0 errors)

---

## 🚧 Next: Milestone 4.0.2 — Panel UX Improvements

**Status**: 📋 PLANNED — not started
**Priority**: P1 - User Experience
**Target**: v0.5.22

### Planned Features

#### Panel UX Debt Reduction
- **Remove hardcoded CSS gradients**: Replace `#667eea`, `#764ba2` with HA theme variables
  - Use `--ha-card-background`, `--primary-color`, `--secondary-color`
  - Respect HA light/dark theme mode
- **Responsive design improvements**: Mobile-friendly panel layout
- **HA theme integration**: All colors use semantic theme variables

#### EMHASS Configuration UX
- **In-panel EMHASS config display**: Show ready-to-copy YAML/Jinja2 templates
- **Copy button**: One-click copy of EMHASS configuration
- **Dynamic template generation**: Always shows current trip configuration

### Estimate
- **Time**: 3-5 days
- **Complexity**: Low-Medium (CSS refactoring + minor JS changes)
- **Files**: frontend/panel.js, frontend/panel.css
```

### 2. Add Completed Specs to "Completed Milestones History"

**ADD after Milestone 4:**

```markdown
### Milestone 4.0.1: EMHASS Per-Trip Sensors & Hotfixes (Apr 26, 2026)
- `TripEmhassSensor`: Per-trip EMHASS sensors with 9 attributes
- Gap #8 fixed: EMHASS now receives per-trip optimization profiles
- Gap #5 fixed: Charging power updates from options flow
- Hours deficit propagation algorithm for multi-trip charging
- 7 EMHASS integration bugs fixed (datetime, math.ceil, template keys)
- 82 TDD tasks completed, 1470 tests passing, 100% coverage
- Enhanced EMHASS aggregated sensor with `p_deferrable_matrix` attribute
- PR #26 merged (m401-emhass-per-trip-sensors branch)
- CHANGELOG: [0.5.21]
```

### 3. Update "Known Limitations" Section

**REMOVE:**
```markdown
1. **⚠️ EMHASS automatic charge control NOT WORKING (P0 Critical)**: `schedule_monitor.py` (324 lines) exists but is **never instantiated**.
```

**ADD:**
```markdown
### Resolved in M4.0.1
- ~~Gap #8: EMHASS per-trip sensors~~ ✅ FIXED - TripEmhassSensor implemented
- ~~Gap #5: Charging power not updating~~ ✅ FIXED - entry.options read implemented
- ~~7 EMHASS integration bugs~~ ✅ FIXED - datetime, math.ceil, template keys
```

### 4. Update "What's Next" Section

**ADD new section:**

```markdown
## 📋 Immediately After M4.0.1 (Priority Order)

### P0 — Panel UX (Technical Debt)
1. **Remove hardcoded CSS** - Replace gradients with HA theme variables
2. **Responsive design** - Mobile-friendly layout improvements
3. **HA theme integration** - Respect light/dark mode

### P1 — Documentation
1. **Update EMHASS setup guide** - Reflect per-trip sensor changes
2. **Panel user guide** - How to use new EMHASS config display
3. **Migration guide** - From aggregated-only to per-trip sensors

### P2 — Enhancement Candidates
1. **ScheduleMonitor activation** - Wire automatic charge control
2. **Config flow options expansion** - Make all 20+ fields editable
3. **Multi-vehicle power balancing** - Shared charging line management
```

---

## SUMMARY OF CHANGES

### Specs Verified as COMPLETED ✅
1. **m401-emhass-hotfixes** - 82 tasks, PR #26 merged
2. **fix-emhass-aggregated-sensor** - 7 bugs fixed, verified in code
3. **propagate-charge-deficit-algo** - Algorithm implemented in calculations.py
4. **solid-refactor-coverage** - protocols.py, definitions.py added
5. **fix-sequential-trip-charging** - Fixed in v0.5.16-0.5.17

### Specs Descartadas (Muy Viejas - Mismo Timestamp)
- trip-card-enhancement, soc-integration-baseline, regression-orphaned-sensors (Apr 8)
- duplicate-emhass-sensor-fix, emhass-sensor-entity-lifecycle, trip-creation, emhass-sensor-enhancement, e2e-trip-crud, charging-window-calculation (Apr 6-7)
- soc-milestone-algorithm, automation-template, 020-fix-panel-trips-sensors (Mar 2026)

**Reason**: Same creation timestamp suggests batch creation without execution. Code verification shows no traces of implementation.

### Specs Recientes Requieren Verificación
- e2e-ux-tests-fix (Apr 23) - Requiere verificación E2E
- pr35-review-fixes (Apr 24) - Requiere revisión de PR #35
- propagate-charge-test, propagate-charge-wiring, emhass-integration-with-fixes (Apr 24) - Requiere verificación de código

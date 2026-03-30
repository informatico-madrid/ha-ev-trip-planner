# Tasks: Charging Window Calculation

## Phase 1: Implementation (POC)

### CRITICAL PREREQUISITE (Must understand before 1.1)

- [x] 0.1 Read Spec 1 context: `hora_regreso` stored in `PresenceMonitor` via `hass.states.async_set()` at entity `sensor.ev_trip_planner_{vehicle_id}_return_info`
  - **Do**: Review presence_monitor.py lines 68, 78-84, 198-241 for storage pattern
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: Understanding of hora_regreso persistence mechanism
  - **Verify**: `grep -n "hora_regreso\|_return_info_entity_id" custom_components/ev_trip_planner/presence_monitor.py`
  - **Commit**: None (research task)

### Implementation Tasks

- [x] 1.1 Implement `calcular_ventana_carga()` function in trip_manager.py
  - **Do**:
    1. Add function `calcular_ventana_carga(trip, soc_actual, hora_regreso, charging_power_kw)` to TripManager
    2. Parse `hora_regreso` string to datetime using `datetime.fromisoformat()` with error handling
    3. Calculate `inicio_ventana`:
       - If `hora_regreso` exists: use it (car returned at this real time)
       - If `hora_regreso` is None: use `trip.departure_time - 6h` (estimated return, 6h before departure)
    4. Calculate `fin_ventana` = trip departure time (from `trip["datetime"]` or `trip["hora"]`)
    5. Calculate `ventana_horas` = difference between fin_ventana and inicio_ventana in hours
    6. Calculate `kwh_necesarios` using existing `async_calcular_energia_necesaria()` logic
    7. Calculate `horas_carga_necesarias` = kwh_necesarios / charging_power_kw
    8. Calculate `es_suficiente` = ventana_horas >= horas_carga_necesarias
    9. Return dict with all calculated values
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Function signature matches plan.md interface contract
  - **Verify**: `grep -n "def calcular_ventana_carga" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(charging): implement calcular_ventana_carga function`
  - _Requirements: AC-1, AC-2, AC-3, AC-4, AC-5_
  - _Design: Interface Contracts section (plan.md)_

- [x] 1.2 Add helper to read `hora_regreso` from HA state entity
  - **Do**:
    1. Add method `async_get_hora_regreso()` to PresenceMonitor that reads from `hass.states.get(_return_info_entity_id)`
    2. The state attributes contain `hora_regreso_iso` as ISO string
    3. Return `Optional[datetime]` parsed from the entity state/attributes
    4. Handle missing entity or None values gracefully (return None)
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: PresenceMonitor can retrieve hora_regreso from HA state entity
  - **Verify**: `grep -n "async_get_hora_regreso" custom_components/ev_trip_planner/presence_monitor.py`
  - **Commit**: `feat(presence): add async_get_hora_regreso method`
  - _Requirements: AC-2, AC-3_
  - _Design: Dependencies section - reading hora_regreso from Spec 1_

- [x] 1.3 Add helper to get next pending trip after a given time
  - **Do**:
    1. Add method `async_get_next_trip_after(hora_regreso: datetime)` to TripManager
    2. Filter punctual trips with datetime > hora_regreso and estado=pendiente
    3. Filter recurring trips with hora > hora_regreso.time() for today's day_of_week and activo=True
    4. Return the earliest trip by departure time
    5. Return None if no trips pending after hora_regreso
    6. Note: Si hora_regreso is None (car not yet returned), use estimated arrival = departure_time + 6h for window calculation
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: TripManager can query next trip after a given time
  - **Verify**: `grep -n "async_get_next_trip_after" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(trips): add async_get_next_trip_after helper`
  - _Requirements: AC-1, AC-4_
  - _Design: Multi-trip window chaining logic_

- [x] 1.4 Handle edge case: no trips pending (AC-5)
  - **Do**:
    1. In `calcular_ventana_carga()`, check if next trip exists after hora_regreso
    2. If no trip exists, return dict with:
       - ventana_horas: 0
       - kwh_necesarios: 0
       - horas_carga_necesarias: 0
       - inicio_ventana: None
       - fin_ventana: None
       - es_suficiente: True (no charging needed)
    3. This ensures power profile generates all zeros when no trips pending
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: No trips pending returns zero-values dict
  - **Verify**: `grep -n "no trips\|no pending" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(charging): handle no pending trips edge case`
  - _Requirements: AC-5_
  - _Design: AC-5 edge case handling_

- [x] 1.5 Handle multi-trip window chaining (AC-4)
  - **Do**:
    1. Add function `calcular_ventana_carga_multitrip(trips, soc_actual, hora_regreso, charging_power_kw)` to TripManager
    2. Sort trips by departure time (earliest first)
    3. For first trip: ventana starts at hora_regreso (real time when car returns, from Spec 1)
    4. For subsequent trips: ventana starts at previous trip's arrival time
    5. **Duracion del viaje: 6 horas hardcoded por defecto** - cada viaje termina 6h despues de su salida
    6. Si el coche no ha llegado (hora_regreso aun no detectada), usar departure_time + 6h como estimado
    7. Cuando el coche real llegue a casa, Spec 1 detecta y auto-recalcula las ventanas (AC-3)
    8. Calculate window for each trip individually
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Multiple trips in same day each get own window from previous trip end
  - **Verify**: `grep -n "calcular_ventana_carga_multitrip\|window.*chained" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(charging): implement multi-trip window chaining`
  - _Requirements: AC-4_
  - _Design: Multi-trip window chaining section (plan.md)_

- [x] 1.6 Wire hora_regreso reading into power profile generation
  - **Do**:
    1. Modify `async_generate_power_profile()` to accept optional `hora_regreso` parameter
    2. If `hora_regreso` is None, read it from `presence_monitor.async_get_hora_regreso()`
    3. Use `calcular_ventana_carga()` to determine window instead of assuming "now"
    4. Si no hay hora_regreso detectada aun: usar departure_time + 6h como estimado para la ventana
    5. Cuando el coche llegue a casa: `hora_regreso` se actualiza (Spec 1 detecta off->on) y se auto-recalcula (SOC change listener de Spec 1 dispara recalculo)
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Power profile generation uses actual return time for window calculation
  - **Verify**: `grep -n "hora_regreso" custom_components/ev_trip_planner/trip_manager.py | grep -v "_return_info"`
  - **Commit**: `feat(charging): wire hora_regreso into power profile generation`
  - _Requirements: AC-2, AC-3_
  - _Design: SOC change triggers recalculation section (plan.md)_

- [ ] 1.7 POC Checkpoint: Verify basic window calculation
  - **Do**:
    1. Create test: hora_regreso=18:00, next trip=22:00, verify ventana=4 hours
    2. Run the test to verify calculation is correct
    3. Verify function returns all expected fields
  - **Done when**: Basic window calculation works correctly
  - **Verify**: `pytest tests/test_trip_manager.py -v --tb=short -k "window" 2>&1 | tail -30`
  - **Commit**: `chore(charging): verify POC of window calculation`

### Quality Checkpoints

- [ ] 1.8 [VERIFY] Quality checkpoint: lint and type check
  - **Do**: Run lint and type checks on modified files
  - **Verify**: `pylint custom_components/ev_trip_planner/trip_manager.py custom_components/ev_trip_planner/presence_monitor.py && python -m mypy custom_components/ev_trip_planner/trip_manager.py custom_components/ev_trip_planner/presence_monitor.py --ignore-missing-imports`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(charging): pass quality checkpoint` (only if fixes needed)
  - _Files: trip_manager.py, presence_monitor.py_

### Testing Tasks

- [ ] 1.9 Add unit tests for calcular_ventana_carga
  - **Do**:
    1. Create `tests/test_charging_window.py`
    2. Add test: Basic window calculation (AC-1: 18:00 return, 22:00 trip = 4h window)
    3. Add test: hora_regreso in future (car not yet returned) - window does NOT start
    4. Add test: No pending trips returns zero values (AC-5)
    5. Add test: Multiple trips get separate windows (AC-4)
    6. Add test: es_suficiente is True when window >= charging time
    7. Add test: es_suficiente is False when window < charging time
    8. Add test: Invalid hora_regreso format handled gracefully
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: All new tests pass
  - **Verify**: `pytest tests/test_charging_window.py -v --tb=short 2>&1 | tail -40`
  - **Commit**: `test(charging): add unit tests for calcular_ventana_carga`
  - _Requirements: AC-1 through AC-5_
  - _Design: Test Strategy_

- [ ] 1.10 Add unit tests for multi-trip window chaining
  - **Do**:
    1. Add test: Two trips same day - second trip window starts at first trip departure
    2. Add test: Three trips same day - each gets sequential window
    3. Add test: First trip window starts at hora_regreso, subsequent at previous arrival
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: All multi-trip tests pass
  - **Verify**: `pytest tests/test_charging_window.py -v --tb=short -k "multi" 2>&1 | tail -30`
  - **Commit**: `test(charging): add tests for multi-trip window chaining`
  - _Requirements: AC-4_
  - _Design: Test Strategy_

## Phase 2: Verification

- [ ] 2.1 [VERIFY] Full local CI: lint && typecheck && test
  - **Do**: Run complete local CI suite
  - **Verify**: `pylint --rcfile=.pylintrc custom_components/ev_trip_planner/*.py && python -m mypy custom_components/ev_trip_planner/*.py --ignore-missing-imports && pytest tests/ -v --tb=short`
  - **Done when**: Build succeeds, all tests pass, no lint/type errors
  - **Commit**: `chore(charging): pass local CI` (only if fixes needed)

- [ ] 2.2 [VERIFY] CI pipeline passes
  - **Do**: Verify GitHub Actions/CI passes after push
  - **Verify**: `gh run list --workflow=ci.yml 2>&1 | head -10`
  - **Done when**: CI pipeline passes
  - **Commit**: None

## Notes
- **Duracion del viaje: 6 horas hardcoded por defecto** - todos los viajes duran 6h hasta que el coche vuelve
- **Return detection**: Cuando el coche vuelve a casa, Spec 1 (PresenceMonitor) detecta off->on y actualiza `hora_regreso`
- **Auto-recalculo**: Cuando `hora_regreso` cambia, el SOC listener de Spec 1 dispara `async_generate_power_profile()` automaticamente
- **Si el coche no llega a tiempo**: No pasa nada. El sistema espera. Cuando el coche finalmente llegue, se detecta y se auto-recalcula
- **Sin hora_regreso**: Si no hay `hora_regreso` detectada aun, se usa `departure_time - 6h` como estimado para la ventana
- POC shortcuts: No deficit propagation yet (Spec 3)
- Dependencies: Requires Spec 1 (soc-integration-baseline) for hora_regreso persistence and auto-recalculation
- Storage pattern: hora_regreso stored via ha_storage.Store and hass.states.async_set() in presence_monitor.py
- State entity: `sensor.ev_trip_planner_{vehicle_id}_return_info` contains hora_regreso_iso attribute
- Datetime: Use `dt_util.now()` for timezone-aware HomeAssistant datetime, parse with `datetime.fromisoformat()`

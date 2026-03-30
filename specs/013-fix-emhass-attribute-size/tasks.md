---

description: "Task list for fixing EMHASS deferrables_schedule attribute size exceeding 16KB limit"

---

# Tasks: Fix EMHASS Attribute Size - SPEC 013

**Input**: Production warning logs showing:
```
State attributes for sensor.ev_trip_planner_chispitas_emhass_perfil_diferible_01kmxtcmhkc12w3s1ege3sxd0w exceed maximum size of 16384 bytes
```

**Root Cause**: `_generate_schedule_from_trips` generates 168 entries (7 days × 24 hours), each entry containing `date` + `p_deferrable{n}` keys. With multiple trips and 7 days, the total size exceeds HA's 16KB state attributes limit.

**Fix**: Reduce schedule from 168 hours (7 days) to 24 hours (1 day).

**Prerequisites**: emhass-sensor-enhancement (completed)

**Tests**: Following TDD - tests were updated to reflect 24-hour schedule

---

## Phase 1: Root Cause Verification

- [x] 1.1 [VERIFY] Confirm deferrables_schedule size issue
  - **Do**: Check `_generate_schedule_from_trips` in emhass_adapter.py
  - **Verify**: `grep -n "range(168)" custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Confirmed the 168-hour loop is the cause

## Phase 2: Implementation

- [x] 2.1 Fix schedule generation to use 24 hours instead of 168
  - **Do**: Change `range(168)` to `range(24)` in emhass_adapter.py
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Verify**: `grep -n "range(24)" custom_components/ev_trip_planner/emhass_adapter.py`
  - **Commit**: `fix(emhass): reduce deferrables_schedule from 168h to 24h`

- [x] 2.2 Update tests to expect 24 entries instead of 168
  - **Do**: Update test assertions in test_emhass_adapter.py
  - **Files**: tests/test_emhass_adapter.py
  - **Verify**: `grep -n "len(schedule) == 24" tests/test_emhass_adapter.py`
  - **Commit**: `test(emhass): update schedule length assertions to 24`

## Phase 3: Verification

- [x] 3.1 [VERIFY] All EMHASS adapter tests pass
  - **Do**: Run pytest on emhass adapter tests
  - **Verify**: `python3 -m pytest tests/test_emhass_adapter.py -v --tb=short`
  - **Done when**: All 76 tests pass

- [x] 3.2 [VERIFY] All deferrable load sensor tests pass
  - **Do**: Run pytest on deferrable load sensor tests
  - **Verify**: `python3 -m pytest tests/test_deferrable_load_sensors.py -v --tb=short`
  - **Done when**: All tests pass

- [x] 3.3 [VERIFY] Full test suite passes
  - **Do**: Run full pytest suite
  - **Verify**: `python3 -m pytest tests/ --no-cov -v`
  - **Done when**: All 872 tests pass

## Notes

- **Why 24 hours?**: EMHASS optimization runs on hourly cycles, so 24 hours provides sufficient look-ahead for daily planning
- **Impact**: Reduces attribute size from ~20KB+ to ~4KB for typical configurations
- **Compatibility**: EMHASS will re-query as hours pass; this is consistent with the optimization cycle

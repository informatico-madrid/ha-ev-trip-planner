# Requirements: Fix Sequential Trip Charging

## Goal
Fix the bug where `def_start_timestep_array` shows `[0, 0]` for sequential trips when the second trip's charging window should start after the first trip completes plus a fixed return buffer.

## User Stories

### US-1: Sequential Trip Charging Window Calculation
**As a** EV trip planner user
**I want to** have sequential trips with correctly computed def_start_timestep values
**So that** each trip's charging window starts after the previous trip completes plus the return buffer

**Acceptance Criteria:**
- [ ] AC-1.1: Given two sequential trips, def_start_timestep_array[1] > def_start_timestep_array[0]
- [ ] AC-1.2: Given N sequential trips, each def_start_timestep[i] > def_start_timestep[i-1]
- [ ] AC-1.3: Single trip def_start_timestep remains unchanged at 0
- [ ] AC-1.4: def_end_timestep_array values remain unchanged after fix
- [ ] AC-1.5: p_deferrable_matrix values remain unchanged (already correct)

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Batch process all trips through calculate_multi_trip_charging_windows() | High | Function called once with all trips instead of once per trip |
| FR-2 | Compute sequential def_start_timestep for each trip | High | def_start_timestep[i] uses batch-computed inicio_ventana for i > 0 |
| FR-3 | Add RETURN_BUFFER_HOURS constant to const.py | High | RETURN_BUFFER_HOURS = 4.0 constant defined |
| FR-4 | Add return_buffer_hours parameter to calculate_multi_trip_charging_windows() | High | New parameter added alongside existing duration_hours |
| FR-5 | Backward compatibility for single trips | High | Single trip behavior unchanged (def_start_timestep = 0) |
| FR-6 | Pass pre-computed batch results to _populate_per_trip_cache_entry() | High | Method accepts and uses batch-computed inicio_ventana |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Performance | Additional latency per batch publish | < 100ms |
| NFR-2 | Maintainability | Code duplication reduction | 100% (single call site) |
| NFR-3 | Testability | Unit test coverage for multi-trip logic | 100% of calculate_multi_trip_charging_windows edge cases |
| NFR-4 | Backward compatibility | Existing single-trip behavior | 100% unchanged |
| NFR-5 | No regressions | Existing test suite | All 1519+ tests pass |

## Glossary

- **def_start_timestep**: Zero-based timestep index from optimization window start when charging can begin
- **def_end_timestep**: Zero-based timestep index from optimization window start when charging must complete
- **return_buffer**: Fixed time gap (4h) between when a trip ends and the next trip's charging window starts
- **duration_hours**: Trip duration — how long the car is away (used for trip_arrival calculation)
- **sequential trips**: Multiple trips scheduled where each trip's charging occurs after the previous trip
- **p_deferrable_matrix**: Power profile matrix showing charging watts per timestep per trip
- **EMHASS**: Energy Management and Optimization of Home Energy Storage Systems
- **hora_regreso**: Actual return time datetime (dynamic, from presence_monitor) used as start reference for first trip's charging window
- **inicio_ventana**: Calculated window start datetime for each trip

## Out of Scope
- Changing def_end_timestep calculation logic
- Modifying p_deferrable_matrix generation
- Adding new sensors or entities
- Changing the charging power calculation
- Support for overlapping trips (out of scope for this bug fix)
- UI changes to existing trip management
- Configurable return buffer (constant only for MVP)
- Reactive update when buffer changes (not needed — constant is immutable)

## Dependencies
- **calculations.py**: `calculate_multi_trip_charging_windows()` function must accept return_buffer_hours parameter
- **sensor.py**: Aggregated sensor already collects arrays correctly (no changes needed)
- **const.py**: Existing pattern for configuration constants
- **presence_monitor.py**: Already provides dynamic hora_regreso (no changes needed)

## Success Criteria
- def_start_timestep_array shows correct sequential offsets: [0, X, Y, ...] where X > 0
- Single trip behavior unchanged: def_start_timestep = 0
- RETURN_BUFFER_HOURS constant exists with value 4.0
- All existing tests pass
- No regression in p_deferrable_matrix or def_end_timestep_array values

## Verification Contract

**Project type**: fullstack

**Entry points**:
- `emhass_adapter.py:async_publish_all_deferrable_loads()` - Batch processing entry point
- `calculations.py:calculate_multi_trip_charging_windows()` - Multi-trip window calculation function with return_buffer_hours
- `sensor.py` - Aggregated sensor reading (read-only verification)

**Observable signals**:
- PASS: `def_start_timestep_array` shows sequential offsets like [0, 10, 24] for three trips
- PASS: `def_end_timestep_array` unchanged (e.g., [11, 49, 80])
- PASS: `p_deferrable_matrix` unchanged (already correct)
- FAIL: `def_start_timestep_array` shows [0, 0, 0] (old buggy behavior)
- FAIL: Single trip def_start_timestep != 0

**Hard invariants**:
- Single-trip functionality unchanged
- Existing trip data must continue to work
- EMHASS API contract maintained (timestep indices remain valid integers)
- duration_hours parameter semantics preserved (trip duration, not buffer)

**Seed data**:
- At least 2 sequential trips with different deadlines
- SOC sensor available (fallback 50.0 if unavailable)
- Charging power configured (default 11.0 kW)

**Dependency map**:
- `emhass_adapter.py` → `calculations.py` (calls calculate_multi_trip_charging_windows)
- `emhass_adapter.py` → `sensor.py` (cached params aggregated by sensor)
- `const.py` → `calculations.py` (RETURN_BUFFER_HOURS constant)

**Escalate if**:
- Trip deadlines overlap with return_buffer calculation
- Return buffer larger than time between trips (window_start > trip_deadline)
- Existing tests fail without clear regression cause
- EMHASS response indicates invalid timestep values

## Unresolved Questions
- What should happen when return_buffer calculation results in window_start > trip deadline? Should we cap at deadline or extend window?

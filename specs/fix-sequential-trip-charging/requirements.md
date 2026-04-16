# Requirements: Fix Sequential Trip Charging

## Goal
Fix the bug where `def_start_timestep_array` shows `[0, 0]` for sequential trips when the second trip's charging window should start after the first trip completes plus a configurable return buffer.

## User Stories

### US-1: Sequential Trip Charging Window Calculation
**As a** EV trip planner user
**I want to** have sequential trips with correctly computed def_start_timestep values
**So that** each trip's charging window starts after the previous trip completes plus the return buffer

**Acceptance Criteria:**
- [ ] AC-1.1: Given two sequential trips, def_start_timestep_array[1] = def_end_timestep_array[0] + return_buffer_hours
- [ ] AC-1.2: Given N sequential trips, each def_start_timestep[i] = def_end_timestep[i-1] + return_buffer_hours
- [ ] AC-1.3: Single trip def_start_timestep remains unchanged at 0
- [ ] AC-1.4: def_end_timestep_array values remain unchanged after fix
- [ ] AC-1.5: p_deferrable_matrix values remain unchanged (already correct)

### US-2: Configurable Return Buffer
**As a** EV trip planner user
**I want to** configure the return buffer duration between sequential trips
**So that** the buffer can be adjusted based on my typical trip patterns (0-12 hours)

**Acceptance Criteria:**
- [ ] AC-2.1: Config option return_buffer_hours exists with default value 4.0
- [ ] AC-2.2: Config option range is 0.0 to 12.0 hours (step 0.5h)
- [ ] AC-2.3: Config option accessible via vehicle settings UI
- [ ] AC-2.4: New return_buffer_hours value applies to all new sequential trip calculations
- [ ] AC-2.5: Existing trips use default 4.0h buffer if config not updated

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Batch process all trips through calculate_multi_trip_charging_windows() | High | Function called once with all trips instead of once per trip |
| FR-2 | Compute sequential def_start_timestep for each trip | High | def_start_timestep[i] = def_end_timestep[i-1] + return_buffer for i > 0 |
| FR-3 | Add return_buffer_hours configuration option | Medium | Option added to config_flow.py with validation |
| FR-4 | Add return_buffer_hours constant to const.py | High | CONF_RETURN_BUFFER_HOURS = "return_buffer_hours" |
| FR-5 | Backward compatibility for single trips | High | Single trip behavior unchanged (def_start_timestep = 0) |
| FR-6 | Store published trips for reactive updates | Medium | Existing _published_trips used to republish when config changes |
| FR-7 | Update charging windows when return_buffer_hours changes | Low | Republish triggers recalculation with new buffer value |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Performance | Additional latency per batch publish | < 100ms |
| NFR-2 | Maintainability | Code duplication reduction | 100% (single call site) |
| NFR-3 | Testability | Unit test coverage for multi-trip logic | 100% of calculate_multi_trip_charging_windows edge cases |
| NFR-4 | Backward compatibility | Existing single-trip behavior | 100% unchanged |
| NFR-5 | Configuration validation | Input validation | 0.0-12.0 hours, step 0.5h |

## Glossary

- **def_start_timestep**: Zero-based timestep index from optimization window start when charging can begin
- **def_end_timestep**: Zero-based timestep index from optimization window start when charging must complete
- **return_buffer**: Time (hours) between trip end and next trip's charging window start
- **sequential trips**: Multiple trips scheduled where each trip's charging occurs after the previous trip
- **p_deferrable_matrix**: Power profile matrix showing charging watts per timestep per trip
- **EMHASS**: Energy Management and Optimization of Home Energy Storage Systems
- **hora_regreso**: Return time datetime used as start reference for first trip's charging window

## Out of Scope
- Changing def_end_timestep calculation logic
- Modifying p_deferrable_matrix generation
- Adding new sensors or entities
- Changing the charging power calculation
- Support for overlapping trips (out of scope for this bug fix)
- UI changes to existing trip management

## Dependencies
- **calculations.py**: `calculate_multi_trip_charging_windows()` function must accept multiple trips
- **sensor.py**: Aggregated sensor already collects arrays correctly (no changes needed)
- **config_flow.py**: Existing pattern for adding new config options
- **const.py**: Existing pattern for configuration constants

## Success Criteria
- def_start_timestep_array shows correct sequential offsets: [0, X, Y, ...] where X = end_timestep[0] + buffer
- Single trip behavior unchanged: def_start_timestep = 0
- Config option return_buffer_hours exists with default 4.0h and range 0-12h
- All existing tests pass
- No regression in p_deferrable_matrix or def_end_timestep_array values

## Verification Contract

**Project type**: fullstack

**Entry points**:
- `emhass_adapter.py:async_publish_all_deferrable_loads()` - Batch processing entry point
- `emhass_adapter.py:async_publish_deferrable_load()` - Per-trip publishing (must remain for individual trip management)
- `calculations.py:calculate_multi_trip_charging_windows()` - Multi-trip window calculation function
- `custom_components/ev_trip_planner/config_flow.py:STEP_EMHASS_SCHEMA` - Configuration schema for new option
- `sensor.py` - Aggregated sensor reading (read-only verification)

**Observable signals**:
- PASS: `def_start_timestep_array` shows sequential offsets like [0, 10, 24] for three trips
- PASS: `def_end_timestep_array` unchanged (e.g., [11, 49, 80])
- PASS: `p_deferrable_matrix` unchanged (already correct)
- PASS: Config option `return_buffer_hours` appears in vehicle settings with default 4.0
- FAIL: `def_start_timestep_array` shows [0, 0, 0] (old buggy behavior)
- FAIL: Single trip def_start_timestep != 0
- FAIL: Config option missing or validation fails for out-of-range values

**Hard invariants**:
- Auth/session validity unchanged
- Permissions enforcement unchanged
- Data belonging to other users/tenants not affected
- Single-trip functionality unchanged
- Existing trip data (without sequential processing) must continue to work
- EMHASS API contract maintained (timestep indices remain valid integers)

**Seed data**:
- Config entry with default values (including new return_buffer_hours)
- At least 2 sequential trips with different deadlines
- SOC sensor available (fallback 50.0 if unavailable)
- Charging power configured (default 11.0 kW)

**Dependency map**:
- `emhass_adapter.py` → `calculations.py` (calls calculate_multi_trip_charging_windows)
- `emhass_adapter.py` → `sensor.py` (cached params aggregated by sensor)
- `config_flow.py` → `const.py` (imports CONF_RETURN_BUFFER_HOURS)
- `coordinator.py` → `emhass_adapter.py` (retrieves cached per-trip params)

**Escalate if**:
- Trip deadlines overlap with return_buffer calculation (e.g., trip 2 starts before trip 1 + buffer)
- Return buffer larger than time between trips (window_start > trip_deadline)
- Existing tests fail without clear regression cause
- EMHASS response indicates invalid timestep values
- Performance degradation > 100ms per publish operation

## Unresolved Questions
- What should happen when return_buffer calculation results in window_start > trip deadline? Should we cap at deadline or extend window?
- Should existing trips be retroactively updated with new return_buffer value or only new trips?
- Is there a minimum return_buffer value (e.g., 1h) that makes practical sense for EV charging?

## Next Steps
1. Review and approve requirements with stakeholder
2. Implement FR-4: Add CONF_RETURN_BUFFER_HOURS constant to const.py
3. Implement FR-3: Add return_buffer_hours config option to config_flow.py with validation
4. Implement FR-1 & FR-2: Modify async_publish_all_deferrable_loads() to batch process trips
5. Add unit tests for multi-trip charging window calculation
6. Run existing test suite to verify no regressions
7. Test with real sequential trips in Home Assistant environment

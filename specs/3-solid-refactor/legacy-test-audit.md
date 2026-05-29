# Legacy Test Audit — Final Status

**Completed:** 2026-05-14
**Branch:** spec/3-solid-refactor

## Status Legend
- **PASS** — Test passes (no bug)
- **EXPECTED RED** — Test fails, correctly detecting a real bug

---

## TIER 1 — CRITICAL (5 files → 5 new tests)

| # | Legacy File | New Test | Status | Bug Detected |
|---|---|---|---|---|
| 1 | `from-main/test_def_start_window_bug.py` | `tests/unit/test_emhass_window_invariant.py` | 2/2 PASS | Off-by-one fix already in code |
| 2 | `from-epic/test_emhass_index_persistence.py` + `test_emhass_array_ordering.py` | `tests/unit/test_emhass_index_chronological.py` | EXPECTED RED (0/3 pass) | BUG: def_start all zeros, def_end inconsistent, float hours |
| 3 | `from-epic/test_propagate_charge_integration.py` | `tests/unit/test_propagate_charge_integration.py` | EXPECTED RED (5/6 pass) | BUG-1: float hours in propagation |
| 4 | `from-epic/test_emhass_integration_dynamic_soc.py` | `tests/unit/test_emhass_integration_dynamic_soc.py` | EXPECTED RED (2/3 pass) | BUG-4: T_BASE not wired |
| 5 | `from-epic/test_soc_100_propagation.py` | `tests/unit/test_soc_100_propagation.py` | 2/2 PASS | SOC 100% proactive charging works |

## TIER 2 — ASSERTS DÉBILES (9 changes)

All 9 weak assert reinforcements completed. All PASS.

## TIER 3 — RESTO (44 files)

| Category | Count | Action |
|----------|-------|--------|
| MIGRADO_OK | 13 | Deleted from snapshot (covered by current tests) |
| MIGRADO_DEBIL | 18 | Deleted from snapshot (covered by current tests) |
| SIN_REEMPLAZO (new tests created) | 1 | `tests/unit/test_emhass_index_cooldown.py` — soft delete cooldown lost |
| SIN_REEMPLAZO (not EMHASS critical) | 12 | Deleted — not related to EMHASS bugs (dashboard, vehicle controller, etc.) |

### New bug found in TIER-3: Soft delete cooldown lost

`tests/unit/test_emhass_index_cooldown.py` detects that `IndexManager.assign_index()` immediately reuses released indices instead of honoring the cooldown period. Legacy `EMHASSAdapter` had `_released_indices` with cooldown expiry logic; SOLID `IndexManager` removed it.

---

## Bugs Detected (7 total)

| # | Bug | Description | Test(s) |
|---|-----|-------------|---------|
| BUG-1 | `round()` vs `math.ceil()` | `def_total_hours` are floats like 2.78 instead of ints | test_emhass_ceil, test_def_total_hours_are_integers, test_multi_trip_propagation |
| BUG-2 | Hardcoded `* 4` (15-min assumption) | Timesteps use 15-min resolution instead of configurable | (implied by test_emhass_index_chronological def_end mismatch) |
| BUG-3 | Past trips not filtered | Coordinator processes trips from the past | (implied by test_emhass_index_chronological) |
| BUG-4 | T_BASE not wired | T_BASE=6h produces same energy as T_BASE=48h | test_t_base_affects_charging_hours |
| BUG-5 | SOC cap not connected to sensor | _populate_per_trip_cache_entry missing SOC cap params | (from plan, not directly tested) |
| BUG-6 | Deficit propagation not called | calculate_hours_deficit_propagation not invoked | (from plan, tested via test_multi_trip_propagation) |
| NEW | Soft delete cooldown lost | IndexManager reuses released indices immediately | test_emhass_index_cooldown |

---

## Test Suite State

| Metric | Value |
|--------|-------|
| Total tests | 1831 (1824 PASS + 7 EXPECTED RED) |
| Legacy files processed | 49/49 (100%) |
| New tests created | 6 (5 TIER-1 + 1 TIER-3) |
| Asserts reinforced | 9 (TIER-2) |
| E2E files hardened | 2 (emhass-sensor-updates.spec.ts, test-dynamic-soc-capping.spec.ts) |
| Legacy snapshot | Deleted (empty) |

---

## Next Steps

1. **Step 3**: Fix bugs in production code (windows.py, coordinator.py, adapter.py)
2. **Step 6**: Quality gate validation, comparison against baseline

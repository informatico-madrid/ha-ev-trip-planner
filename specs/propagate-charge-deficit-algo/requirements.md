# Requirements: Propagate Charge Deficit Algorithm

## Goal

Propagate charging hours deficit backward across chained trips so overflow hours are absorbed by earlier trips with spare capacity instead of being silently discarded.

## User Stories

### US-1: Absorb unsatisfied charging time into earlier trips
**As a** trip planner user with multiple chained trips
**I want to** have charging deficit from a constrained trip propagate to earlier trips with spare window capacity
**So that** all required charging happens without silently dropping hours

**Acceptance Criteria:**
- [ ] AC-1.1: Given 3 trips where trip #3 needs 3h but has 2h window, the 1h deficit propagates to trip #2
- [ ] AC-1.2: Given trip #2 has spare capacity (its `def_total_hours` < its `ventana_horas`), it absorbs the deficit up to its spare amount
- [ ] AC-1.3: If trip #2 has no spare capacity, the deficit continues to trip #1
- [ ] AC-1.4: If trip #1 cannot absorb the full deficit (first trip has no predecessor), the remaining deficit stays on trip #1 as `deficit_hours_to_propagate`
- [ ] AC-1.5: `ventana_horas` is never modified by propagation — only `def_total_hours` is adjusted

### US-2: Produce enriched window dicts compatible with downstream consumers
**As a** downstream consumer (EMHASS adapter, SOC display)
**I want to** receive window dicts with propagation metadata
**So that** I can act on absorbed deficits without re-deriving the algorithm

**Acceptance Criteria:**
- [ ] AC-2.1: Each returned dict contains the original keys: `ventana_horas`, `inicio_ventana`, `fin_ventana`, `horas_carga_necesarias`
- [ ] AC-2.2: Each returned dict contains `deficit_hours_propagated` (hours absorbed from subsequent trips), rounded to 2 decimal places
- [ ] AC-2.3: Each returned dict contains `deficit_hours_to_propagate` (remaining deficit after absorption), rounded to 2 decimal places
- [ ] AC-2.4: Each returned dict contains `adjusted_def_total_hours` = original `def_total_hours` + `deficit_hours_propagated`, rounded to 2 decimal places

### US-3: Leave existing SOC propagation path untouched
**As a** system maintainer
**I want to** `calculate_multi_trip_charging_windows()` and `calculate_deficit_propagation()` to remain unchanged
**So that** existing SOC display and sensor paths continue to work without regression

**Acceptance Criteria:**
- [ ] AC-3.1: `calculate_multi_trip_charging_windows()` returns the same output before and after adding the new function
- [ ] AC-3.2: `calculate_deficit_propagation()` returns the same output before and after adding the new function
- [ ] AC-3.3: The new function is a pure function — no I/O, no state mutation, no side effects

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | New function `calculate_hours_deficit_propagation(windows, battery_capacity_kwh)` in `calculations.py` | High | Function exists in `calculations.py`, importable, takes windows list and battery capacity |
| FR-2 | Function walks backward from last trip to first | High | Iteration order is last-to-first; last trip is evaluated first for deficit |
| FR-3 | Deficit = `horas_carga_necesarias - ventana_horas` when positive | High | For each trip, if `horas_carga_necesarias > ventana_horas`, excess is the candidate deficit |
| FR-4 | Each trip's `deficit_hours_propagated` = deficit absorbed from subsequent trips (not its own overflow) | High | `deficit_hours_propagated` on trip N reflects only hours taken from trip N+1, N+2, etc. |
| FR-5 | Previous trip absorbs up to its spare capacity: spare = `def_total_hours_original - ventana_horas` (floored at 0) | High | If spare <= 0, previous trip absorbs 0 hours from the incoming deficit |
| FR-6 | `deficit_hours_to_propagate` on last trip = raw deficit from its own overflow minus what it can absorb (0 for last trip) | Medium | For last trip, `deficit_hours_to_propagate = horas_carga_necesarias - ventana_horas` |
| FR-7 | `deficit_hours_to_propagate` on intermediate trip N = incoming deficit from N+1 minus what trip N absorbs | Medium | Tracked per-trip; propaged only if positive |
| FR-8 | `adjusted_def_total_hours` = original `def_total_hours` + `deficit_hours_propagated` for each trip | High | Sum equals the absorbed total; verifiable post-computation |
| FR-9 | `ventana_horas` is never modified in returned dicts | High | Assert `ventana_horas` equals input value for every returned dict |
| FR-10 | Empty input returns empty list | Low | `calculate_hours_deficit_propagation([], 60.0) == []` |
| FR-11 | Single trip with no deficit returns dict with all propagation fields = 0 | Low | `deficit_hours_propagated=0`, `deficit_hours_to_propagate=0` if `horas_carga_necesarias <= ventana_horas` |
| FR-12 | Single trip with deficit returns dict with deficit on `deficit_hours_to_propagate` | Low | All overflow sits on `deficit_hours_to_propagate`; cannot propagate anywhere |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Purity | Side effects | Zero — no DB, no I/O, no mutation |
| NFR-2 | Determinism | Same input | Same output every call |
| NFR-3 | Performance | 10 trips | < 1ms on typical hardware |

## Glossary

- **Deficit**: The hours a trip needs to charge (`horas_carga_necesarias`) minus the hours available in its window (`ventana_horas`), when positive.
- **Spare capacity**: How much a trip's window can absorb from subsequent trips: `def_total_hours - ventana_horas`, floored at 0.
- **Backward propagation**: The direction of deficit flow — from later trips (last) to earlier trips (first), opposite the forward allocation order.
- **`def_total_hours`**: The total charging hours assigned to a trip (original demand, potentially inflated by absorbed deficits).
- **`ventana_horas`**: The available charging window size in hours. Immutable by propagation.

## Out of Scope

- Modifying `calculate_multi_trip_charging_windows()` — stays unchanged
- Modifying `calculate_deficit_propagation()` — stays in SOC domain only
- Wiring this function into `emhass_adapter.py` — handled by a separate spec
- Integration or end-to-end tests — handled by a separate spec
- Forward propagation (first trip absorbs from later trips) — not required
- Visualizing propagated deficits in UI — handled by trip card spec
- Modifying `determine_charging_need()` or `_populate_per_trip_cache_entry()` directly

## Dependencies

- `calculations.py` — must import into `custom_components/ev_trip_planner/calculations.py`
- `calculate_multi_trip_charging_windows()` — provides the input windows format
- `_populate_per_trip_cache_entry()` in `emhass_adapter.py` — downstream consumer that will use `adjusted_def_total_hours` (future spec)
- `calculate_energy_needed()` — feeds `horas_carga_necesarias` into window dicts

## Success Criteria

- [ ] When all trips have sufficient windows, zero deficits are reported across all trips
- [ ] When last trip has deficit and middle trip has spare capacity, deficit is fully absorbed (no `deficit_hours_to_propagate` remaining)
- [ ] When all trips are tight, deficit accumulates on the first trip's `deficit_hours_to_propagate`
- [ ] Existing tests for `calculate_multi_trip_charging_windows()` and `calculate_deficit_propagation()` continue to pass unchanged

## Verification Contract

**Project type**: `api-only`

**Entry points**:
- `calculations.calculate_hours_deficit_propagation()` — new function
- `calculations.calculate_multi_trip_charging_windows()` — existing function (no changes)

**Observable signals**:
- PASS: Returned list of window dicts with `deficit_hours_propagated` and `deficit_hours_to_propagate` keys present; values sum correctly across trips
- FAIL: `ventana_horas` modified in output; original keys missing; non-numeric propagation values

**Hard invariants**:
- `ventana_horas` must equal the input value for every returned dict (never modified)
- `inicio_ventana` and `fin_ventana` must equal the input values (never modified)
- `calculate_multi_trip_charging_windows()` output is identical before and after
- `calculate_deficit_propagation()` output is identical before and after
- No side effects: calling the function twice with same input returns same output

**Seed data**:
- Minimum: 3 window dicts from `calculate_multi_trip_charging_windows()` with known `ventana_horas` and `horas_carga_necesarias` values
- Battery capacity: 60.0 kWh (typical)
- Window scenario: trip #1 spare=4h, trip #2 spare=2h, trip #3 deficit=1h

**Dependency map**:
- `calculations.py` — single file, no cross-module dependencies for this function
- `emhass_adapter.py` — reads propagation metadata from enriched dicts (future consumer)
- `test_calculations.py` — must add test classes for the new function

**Escalate if**:
- `ventana_horas` in input window dicts can be 0 (division-by-zero risk in spare capacity calc — clarify behavior)
- `def_total_hours` is not present in input window dicts (requires clarification on whether to read from dict or compute from `horas_carga_necesarias`)
- Input windows may come from `calculate_energy_needed()` path instead of `calculate_multi_trip_charging_windows()` path — requires confirming input contract

## Unresolved Questions
- What should `adjusted_def_total_hours` represent for trips that have NO absorbed deficit (value = original `def_total_hours` or value = `ventana_horas`)?
- Does `def_total_hours` exist as a key in input window dicts, or should the function derive it from `horas_carga_necesarias`?
- If a trip has negative spare capacity (`ventana_horas < def_total_hours`), should it absorb 0 or should this be flagged?

## Next Steps
1. Write `calculate_hours_deficit_propagation()` in `custom_components/ev_trip_planner/calculations.py`
2. Add `TestCalculateHoursDeficitPropagation` test class to `tests/test_calculations.py`
3. Verify existing tests for `calculate_multi_trip_charging_windows()` and `calculate_deficit_propagation()` pass unchanged
4. Append learnings to `.progress.md`

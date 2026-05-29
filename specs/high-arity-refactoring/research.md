# Research: high-arity-refactoring

## Executive Summary

Spec 3 (SOLID refactoring, PR #47) already addressed the majority of high-arity violations. Of the 20 functions with >5 params found in the post-Spec3 codebase, most are either already `qg-accepted` with BMAD consensus or carry documented rationale. The 6 functions named in the epic ACs are all either already approved, partially refactored, or no longer exist. The actual remaining work is **4–5 function wrappers** in `calculations/` — all pure functions, low-risk. Project convention is established: `@dataclass(frozen=True)` named `<FunctionName>Params`, co-located with the target function.

**Feasibility**: High | **Risk**: Low | **Effort**: XS (< 0.5 story points)

---

## External Research

### Best Practices

**Pattern decision**: `@dataclass(frozen=True)` — already the codebase standard. No alternatives needed.

| Pattern | Verdict |
|---------|---------|
| `@dataclass(frozen=True)` | **Use** — project standard, stdlib, pyright-native, immutable |
| `TypedDict` | Only for dict-shaped returns (already used in `_types.py`) |
| `NamedTuple` | Avoid — positional access confusing, no default_factory |
| `attrs` | Avoid — third-party, overkill, not in project |
| Builder | Avoid — pure functions, no cross-field invariants, not idiomatic Python |
| `**kwargs` | Never — loses type safety |

**Key rules**:
- `kw_only=True` recommended for 5+ field dataclasses (Python 3.10+, pyright-supported)
- Never `field(default=[])` — always `field(default_factory=list)` (RUF009/B006)
- Naming convention: `<FunctionName>Params` (established: `VentanaCargaParams`, `PerTripCacheParams`)
- Location convention: co-locate dataclass with function in same module (established pattern)

### Pitfalls to Avoid

1. **Caller update cascade** — grep for all callers before touching signature; update tests first
2. **Positional arg tests** — update test callers alongside function signature (Option B: clean PR)
3. **`_populate_per_trip_cache_entry` special case** — partially migrated; backward-compat kwargs must be removed after test callers updated
4. **`qg-accepted` functions** — do not touch; they have BMAD consensus with documented rationale
5. **No `__post_init__` validation needed** — none of the existing param objects use it; keep new ones simple
6. **Builder pattern** — not needed; all targets are pure computations

---

## Codebase Analysis

### Current High-Arity Violations (post-Spec3 full scan)

| Params | Function | File | Status |
|--------|----------|------|--------|
| 11 | `_try_populate_window()` | `calculations/power.py:307` | `qg-accepted` (BMAD consensus) |
| 10 | `_propagate_deficits()` | `calculations/deficit.py:149` | `qg-accepted` (BMAD consensus) |
| 9 | `calculate_deficit_propagation()` | `calculations/deficit.py:257` | `qg-accepted` (AC-4.2 → DONE) |
| 8 | `_build_milestone()` | `calculations/deficit.py:200` | `qg-accepted` (BMAD consensus) |
| 8 | `calculate_multi_trip_charging_windows()` | `calculations/windows.py:223` | `qg-accepted` (AC-4.1 → DONE) |
| 8 | `calculate_power_profile()` | `calculations/power.py:152` | `qg-accepted` (AC-4.4 → DONE) |
| 8 | `calculate_power_profile_from_trips()` | `calculations/power.py:80` | `qg-accepted` (AC-4.3 → DONE) |
| 7 | `_populate_per_trip_cache_entry()` | `emhass/adapter.py:715` | Partial (AC-4.6 → cleanup kwargs) |
| 7 | `_compute_window_start()` | `calculations/windows.py:324` | Needs wrap |
| 6 | `_validate_field()` | `config_flow/main.py:264` | Assess (method — `self` reduces count) |
| 6 | `calculate_charging_window_pure()` | `calculations/windows.py:103` | Needs wrap |
| 6 | `_populate_profile()` | `calculations/power.py:288` | Needs wrap |
| 6 | `calculate_energy_needed()` | `calculations/windows.py:19` | `qg-accepted` |
| 6 | `calculate_trip_time()` | `calculations/core.py:207` | `qg-accepted` |
| 6 | `_handle_trip_created_recurring()` | `trip/_sensor_callbacks.py:52` | `qg-accepted` (framework callback) |
| 6 | `_handle_trip_created_punctual()` | `trip/_sensor_callbacks.py:66` | `qg-accepted` (framework callback) |
| 6 | `_handle_trip_sensor_created_emhass()` | `trip/_sensor_callbacks.py:80` | `qg-accepted` (framework callback) |
| 6 | `_handle_trip_removed()` | `trip/_sensor_callbacks.py:92` | `qg-accepted` (framework callback) |
| 6 | `_handle_trip_sensor_removed_emhass()` | `trip/_sensor_callbacks.py:104` | `qg-accepted` (framework callback) |
| 6 | `_handle_trip_sensor_updated()` | `trip/_sensor_callbacks.py:115` | `qg-accepted` (framework callback) |

### Epic AC Status (post-Spec3)

| AC | Function | Current Location | Status |
|----|----------|-----------------|--------|
| AC-4.1 | `calculate_multi_trip_charging_windows` | `calculations/windows.py:223` | ✅ `qg-accepted` — DONE |
| AC-4.2 | `calculate_deficit_propagation` | `calculations/deficit.py:257` | ✅ `qg-accepted` — DONE |
| AC-4.3 | `calculate_power_profile_from_trips` | `calculations/power.py:80` | ✅ `qg-accepted` — DONE |
| AC-4.4 | `calculate_power_profile` | `calculations/power.py:152` | ✅ `qg-accepted` — DONE |
| AC-4.5 | `DashboardImportResult.__init__` | ❌ Not in codebase | ✅ Removed/never created — DONE |
| AC-4.6 | `_populate_per_trip_cache_entry` | `emhass/adapter.py:715` | ⚠️ Partial — backward-compat kwargs to remove |

**Actual remaining work** (not in epic ACs, found by audit):
- `_compute_window_start()` — 7 params, private, `calculations/windows.py:324`
- `calculate_charging_window_pure()` — 6 params, `calculations/windows.py:103`
- `_populate_profile()` — 6 params, private, `calculations/power.py:288`
- `_validate_field()` — 6 params (method), `config_flow/main.py:264` — assess after removing `self`

### Existing Dataclass Conventions

Co-location pattern (same file as function):

| Dataclass | File | Purpose |
|-----------|------|---------|
| `PerTripCacheParams` | `emhass/adapter.py` | Reduces `_populate_per_trip_cache_entry` arity 11→2 |
| `ChargingDecision` | `calculations/deficit.py` | Pure decision output |
| `VentanaCargaParams` | `trip/_soc_window.py` | Params for window calc |
| `SOCInicioParams` | `trip/_soc_window.py` | Params for SOC inicio |
| `SOCWindowCalculator` | `trip/_soc_window.py` | Params for SOC milestones |

All use `@dataclass(frozen=True)`. No TypedDict, NamedTuple, or attrs anywhere.

### Post-Spec3 Module Structure

```
calculations/
  _helpers.py     — timezone, hours, watts helpers
  core.py         — BatteryCapacity, trip time logic
  windows.py      — charging window calculations  ← 3 targets here
  deficit.py      — deficit propagation
  power.py        — power profile calculations    ← 2 targets here
  schedule.py     — deferrable schedule
emhass/
  adapter.py      — EMHASSAdapter                ← 1 partial target
config_flow/
  main.py         — config flow                  ← 1 target to assess
```

---

## Related Specs

| Spec | Relevance | Relationship |
|------|-----------|--------------|
| `3-solid-refactor` | High | Completed — decomposed `calculations.py` into packages; moved all target functions to new locations; added `qg-accepted` comments |
| `solid-refactor-coverage` | Medium | Test coverage for SOLID refactor — tests for refactored functions live here |
| `propagate-charge-deficit-algo` | Low | Algorithm work on `calculate_deficit_propagation` — already qg-accepted |

---

## Quality Commands

| Type | Command | Notes |
|------|---------|-------|
| Tests | `make test` | Full unit + integration suite |
| TypeCheck | `make typecheck` | pyright basic mode |
| Lint | `make lint` | ruff + pylint |
| All checks | `make check` | test + lint + typecheck |
| Layer 3A (arity check) | `make layer3a` | SOLID AST scan — max_arity=5 threshold |
| Quality gate | `make quality-gate` | Full 6-layer gate |

**Arity enforcement**: `solid_metrics.py` in Layer 3A — threshold `max_arity=5`. Not enforced by ruff/pylint (disabled). Suppressible with `# qg-accepted:` comment.

**Venv**: All commands require `. .venv/bin/activate` — or use `.venv/bin/` prefix directly.

---

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|-----------|-------|
| Scope | Small | 3–4 new dataclasses + 1 cleanup |
| Risk | Low | All targets are pure functions; no side effects |
| Breaking changes | Minimal | Only callers within `calculations/` + `emhass/adapter.py` + tests |
| Pattern clarity | High | Convention fully established — just follow it |
| Epic ACs status | Mostly done | 5/6 ACs already satisfied post-Spec3 |
| Tooling | Ready | `make check` covers all quality gates |

---

## Recommendations for Requirements

1. **Reframe spec goal**: Not "refactor 6 functions" but "close arity debt" — audit-confirm what Spec 3 did, wrap the 3–4 remaining pure functions, close the epic AC.

2. **Functions to wrap** (new dataclasses needed):
   - `_compute_window_start` → `WindowStartParams` in `calculations/windows.py`
   - `calculate_charging_window_pure` → `ChargingWindowParams` in `calculations/windows.py`
   - `_populate_profile` → `PopulateProfileParams` (or merge into `PowerProfileParams`) in `calculations/power.py`

3. **AC-4.6 cleanup**: Remove backward-compat kwargs from `_populate_per_trip_cache_entry` after updating test callers.

4. **AC-4.7 validation**: After wrapping, run `make layer3a` — confirm zero arity violations (or all remaining have `qg-accepted`).

5. **`_validate_field` assessment**: Method with `self` — effective param count is 5 (excluding self). May already be compliant; verify before adding to scope.

6. **Do not wrap `qg-accepted` functions** — they have BMAD consensus; touching them reopens consensus discussions.

---

## Open Questions

1. Should `_validate_field(self, ...)` in `config_flow/main.py:264` be in scope? (6 declared params, 5 effective after `self`)
2. Should `_try_populate_window` (11 params, `qg-accepted`) be revisited, or is the BMAD consensus final?
3. Does the epic need a formal "closure" task (update `.epic-state.json`, mark ACs done) or is that handled separately?

---

## Sources

- `specs/_epics/tech-debt-cleanup/epic.md` — AC definitions for Spec 4
- `custom_components/ev_trip_planner/calculations/` — post-Spec3 decomposed modules
- `custom_components/ev_trip_planner/emhass/adapter.py` — `PerTripCacheParams` pattern example
- `custom_components/ev_trip_planner/trip/_soc_window.py` — `VentanaCargaParams` pattern example
- `custom_components/ev_trip_planner/trip/_types.py` — domain type definitions
- `.claude/skills/quality-gate/scripts/solid_metrics.py` — arity enforcement (max_arity=5)
- `.claude/skills/quality-gate/config/quality-gate.yaml` — AP08 max_parameters=5
- `pyproject.toml` — pyright basic mode, ruff config, pytest config
- [Python dataclasses docs](https://docs.python.org/3/library/dataclasses.html)
- [Real Python — Data Classes Guide](https://realpython.com/python-data-classes/)
- [Ruff rules reference](https://docs.astral.sh/ruff/rules/)

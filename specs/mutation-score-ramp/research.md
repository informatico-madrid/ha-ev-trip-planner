---
spec: mutation-score-ramp
phase: research
created: 2026-05-18T00:00:00Z
---

# Research: Mutation Score Ramp

## Executive Summary

The project already has a mature mutation testing infrastructure (mutmut 3.5.0, custom mutation analyzer, per-module thresholds in pyproject.toml, quality gate Layer 2 integration) with current overall mutation kill rate of **57.1%** (6605/11571 mutants killed). This is a strong foundation — the spec should proceed immediately. Verification corrections: (1) `make mutation` already uses `--max-children=4` (not `--until=100`), (2) the "3-5 hours" runtime claim was fundamentally wrong, (3) **actual measured runtime is ~9.7 minutes** with 0 timeouts, (4) module names changed (dead-code-elimination renamed `emhass_adapter`→`emhass`, `trip_manager`→`trip`, `vehicle_controller`→`vehicle`), (5) quality-gate config has stale references to merged `dashboard.*` directories.

## Current State Assessment

### Infrastructure (Already Built)

| Component | Status | Details |
|-----------|--------|---------|
| Tool | mutmut 3.5.0 | Installed in .venv |
| Config | `pyproject.toml [tool.mutmut]` | paths_to_mutate, runner=pytest, tests_dir, timeout=600s |
| Analyzer | mutation_analyzer.py (371 LOC) | Parses `mutmut results --all true`, per-module aggregation, gate mode |
| Quality Gate | Layer 2 (make layer2) | Runs mutation gate + weak test detector + diversity metric |
| Thresholds | 36 per-module targets in pyproject.toml | `[tool.quality-gate.mutation.modules.*]` |
| Makefile targets | `mutation`, `mutation-gate`, `layer2` | All wired up |
| Quality gate checkpoint | quality-gate-checkpoint.json | Last checkpoint: 2026-05-17, PASS=true |

### Baseline Mutation Score (from baseline/20260509-092405)

| Module | Killed | Survived | Total | Kill Rate | Threshold | Status |
|--------|--------|----------|-------|-----------|-----------|--------|
| **config_flow** | 74 | 165 | 239 | **31.0%** | 31% | in_progress |
| **dashboard** | 644 | 1171 | 1817 | **35.4%** | 35% | in_progress |
| **coordinator** | 54 | 89 | 143 | **37.8%** | 37% | in_progress |
| **panel** | 73 | 120 | 193 | **37.8%** | 37% | in_progress |
| **services** | 1018 | 1640 | 2658 | **38.3%** | 38% | in_progress |
| **sensor** | 253 | 401 | 654 | **38.7%** | 38% | in_progress |
| **trip_manager** | 1421 | 1615 | 3036 | **46.8%** | 46% | in_progress |
| **yaml_trip_storage** | 30 | 29 | 59 | **50.8%** | 50% | passing |
| **__init__** | 124 | 117 | 241 | **51.5%** | 51% | in_progress |
| **presence_monitor** | 378 | 348 | 726 | **52.1%** | 52% | passing |
| **emhass_adapter** | 1456 | 1293 | 2749 | **53.0%** | 53% | passing |
| **vehicle_controller** | 294 | 239 | 533 | **55.2%** | 55% | passing |
| **calculations** | 1237 | 489 | 1726 | **71.7%** | 71% | passing |
| **utils** | 288 | 34 | 322 | **89.4%** | 89% | passing |
| **diagnostics** | 69 | 5 | 74 | **93.2%** | 28% | passing |
| **definitions** | 18 | 0 | 18 | **100.0%** | 45% | passing |
| **OVERALL** | **7431** | **7757** | **15188** | **48.9%** | 48% | baseline |

### Key Observations

1. **No mutation test timeouts** -- all 15188 mutants were either killed or survived. No timeout=0 across any module.
2. **Dashboard module is stale** -- the `dashboard/` directory was merged into `panel.py` during refactoring, but the quality-gate config still references `dashboard.importer`, `dashboard.builder`, `dashboard.template_manager`. The `dashboard` entry in the killmap likely comes from old mutmut results that are no longer relevant.
3. **Services sub-modules not yet tracked** -- pyproject.toml defines 6 sub-module thresholds for services (handlers, _handler_factories, cleanup, dashboard_helpers, presence, _lookup) but the killmap aggregates them into a single `services` entry at 38.3%.
4. **Trip sub-modules split** -- pyproject.toml tracks trip.crud_mixin, trip.soc_mixin, trip.power_profile_mixin, trip.schedule_mixin, but the killmap shows `trip_manager` as a single 46.8% entry. The analyzer needs to reconcile these naming schemes.
5. **Emhass sub-modules tracked separately** in config (emhass.adapter, emhass.index_manager, etc.) at 53% threshold each, but killmap shows `emhass_adapter` as a single entry.

## Baseline Measurement

### Tools Available

| Tool | Version | Purpose |
|------|---------|---------|
| mutmut | 3.5.0 | Python mutation testing engine |
| custom mutation_analyzer.py | 371 LOC | Per-module threshold checking, JSON output |
| weak_test_detector.py | 11.8 KB | Detects weak test patterns |
| diversity_metric.py | 6.5 KB | Test diversity analysis |
| coverage (pytest-cov) | --cov | 99.55% code coverage |

### How to Establish New Baseline

```bash
# Full run (with --max-children=4):
make mutation

# Gate mode only (checks existing results against thresholds):
make mutation-gate

# Quick estimate of test coverage for mutants:
.venv/bin/mutmut tests-for-mutant <mutant_id>
```

### Known Issues (fixed during verification)

| Issue | Impact | Fix |
|-------|--------|-----|
| `make mutation` used `--until=100` (removed in mutmut 3.x) | Command always failed | Replaced with `--max-children=4` |
| `test_solid_metrics_isp.py` reads `.agents/...` path that doesn't exist | Stats collection fails (test assertions on file contents) | Excluded via `pytest_add_cli_args` |
| `test_vehicle_controller_event.py` uses `inspect.getsource()` to check source patterns | Fails because mutated code doesn't match original assertions | Excluded via `pytest_add_cli_args` |
| `.claude/skills/quality-gate/scripts/` not copied to `mutants/` dir | Tests referencing these files fail | Added to `also_copy` config |

### Actual Runtime (measured 2026-05-18)

**Full mutmut run on current codebase (11571 mutants, `--max-children=4`):**

| Measurement | Value | Notes |
|-------------|-------|-------|
| **Actual measured total** | **583 seconds (~9.7 min)** | Measured 2026-05-18 on current branch |
| Throughput (steady-state) | ~20 mutants/sec | Net rate across full run (11571 mutants in 583s) |
| Timeouts observed | **0** | All 11571 mutants either killed or survived; none hit 600s ceiling |
| Current kill rate | **57.1%** (6605/11571 killed) | Up from baseline 48.9% |

**The "3-5 hours" estimate was fundamentally wrong.** The 600s timeout per mutant is a MAXIMUM safety ceiling, not typical. Mutants are killed by the first failing test (typically milliseconds). Actual throughput is ~20 mutants/sec, giving **~10 minutes total** for full run.

**Implications:**
- ✅ Mutation testing is practical for **scheduled weekly runs** (~10 min fits CI budget)
- ✅ Can be part of **CI-on-schedule** (not blocking every PR)
- ⚠️ Too slow for **interactive development** (run locally only when targeting specific modules)
- ✅ **No architectural problem** — the infrastructure scales fine

**Note on `--max-children=4`**: This controls **parallelism** (4 mutants tested simultaneously), NOT which mutants are tested. ALL mutants are tested regardless of this setting.

**Module naming updates (from dead-code-elimination):**
- `emhass_adapter` → `emhass` 
- `trip_manager` → `trip`
- `vehicle_controller` → `vehicle`
- Dashboard merged into panel.py (but config still references stale `dashboard.*` thresholds)

### Runtime Optimization Options

1. **Increase parallel workers**: `--max-children=8` or more. Tradeoff: higher memory/CPU usage; estimated savings ~2-3 min.
2. **Reduce timeout**: 600s is generous. Could try 120-180s for most mutants (but needs validation).
3. **Selective mutation**: Use `paths_to_mutate` in `[tool.mutmut]` config to target specific modules during development (config option, NOT a CLI flag).
4. **Coverage-guided**: Use `mutmut tests-for-mutant <id>` to identify which tests kill a specific mutant.

## Code Coverage vs Mutation Score

**100% code coverage does NOT mean high mutation score.** This is the central tension. Here is why:

### Coverage-Mutation Gap Analysis

| Reason | Example | Impact |
|--------|---------|--------|
| **Branch coverage vs statement coverage** | `if x: return True; else: return False` is 100% covered but a `not x` mutation still passes | High in coordinator (37.8%) |
| **Tests don't assert mutation-triggered behavior** | Tests call functions but only check return value, not edge cases | High in config_flow (31%) |
| **Mocks replace real behavior** | HA fixtures mock `hass.data` but mutations to data access go unnoticed | High in services (38.3%) |
| **Assert-only-on-success** | Tests check happy path, mutations to error paths survive | High in panel (37.8%) |
| **Schema validation tests** | Mutating voluptuous schema defaults has no visible effect | High in config_flow (31%) |

### Specific Gap Examples

**config_flow (31%) -- 165 survived mutants:**
- ConfigFlow schema definitions use `voluptuous` which has built-in validation. Mutating default values or type coercions often has no visible test effect because tests don't assert on the generated schema structure.
- 696 LOC in main.py alone, mostly schema definitions.
- Tests likely exercise form submission but not schema mutation edge cases.

**coordinator (37.8%) -- 89 survived mutants:**
- Only 143 total mutants (small module, 199 LOC).
- DataUpdateCoordinator base class methods are hard to mutate-test because mutations to internal state often don't trigger test assertions.
- Async patterns: mutations to async methods may not be caught because test assertions check `asyncio.gather` results rather than intermediate state.

**panel (37.8%) -- 120 survived mutants:**
- 244 LOC, registers HA native panels.
- Mutations to URL paths, cache busting strings, or panel registration parameters would have no visible test effect without running HA.

**services (38.3%) -- 1640 survived mutants (largest survivor count):**
- 2658 total mutants across 5 files, 34 test files.
- Handler factories use closure patterns -- mutations to closure captures may not be testable from outside.
- Voluptuous schemas in service handlers -- many mutations to field types, defaults, required/optional flags have no effect on test assertions.

## Weak Spot Analysis

### Highest Risk Modules (by survivor count)

| Module | Survived | LOC | Survived/LOC | Risk |
|--------|----------|-----|-------------|------|
| services | 1640 | ~1600 | 1.02 | **CRITICAL** |
| trip_manager | 1615 | ~2500 | 0.65 | **HIGH** |
| emhass_adapter | 1293 | ~2200 | 0.59 | **HIGH** |
| dashboard | 1171 | N/A (merged) | -- | Stale |
| calculations | 489 | ~2400 | 0.20 | Medium |
| sensor | 401 | ~1000 | 0.40 | **HIGH** |
| presence_monitor | 348 | ~455 | 0.76 | **HIGH** |

### Module-by-Module Vulnerability Assessment

**config_flow (31%) -- Most urgent improvement target:**
- Survivors: 165, Low total (239) = high percentage of failures
- Root cause: HA ConfigFlow is boilerplate-heavy with schema definitions, not business logic
- Best strategy: Add assertions on generated form data, not just form submission
- Expected improvement: 31% -> 50%+ with targeted tests

**coordinator (37.8%) -- Moderate priority:**
- Survivors: 89, Small module (143 total)
- Root cause: async patterns + HA base class methods hard to mutate-test
- Best strategy: Test intermediate state mutations, not just final results

**panel (37.8%) -- Low ROI:**
- Survivors: 120, but panel registration is HA framework code
- Root cause: mutations to HA API calls (async_register_panel) have no test-visible effect
- Recommendation: Lower threshold or accept low score -- this is integration glue, not business logic

**services (38.3%) -- Highest absolute impact:**
- Survivors: 1640 across 5 sub-modules
- Root cause: closure-based handler factories, voluptuous schemas
- Best strategy: Add assertion tests that exercise handler return values for mutated inputs
- Expected improvement: 38% -> 60%+ with schema assertion tests

**sensor (38.7%) -- High priority:**
- Survivors: 401 across 654 mutants
- Root cause: HA sensor entity pattern (property-based values) mutations not caught
- Best strategy: Test sensor state transitions with mutated values

**dashboard (35.4%) -- STALE:**
- The `dashboard/` directory was merged into `panel.py`
- Killmap entry is from old mutmut results
- Recommendation: Remove dashboard thresholds, track panel separately

### Calculation Modules (Already Strong)

The calculations module at 71.7% is already excellent because:
- Pure functions with clear input/output contracts
- Math-heavy (SOC capping, deficit propagation, charging windows) -- mutations to arithmetic are immediately caught by assertions
- 27 test files for ~2400 LOC
- Best practice to emulate: assertion-heavy, pure-function testing

## Risk Assessment

### Feasibility of Target Mutation Scores

| Target | Feasibility | Time to Reach | Effort | Notes |
|--------|-------------|---------------|--------|-------|
| 55% (from 49%) | **High** | 1-2 sprints | Medium | Focus on top 5 modules by survivor count |
| 65% | **Medium** | 3-5 sprints | High | Requires architectural test improvements |
| 80% | **Low** | 6+ sprints | Very High | Diminishing returns, many survivors are unkillable |
| 90%+ | **Very Low** | Not recommended | Prohibitive | ~30% of survivors are typically unkillable by design |

### What's Typically Unkillable (and should be accepted)

| Pattern | Why Unkillable | Example |
|---------|----------------|---------|
| HA framework API calls | No test can see framework-internal state | `panel_custom.async_register_panel()` |
| HA config entry defaults | voluptuous schemas pass validation regardless of defaults | `vol.Required("x", default=5)` |
| Logging calls | mutations to log level/message have no test-visible effect | `_LOGGER.debug("...")` |
| Dataclass frozen() | mutations to frozen=True have runtime effect but not test-visible | `@dataclass(frozen=True)` |
| HA entity properties | computed properties return cached values | `@property def state(self): return self._state` |

### Cost-Benefit Analysis

| Score Range | Expected Bug Catch Rate | Additional Tests Needed | ROI |
|-------------|------------------------|------------------------|-----|
| 49% -> 55% | +15-20% | ~200 targeted tests | **HIGH** |
| 55% -> 65% | +10-15% | ~300 targeted tests | MEDIUM |
| 65% -> 80% | +5-10% | ~500 targeted tests | LOW |
| 80% -> 90% | +2-5% | ~400 targeted tests | VERY LOW |

## Recommendations

1. **Proceed with the spec.** The infrastructure is already mature (mutmut + analyzer + quality gate + per-module thresholds). The spec should focus on incremental improvement strategy.

2. **Fix stale configuration first:**
   - Remove dashboard thresholds (directory merged into panel.py)
   - Consolidate services sub-module tracking (analyzer groups them into single `services` entry)
   - Clarify trip_manager vs trip sub-module naming

3. **Set realistic targets per module:**
   - config_flow: 31% -> 50% (schemas + form validation tests)
   - coordinator: 37.8% -> 55% (async state tests)
   - services: 38.3% -> 55% (schema assertion tests)
   - sensor: 38.7% -> 55% (state transition tests)
   - panel: accept 37.8% (HA framework glue, low ROI)
   - calculations: maintain 71.7% (already excellent)

4. **Runtime optimization:** Use `--max-children=N` for parallel workers (no `--parallel` flag in 3.5.0). Current runtime is ~10 minutes with 4 workers; can be optimized with higher parallelism or reduced timeout (600s → 120-180s).

5. **CI strategy:** Full `mutmut run` takes ~10 minutes, acceptable for scheduled weekly runs. For CI-on-each-PR, only run `mutation-gate` against cached results or trigger full run after significant code changes.

6. **Module-per-sprint approach:** The existing `modules_per_sprint = 2` and `increment_step = 0.01` in pyproject.toml is a good framework. Use it.

7. **Consider mutmut alternatives for fast feedback:**
   - `mutmut tests-for-mutant <id>` to identify which test kills a specific mutant
   - `mutmut run --paths-to-mutate custom_components/ev_trip_planner/<changed_files>` for targeted runs
   - Custom script to run only mutants in changed modules

## Open Questions

1. Are the dashboard submodule thresholds (`dashboard.importer`, `dashboard.builder`, `dashboard.template_manager`) from an old directory structure that no longer exists? If so, should they be removed?
2. The services sub-modules in pyproject.toml (handlers, _handler_factories, cleanup, etc.) don't map cleanly to the single `services` entry in the killmap. Should the analyzer be updated to parse submodule boundaries, or should thresholds be at the services level only?
3. Should we add `no_tests` as a separate tracking category? Currently it's always 0 in the baseline.
4. The `quality-gate.mutation.modules` config uses dotted paths like `trip.crud_mixin` but mutmut output uses `trip_manager`. Is there a mapping layer, or is the analyzer supposed to handle this?
5. What is the rationale for `definitions` having a 100% kill rate but only a 0.45 threshold? Is the threshold intentionally loose because the module is tiny (18 mutants)?

## Sources

### Internal
- `_bmad-output/quality-gate/baseline/20260509-092405/mutation-killmap.txt` -- full mutation kill map with per-module stats
- `_bmad-output/quality-gate/quality-gate-latest.json` -- latest quality gate checkpoint
- `pyproject.toml` -- mutmut config (`[tool.mutmut]`) and quality gate thresholds (`[tool.quality-gate.mutation]`)
- `.claude/skills/quality-gate/scripts/mutation_analyzer.py` -- 371 LOC mutation analysis script
- `Makefile` -- mutation targets (`mutation`, `mutation-gate`, `layer2`)
- `custom_components/ev_trip_planner/` -- 56 source files, 12688 LOC total
- `tests/` -- 129 test files, 37217 LOC total
- `specs/mutation-score-ramp/.ralph-state.json` -- spec state (phase: research)

### Memory System
- Python quality gate orchestration patterns (Makefile layers, mutmut configuration)
- Spec 2 test reorg background (test directory structure, mutmut config implications)

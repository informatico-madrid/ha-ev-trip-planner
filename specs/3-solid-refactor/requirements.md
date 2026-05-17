---
spec: 3-solid-refactor
phase: requirements
created: 2026-05-10
updated: 2026-05-10
epic: tech-debt-cleanup
branch: spec/3-solid-refactor (from epic/tech-debt-cleanup)
pr_target: epic/tech-debt-cleanup
depends_on: [2-test-reorg (PR #46)]
---

# Requirements: 3-solid-refactor

## Executive Summary

This spec decomposes 9 god modules in the entire `custom_components/ev_trip_planner/` package into focused, single-responsibility components. The **primary goal is SOLID compliance and code quality**, measured by objective metrics (LCOM4, verb diversity, ISP unused-method ratio, dependency direction, cyclomatic complexity, nesting depth). LOC ≤ 500 per file is a **screening metric, not the goal** — a well-decomposed 480-LOC file can still violate SRP, and a 510-LOC file may be acceptable if it represents a single cohesive responsibility.

**Scope (WHAT must change)**:
- 9 god modules → focused components, each with cohesive responsibility (HOW: see design.md). Initially 6 modules were in scope (`emhass_adapter.py`, `trip_manager.py`, `services.py`, `dashboard.py`, `vehicle_controller.py`, `calculations.py`); the user expanded scope to also include `sensor.py` (1,041 LOC), `config_flow.py` (1,038 LOC), and `presence_monitor.py` (806 LOC). The full package — not a 6-module subset — must reach Bar A.
- Public API signatures (constructor + imported names) preserved (HOW: re-export mechanism in design.md)
- Test imports continue to resolve (HOW: migration phases in design.md)
- 3 known DRY violations consolidated into single canonical locations (Step 0.5 pre-flight, BEFORE any decomposition begins)
- 1 known KISS violation (`register_services()` 657 LOC) decomposed
- 2 known bugs fixed during the calculations decomposition: `[BUG-001]` `ventana_horas` AND `[BUG-002]` redundant `+ return_buffer_hours` on `previous_arrival`
- Import cycle policy enforced via `lint-imports` contracts (HOW: contract details in design.md)
- 7 lazy `from .sensor import` escape hatches eliminated from trip-management code (HOW: replacement mechanism in design.md)
- Pyright `typeCheckingMode = "basic"` 16 pre-existing errors in `sensor.py` are FIXED in this spec (no longer deferred to Spec 7) because Bar A NFR-7.A.5 requires zero pyright errors across the entire package.

**Success criteria** — at the END of this spec, the codebase must be at **MAXIMUM SOLID compliance**, not merely "improved." There are two distinct quality bars:

**Bar A — Final state of the codebase (end of spec, blocks merge to epic):**
- **SOLID**: 5/5 letters PASS for **every class in `custom_components/ev_trip_planner/`** (no exception for `config_flow`, `sensor`, `presence_monitor`). LCOM4 ≤ 2 AND verb diversity ≤ 5 (with documented per-class allowlists where SRP is genuinely cohesive but verbose, e.g., trip CRUD; HA `Entity` ABC override methods); ISP unused-method ratio ≤ 0.5 for every intra-package ABC/Protocol; public methods ≤ 20 per class; type-hint coverage ≥ 90%; zero inline concrete-class instantiations in `__init__` of cross-package collaborators (intra-package facade-owns-its-parts is whitelisted).
- **Architecture**: Zero module-load circular cycles (`lint-imports` green); zero lazy-import escape hatches in trip-management code; dependency direction enforced by 7 explicit `lint-imports` contracts (e.g., `dashboard` does not import `trip`).
- **DRY**: 3 known duplications collapsed to one canonical location (consolidated in Step 0.5 pre-flight); sliding-window similarity = 0 duplications ≥ 5 consecutive lines across files; error message strings consolidated in `const.py`.
- **KISS**: ALL functions cyclomatic complexity ≤ 10 AND nesting depth ≤ 4 AND length ≤ 100 LOC. The 657-LOC `register_services()` is decomposed.
- **Bug fixes**: `[BUG-001]` `ventana_horas` AND `[BUG-002]` redundant `+ return_buffer_hours` fixed; regression tests assert the corrected (not buggy) values; property-based invariant test covers the bug class.
- **No regression**: Every source file ≤ 500 LOC, 100% test coverage maintained, all 1,820+ tests pass, `make e2e` (30 tests) passes, `make e2e-soc` (10 tests) passes, `pyright` zero errors (including the 16 pre-existing `sensor.py` errors), public API imports unchanged for all callers.

**Bar B — Per-checkpoint progress (every commit must improve, never regress):**
- After each god-module decomposition commit, the metrics for the affected module(s) must show measurable improvement vs baseline (or maintain if already at ceiling). This is a **forward-progress gate**, not a final-acceptance gate.
- Quality-gate diff vs baseline at each checkpoint:
  - Already-passing metrics: maintain (no regression).
  - Currently-failing metrics: must show measurable improvement at the commit that addresses them.
  - Metrics at theoretical ceiling (LCOM4 = 1, coverage = 100%, type hints = 100%): exempt from "must improve" — must merely not regress.
  - Mutation score: Spec 5 scope; transient path-change artifacts during this spec are acceptable.

**Why two bars?** Bar A is the final acceptance criterion — when the spec is done, SOLID is maximum. Bar B is the per-step progress check — every commit moves toward Bar A and never regresses. Bar B's "≥ 10%" / "≥ 20%" thresholds (in NFR-7) are floors for mid-spec checkpoints to detect lazy decompositions; Bar A's "5/5 letters PASS" is the final state.

## Glossary

| Term | Definition |
|------|-----------|
| **God Module** | A source file > 500 LOC, OR a class with > 20 public methods, OR a class with verb-diversity > 5, OR a class with LCOM4 > 2 — i.e. a module/class that violates one or more SOLID screening metrics. |
| **WHAT vs HOW** | WHAT = problem statement, observable outcome, measurable success criterion (this file). HOW = design choice, structural decision, named pattern, file/class names, LOC distribution (design.md). |
| **SOLID Compliance** | Measurable outcome — not a named pattern. Verified via `solid_metrics.py` (S, O, L, I, D letters), `principles_checker.py` (DRY, KISS, YAGNI, LoD, CoI), and `antipattern_checker.py` (Tier A 25 patterns). |
| **LCOM4** | Lack of Cohesion of Methods (4th formulation). Counts connected components in the method-attribute graph. LCOM4 = 1 means the class is fully cohesive (SRP-compliant); LCOM4 ≥ 2 means the class can be split into N independent classes. |
| **Verb Diversity** | Count of unique action verbs in method names (e.g., `save`, `calc`, `notify`). High diversity (> 5) indicates the class does many unrelated things — an SRP violation surfaced via naming. Per-class allowlists are permitted for cohesive-but-verbose responsibilities (documented in `solid_metrics.py` configuration); HA `Entity` ABC required overrides (`name`, `unique_id`, `state`, `available`, etc.) are NOT counted toward verb-diversity. |
| **ISP Unused-Method Ratio** | For each intra-package ABC/Protocol, the ratio of abstract methods that are stubbed (`raise NotImplementedError` / `pass` / `...`) in concrete implementations. Ratio > 0.5 means the interface is too fat — implementers don't need most of it (ISP violation). HA framework ABCs (`Entity`, `RestoreEntity`, `Platform`, `ConfigFlow`, `OptionsFlow`) are EXCLUDED from this check — they have 100+ methods that subclasses legitimately stub. |
| **Dependency Direction** | High-level concerns (e.g., business logic) must not import from low-level concerns in a way that creates cycles. Specifically: `dashboard` must not import `trip` (different concerns); `trip` must not import `sensor` at module-load time. |
| **DRY Violation** | The same logic exists in ≥ 2 places. Detected via: (a) function-name duplication across modules, (b) sliding-window code similarity ≥ 5 consecutive lines across files, (c) divergent implementations of the same concept (e.g., two `validate_hora` with different return types). |
| **KISS Violation** | Cyclomatic complexity > 10, nesting depth > 4, or cognitive complexity high. Surfaces as "I have to read this 3 times to understand it." |
| **Quality-Gate Baseline** | The full `make quality-gate` run captured before any refactoring begins. Documents all 8 metric categories. Used as the before-state for measuring improvement. |
| **`[BUG-001]` `ventana_horas` Bug** | The charging window for a trip is the time available **before that trip departs**, used to charge the car. Located in `calculations.py:698` inside `calculate_multi_trip_charging_windows`. Current code computes `delta = trip_arrival - window_start`, where `trip_arrival = trip_departure_time + duration_hours` (i.e., when the car would arrive at the destination, **after** the trip starts). The window's `fin_ventana` field correctly stores `trip_departure_time` (line 726), so `ventana_horas` is inconsistent with `fin_ventana - inicio_ventana`: it is inflated by `duration_hours` (e.g., +6h) because it counts time during which the car is already away, not available for charging. The fix replaces line 698's `trip_arrival_aware - window_start_aware` with `_ensure_aware(trip_departure_time) - window_start_aware`, making `ventana_horas` consistent with `fin_ventana - inicio_ventana`. |
| **`[BUG-002]` redundant `+ return_buffer_hours` on `previous_arrival`** | Located in `calculations.py:733-735` inside `calculate_multi_trip_charging_windows`. The user clarified the domain model: `duration_hours` should not exist as a separate constant from `return_buffer_hours` — there is **ONE constant** added to a trip's `departure_time` to estimate when the car returns home. The current code computes `previous_arrival = trip_arrival + timedelta(hours=return_buffer_hours)`, which adds `return_buffer_hours` (4h) ON TOP of the `duration_hours` (6h) already baked into `trip_arrival`. This double-counts the away-time. The fix: `previous_arrival = _ensure_aware(trip_arrival)` (NO additional buffer). The `return_buffer_hours` parameter is **kept** in the function signature for API compatibility (callers in `emhass_adapter.py:1062` pass it) but becomes UNUSED inside the function body (a `# Deprecated: kept for API compat, has no effect after [BUG-002] fix` comment is added; full removal is deferred to Spec 4). The new invariant: `previous_arrival == previous_trip.departure_time + duration_hours`. |
| **`[BUG-001]` and `[BUG-002]` are co-fixed** | Both bugs are co-located in the same commit during the calculations decomposition. The hypothesis property-based test asserts BOTH invariants: `ventana_horas == (fin_ventana - inicio_ventana) / 3600` AND `previous_window_start == previous_trip.departure_time + duration_hours`. |

## User Stories

### US-1: Maintainable Modules (developer)

**As a** developer reading or modifying business logic,
**I want** each god module decomposed so that no source file requires reading > 500 LOC of unrelated code to understand a single concern,
**so that** I can make focused changes without holistic re-comprehension of 2,000+ line files.

**Acceptance Criteria:**
- AC-1.1: No source module in `custom_components/ev_trip_planner/` exceeds 500 LOC after decomposition (`wc -l` ≤ 500 for every `.py` file). Old monolithic files removed.
- AC-1.2: Nine god modules decomposed: `emhass_adapter.py`, `trip_manager.py`, `services.py`, `dashboard.py`, `vehicle_controller.py`, `calculations.py`, `sensor.py`, `config_flow.py`, `presence_monitor.py`.
- AC-1.3: Every function in the resulting code has cyclomatic complexity ≤ 10 (`radon cc` passes). C-grade (cc 11-20) is accepted when the function's nature naturally requires that complexity (e.g., multi-branch pattern matching, enum dispatch, or domain logic with multiple valid input categories). Such functions MUST have a `# CC-N-ACCEPTED:` comment explaining why the complexity cannot be reduced further without compromising clarity. D-grade (cc > 20) always requires extraction.
- AC-1.4: Maximum nesting depth ≤ 4 levels in all functions (`radon nc` or equivalent passes).
- AC-1.5: The 657-LOC `register_services()` function in `services.py` is decomposed into smaller, comprehensible units (no single function > 100 LOC, no nested-handler block > 50 LOC). Decomposition mechanism is a design decision (design.md).
- AC-1.6: The 266-LOC `_populate_per_trip_cache_entry` in `emhass_adapter.py` is relocated/decomposed so the host module is ≤ 500 LOC.

### US-2: Stable Public API (consumer of `custom_components.ev_trip_planner`)

**As a** caller of the integration's public API (HA core, tests, downstream code),
**I want** all public imports to resolve identically before and after decomposition,
**so that** no caller code requires modification.

**Acceptance Criteria:**
- AC-2.1: `EMHASSAdapter` constructor signature is unchanged: `__init__(self, hass, entry)`. Verified by `pyright` (zero new errors at call sites).
- AC-2.2: `TripManager` constructor signature is unchanged: `__init__(self, hass, vehicle_id, entry_id, presence_config, storage, emhass_adapter=None)`. Verified by `pyright`.
- AC-2.3: `VehicleController` constructor signature unchanged. Verified by `pyright`.
- AC-2.4: All public names previously importable from each god module remain importable from a stable location. The complete preserved-name contract is:
  - From `emhass_adapter`: `EMHASSAdapter`
  - From `trip_manager`: `TripManager`
  - From `services`: 10 public functions — `async_cleanup_orphaned_emhass_sensors`, `async_cleanup_stale_storage`, `async_import_dashboard_for_entry`, `async_register_panel_for_entry`, `async_register_static_paths`, `async_remove_entry_cleanup`, `async_unload_entry_cleanup`, `build_presence_config`, `create_dashboard_input_helpers`, `register_services`
  - From `dashboard`: `import_dashboard`, `is_lovelace_available`, `DashboardImportResult`, plus 4 exception classes (`DashboardError`, `DashboardNotFoundError`, `DashboardValidationError`, `DashboardStorageError`)
  - From `vehicle_controller`: `VehicleController`, `VehicleControlStrategy`, `create_control_strategy`
  - From `calculations`: 20 names — 17 functions (all `calculate_*` and `generate_*`) + 2 classes (`BatteryCapacity`, `ChargingDecision`) + 1 constant (`DEFAULT_T_BASE`)
  - From `sensor`: HA platform contract — `async_setup_entry` + Entity classes (`TripPlannerSensor`, `EmhassDeferrableLoadSensor`, `TripSensor`, `TripEmhassSensor`)
  - From `config_flow`: `EVTripPlannerFlowHandler`, `EVTripPlannerOptionsFlowHandler`, `async_get_options_flow`
  - From `presence_monitor`: `PresenceMonitor`
- AC-2.5: Every existing import site in source (`__init__.py`, `coordinator.py`, `services.py`, `config_flow.py`, `presence_monitor.py`, `vehicle_controller.py`) continues to resolve without modification. Mechanism (re-exports, package imports) is a design decision (design.md).
- AC-2.6: Public API surface is explicitly declared in code so tooling can detect accidental breakage. Mechanism (`__all__`, etc.) is a design decision (design.md).
- AC-2.7: `deptry` runs after all decomposition steps with zero broken-import findings (`make unused-deps` green).

### US-3: Test Suite Resilience (test engineer)

**As a** test engineer,
**I want** the full test suite to pass after every package decomposition step so that regressions are caught immediately at the granularity of one module per commit,
**so that** broken commits never accumulate and bisecting failures stays trivial.

**Acceptance Criteria:**
- AC-3.1: `make test` passes with ≥ 1,820 tests (post-Spec 1/2 baseline) after each package decomposition commit.
- AC-3.2: `make e2e` passes (30 tests) after each package decomposition commit.
- AC-3.3: `make e2e-soc` passes (10 tests) after each package decomposition commit.
- AC-3.4: 100% test coverage maintained (no regression from 100% post-Spec 2). `make test-cover` passes with `--cov-fail-under=100`.
- AC-3.5: After each decomposition commit, every test file's imports resolve correctly. Test imports do not need to change at the same commit as the source decomposition (a transitional bridge is acceptable; final cleanup may follow). Migration mechanism is a design decision (design.md).

### US-4: Measurable SOLID Compliance (architect)

**As an** architect,
**I want** SOLID principles enforced via objective, machine-checkable metrics, not subjective code review,
**so that** architectural quality is reproducible and CI-gateable, not dependent on a reviewer's opinion.

**Acceptance Criteria:**
- AC-4.1: **S (Single Responsibility)**: LCOM4 ≤ 2 for every class (ideal: 1; acceptable: 2 with shared state). Verb diversity ≤ 5 unique action verbs per class. Both checked by `solid_metrics.py`.
- AC-4.2: **O (Open/Closed)**: Where strategy/extension points exist (e.g., vehicle control strategies), they are expressed as ABCs/Protocols, not if/elif chains. Verified by code review against `solid_metrics.py` ABC/Protocol detection.
- AC-4.3: **L (Liskov Substitution)**: All ABC/Protocol implementations honor the contract (no surprise exceptions on otherwise-valid input). Verified by `pyright` strict-method-signature checks plus existing test coverage.
- AC-4.4: **I (Interface Segregation)**: For every intra-package ABC/Protocol, the ratio of abstract methods that concrete implementations stub out (`raise NotImplementedError`, `pass`, `...`) is ≤ 0.5. HA framework ABCs (`Entity`, `RestoreEntity`, `Platform`, `ConfigFlow`, `OptionsFlow`) are excluded. Checked by `solid_metrics.py` (the `max_unused_methods_ratio` check is implemented as part of this spec — see AC-4.7).
- AC-4.5: **D (Dependency Inversion)**: Zero module-load circular cycles — `lint-imports` runs clean with explicit contracts. Zero lazy-import escape hatches in trip-management code. Zero inline instantiations of concrete classes inside `__init__` bodies (collaborators are dependency-injected). Checked by `solid_metrics.py` and `lint-imports`.
- AC-4.6: Type-hint coverage ≥ 90% across the decomposed modules (`solid_metrics.py` type-hint check passes).
- AC-4.7: The previously-stubbed ISP check in `solid_metrics.py` (`max_unused_methods_ratio`) is implemented as part of this spec. Specification: scoped to ABCs/Protocols defined within `custom_components.ev_trip_planner` only (HA framework ABCs excluded); stub-detection counts method bodies that are exactly `pass`, `...`, or `raise NotImplementedError(...)`; threshold is per-ABC unused-methods-ratio > 0.5 fails. Implementation cost: ~60-100 LOC (AST walk + intra-package class filter + stub detection).
- AC-4.8: All classes have ≤ 20 public methods (existing ARN-002 carried forward; superseded by LCOM4/verb-diversity as primary SRP indicators). HA `Entity` ABC required overrides do not count toward this ceiling.
- AC-4.9: Method arity ≤ 5 parameters per function (existing ARN-003 carried forward).

### US-5: DRY Consolidation (developer)

**As a** developer,
**I want** known code duplications collapsed to a single canonical location,
**so that** behavior is unambiguous and bug fixes propagate automatically.

**Acceptance Criteria:**
- AC-5.1: `validate_hora` exists in exactly one canonical location (currently `utils.py` as `pure_validate_hora`). All other copies removed.
- AC-5.2: `is_trip_today` exists in exactly one canonical location (currently `utils.py` as `pure_is_trip_today`). All other copies removed.
- AC-5.3: `calculate_day_index` exists in exactly one canonical location. The canonical location and any duplicate-removal sequencing is a design decision (design.md), but the end state is one definition.
- AC-5.4: Sliding-window code similarity = 0 duplications ≥ 5 consecutive lines across files (`jscpd` or `simian` check passes with 0 violations).
- AC-5.5: Error message strings used by HA service handlers are consolidated in `const.py` — no duplicate error message literals across service handlers.
- AC-5.6: DRY consolidation happens in **Step 0.5** of the implementation sequence — BEFORE any package decomposition begins (see design.md §6.2). After Step 0.5, Bar B reports DRY = 0 violations; subsequent decompositions only preserve DRY = 0.

### US-6: KISS Reduction (developer)

**As a** developer,
**I want** complex functions broken into immediately comprehensible units,
**so that** each function fits in working memory on first reading.

**Acceptance Criteria:**
- AC-6.1: `register_services()` cyclomatic complexity ≤ 10 after decomposition (current body length: 657 LOC, line 31 → next top-level def at line 688).
- AC-6.2: `_populate_per_trip_cache_entry` (266 LOC) decomposed so the function and its host module each meet KISS thresholds (cc ≤ 10, nesting ≤ 4) and the host module meets US-1 LOC screen.
- AC-6.3: Maximum nesting depth ≤ 4 levels in all functions across the decomposed code (covered by AC-1.4).
- AC-6.4: `calculate_multi_trip_charging_windows` (currently 118 LOC, deep nesting) cyclomatic complexity reduced to ≤ 10. Decomposition mechanism is a design decision (design.md).

### US-7: Dashboard Path Pre-Condition (HA integration)

**As an** HA integration that loads dashboard templates from disk,
**I want** the `__file__` path resolution remain correct after dashboard decomposition,
**so that** dashboard templates load without silent failures in production.

**Acceptance Criteria:**
- AC-7.1: After dashboard decomposition, dashboard template files load successfully at runtime (verified by `make e2e-soc` dashboard import scenarios).
- AC-7.2: Template path resolution does not depend on the source file's package depth (no breakage if a future refactor moves source files between packages).
- AC-7.3: All 11 existing template files (YAML/JS) remain accessible via the new path resolution mechanism.

> **Why this is a requirement, not a design decision**: when `dashboard.py` becomes `dashboard/__init__.py`, `os.path.dirname(__file__)` gains an extra `/dashboard` segment, breaking template paths silently. The fix is a design-phase concern (design.md specifies the mechanism), but the **outcome** (templates load correctly, path is robust to package-depth changes) is a requirement.

### US-8: Eliminate Lazy Import Escape Hatches (developer)

**As a** developer reading trip-management code,
**I want** all `from .sensor import ...` calls inside method bodies of trip-management code removed,
**so that** the trip-management codebase contains no architectural-debt escape hatches and the dependency direction is statically declarable.

**Acceptance Criteria:**
- AC-8.1: All 7 lazy `from .sensor import ...` calls currently in `trip_manager.py` are removed (grep returns 0 matches in trip-management code after decomposition).
- AC-8.2: The previous `# Local import to avoid circular dependency` comments are removed along with the lazy imports.
- AC-8.3: Trip-management code does not import `sensor` at module load time either (no static `from .sensor import` at top level). The mechanism for sensor interaction (callback registry, event bus, DI handle, etc.) is a design decision (design.md).
- AC-8.4: `lint-imports` contract forbidding `trip → sensor` module-load dependency is configured and passing (covered by AC-4.5 / NFR-1.4).
- AC-8.5: Missing-callback handling (e.g., sensor platform not yet loaded during early `setup_entry`) logs a WARNING and no-ops (per design.md §4.2). Silent no-op is rejected because it hides observability of unregistered callbacks; CRITICAL is rejected as too noisy for an expected early-setup state.
- **Risk Note**: US-8 touches `sensor.py` (not a god module pre-scope-expansion; now in scope per US-13). If implementation discovers irreducible runtime ordering (e.g., HA platform registration timing), this US may be deferred to Spec 4 with `# TODO(spec-4)` markers and a `lint-imports` contract documenting the forbidden dependency. The decision to defer is made during the design phase, not during implementation.

### US-9: Per-Decomposition Architectural Validation (reviewer)

**As a** reviewer,
**I want** each god-module decomposition validated semantically (not just by tests passing),
**so that** SOLID violations and hidden coupling are caught before merge.

**Acceptance Criteria:**
- AC-9.1: Each of the 9 god-module decompositions passes a Tier B BMAD Consensus Party review before that decomposition is merged. The Consensus Party includes (at minimum): an architect role validating SRP/cohesion, a test-architect role validating public API contract preservation, and an adversarial role hunting silent failures and hidden coupling.
- AC-9.2: Consensus Party result (PASS/FAIL + issues) is documented in `chat.md` for each decomposition.
- AC-9.3: Tier A deterministic checks (`make layer3a`) pass before Tier B is invoked.
- AC-9.4: A Consensus Party FAIL blocks further progress on that decomposition until resolved.
- AC-9.5: **Sequencing rule**: within a single Consensus Party, agents run sequentially (Winston → Murat → Adversarial). Across packages, Consensus Parties are sequential — each must verify committed state of the previous package before the next decomposition begins.

### US-10: `[BUG-001]` `ventana_horas` Bug Fix (user)

**As an** end user planning EV charging schedules,
**I want** the `ventana_horas` charging window for each trip to count only the time the car is **at home and available to charge**, not the time the car is away on the trip,
**so that** my charging schedule reflects real charging availability instead of an inflated window that includes time during which the car is physically not present.

**Correct semantics (the fix targets this):**
- **First trip's charging window**: from `max(now, hora_regreso)` (or `now` if no `hora_regreso`) until `trip_1.departure_time`. The window ends when the trip starts (the car leaves).
- **Subsequent trips' charging windows (trip N for N ≥ 2)** *(after [BUG-002] fix)*: from `previous_trip.departure_time + duration_hours` (i.e., the moment the car returns home from the previous trip) until `current_trip.departure_time`. NO `+ return_buffer_hours` is added.
- **Invariant**: `ventana_horas == (fin_ventana - inicio_ventana).total_seconds() / 3600`. Currently violated because `fin_ventana = trip_departure_time` (correct) but `ventana_horas` is computed using `trip_arrival = trip_departure_time + duration_hours` (incorrect — adds the away-time).

**Acceptance Criteria:**
- AC-10.1: After the calculations decomposition, `calculate_multi_trip_charging_windows` computes `ventana_horas` as `(trip_departure_time - window_start) / 3600` (not `(trip_arrival - window_start) / 3600`). Equivalently: the invariant `ventana_horas == (fin_ventana - inicio_ventana) / 3600` holds for every trip in the result list.
- AC-10.2: `previous_arrival` (the start of the next trip's charging window) is updated by [BUG-002] (US-13): `previous_arrival = _ensure_aware(trip_arrival)` (no `+ return_buffer_hours`). The new invariant is `previous_arrival == previous_trip.departure_time + duration_hours`.
- AC-10.3: Test `tests/unit/test_single_trip_hora_regreso_past.py` assertions are updated to match the corrected values. The current test file has **3** hardcoded value assertions (line 57: 102.0, line 97: 102.0, line 128: 98.0) — all three must be updated. Recomputed values: line 57 → 96.0, line 97 → 96.0, line 128 → 92.0. Inline rationale comments must also change ("should be ~102h" → "should be ~96h"; "should be 98h" → "should be 92h").
- AC-10.4: The bug fix is co-located in the same commit as the calculations decomposition (not deferred to a later commit). [BUG-001] AND [BUG-002] are co-fixed in this same commit.
- AC-10.5: A new property-based regression test asserts BOTH invariants for arbitrary inputs:
  1. `ventana_horas == (fin_ventana - inicio_ventana).total_seconds() / 3600` for every trip in the result list.
  2. `previous_window_start == previous_trip.departure_time + duration_hours` (NOT `+ return_buffer_hours`) for every transition between consecutive trips.

  Spans single-trip, multi-trip, with/without `hora_regreso`, past/future trips. Makes the bug class (not just one fixture) reportable by tests.
- AC-10.6: The `return_buffer_hours` parameter remains in `calculate_multi_trip_charging_windows` for API compatibility (the caller `emhass_adapter.py:1062` passes it). The parameter becomes UNUSED inside the function body after [BUG-002] fix. A `# Deprecated: kept for API compat, has no effect after [BUG-002] fix` comment marks the unused parameter; full removal is deferred to Spec 4.

### US-11: Pre-Decomposition Module Understanding (developer)

**As a** developer about to decompose a module,
**I want** to first understand its purpose, data flow, and known edge cases,
**so that** latent bugs are detected and fixed in-flight rather than carried forward.

**Acceptance Criteria:**
- AC-11.1: Before each decomposition, a brief written analysis is captured (in `chat.md` or task notes): what the module does, how data flows through it, key edge cases, known latent bugs.
- AC-11.2: The `[BUG-001]` and `[BUG-002]` `ventana_horas` / `previous_arrival` bugs serve as the documented exemplars — co-fixed in the calculations decomposition (US-10, US-13).
- AC-11.3: Bugs found during decomposition are fixed co-located with the corresponding code change (not bulked into a separate "bug fix" commit at the end).
- AC-11.4: After each decomposition, the bug-count for that module is recorded in `chat.md` with `[BUG-XXX]` tags.

### US-12: Parallel Bug-Fix Loop (reviewer)

**As a** reviewer,
**I want** in-flight bug fixes captured in a separate execution loop alongside the main decomposition tasks,
**so that** bug discovery does not block forward decomposition progress and bugs are tracked uniformly.

**Acceptance Criteria:**
- AC-12.1: When a bug is found during a decomposition, the executor creates a separate `[BUG-XXX]` task executed in a dedicated loop (parallel to main decomposition).
- AC-12.2: The bug-fix loop: (a) identifies root cause and data flow, (b) implements fix, (c) verifies with existing tests + adds a regression test if none exists, (d) commits with `[BUG-XXX]` tag.
- AC-12.3: After the bug-fix loop completes, execution returns to the main decomposition task.
- AC-12.4: A running bug-fix table is maintained in `chat.md` with 6 columns: `BUG-ID`, `Source` (file:lines), `Description` (one sentence), `Root Cause` (one sentence), `Status` (Fixed / Pending), `Regression` (test path or N/A).
- AC-12.5: If a bug-fix loop reveals a design flaw (not a bug), it is escalated to a `[DESIGN-XXX]` task for the main executor to resolve.

### US-13: `[BUG-002]` Redundant `+ return_buffer_hours` Bug Fix (user)

**As an** end user planning EV charging schedules across multiple trips,
**I want** the start of trip N's charging window to be exactly when the car returns home from trip N-1 (`departure(N-1) + duration_hours`), not that moment PLUS an extra `return_buffer_hours`,
**so that** subsequent-trip charging windows are not artificially shifted by the buffer constant.

**Domain rule (per user clarification):**
> "duration_hours no debería existir eso no está en los viajes. Lo que hay es UNA constante que se agrega a la hora de salida del viaje para estimar cuándo vuelve. previous_arrival es previous_departure + constante de clase (será return_buffer_hours o algo así)."
>
> Translation: there should be ONE constant added to a trip's `departure_time` to estimate when the car returns home. The current code has TWO separate constants (`DURACION_VIAJE_HORAS = 6.0` aliased as `duration_hours`, and `RETURN_BUFFER_HOURS = 4.0` aliased as `return_buffer_hours`), and `previous_arrival = trip_arrival + return_buffer_hours` redundantly adds both. The correct semantics: `previous_arrival = trip_departure_time + duration_hours` (= `trip_arrival`); no additional buffer.

**Acceptance Criteria:**
- AC-13.1: `calculations.py:733-735` is changed from `previous_arrival = _ensure_aware(trip_arrival) + timedelta(hours=return_buffer_hours)` to `previous_arrival = _ensure_aware(trip_arrival)`.
- AC-13.2: The `return_buffer_hours` parameter remains in the function signature for API compatibility (callers still pass it). The parameter becomes UNUSED inside the function body. A `# Deprecated: kept for API compat, has no effect after [BUG-002] fix` comment marks the unused parameter. Full parameter removal is deferred to Spec 4.
- AC-13.3: The fix is co-located with `[BUG-001]` in the SAME commit (during the calculations decomposition). Both bugs share the same regression test infrastructure.
- AC-13.4: The hypothesis property-based regression test (US-10 AC-10.5) asserts the new invariant: `previous_window_start == previous_trip.departure_time + duration_hours` for every transition between consecutive trips, across a range of inputs.
- AC-13.5: The user clarification is recorded in the bug-tracking table (NFR-7.A entry for `[BUG-002]`) including the original Spanish quote and English translation.

## Functional Requirements

### FR-1: [Must] God Module Decomposition (WHAT)

Nine god modules must be decomposed such that the resulting components each have a single cohesive responsibility, measurable via SOLID metrics (NFR-1):

| God Module | Current LOC | Public Surface to Preserve |
|-----------|------------:|---------------------------|
| `emhass_adapter.py` | 2,733 | `EMHASSAdapter` (class, constructor + 27 public methods) |
| `trip_manager.py` | 2,503 | `TripManager` (class, constructor + 31 public methods) |
| `services.py` | 1,635 | 10 public functions (listed in AC-2.4) |
| `dashboard.py` | 1,285 | `import_dashboard`, `is_lovelace_available`, `DashboardImportResult`, 4 exception classes |
| `vehicle_controller.py` | 537 | `VehicleController`, `VehicleControlStrategy`, `create_control_strategy` |
| `calculations.py` | 1,690 | 20 names (17 functions + 2 classes + 1 constant) listed in AC-2.4 |
| `sensor.py` | 1,041 | HA platform contract — `async_setup_entry`, Entity classes (`TripPlannerSensor`, `EmhassDeferrableLoadSensor`, `TripSensor`, `TripEmhassSensor`) |
| `config_flow.py` | 1,038 | `EVTripPlannerFlowHandler`, `EVTripPlannerOptionsFlowHandler`, `async_get_options_flow` |
| `presence_monitor.py` | 806 | `PresenceMonitor` |

For each god module, the decomposition must satisfy:

- **FR-1.1**: Every resulting source file ≤ 500 LOC (screening gate per US-1; AC-1.1).
- **FR-1.2**: Public constructor signatures unchanged (AC-2.1, AC-2.2, AC-2.3) and HA platform contracts preserved (`async_setup_entry`, Entity ABC overrides).
- **FR-1.3**: All preserved public names continue to import from the same module path that callers currently use (AC-2.4, AC-2.5). Re-export mechanism (package vs sub-module, `__all__` declaration, etc.) is a **design decision** (design.md).
- **FR-1.4**: Each resulting class satisfies SOLID metrics (NFR-1): LCOM4 ≤ 2, verb diversity ≤ 5 (with documented per-class allowlists), ≤ 20 public methods, type hints ≥ 90%. HA `Entity` ABC required overrides do not count toward verb diversity or public-method ceilings.
- **FR-1.5**: Public API surface is **explicitly declared** in each new package via a machine-readable mechanism (e.g., `__all__`) so static tooling can detect accidental surface changes. Specific declaration mechanism is a design decision (design.md).
- **FR-1.6**: Bug-fix obligations co-located with the relevant decomposition: `[BUG-001]` `ventana_horas` AND `[BUG-002]` `previous_arrival` bugs (US-10, US-13) are co-fixed in the SAME commit as the calculations decomposition.
- **FR-1.7**: Pyright `typeCheckingMode = "basic"` 16 pre-existing errors in `sensor.py` are FIXED in this spec (no longer deferred to Spec 7) because Bar A NFR-7.A.5 requires zero pyright errors across the entire package.

> **Note on file/class names**: The specific file names, class names, package layouts, mixin vs. composition vs. facade choices, and per-file LOC budgets are **design decisions** documented in `design.md`. Requirements specify only the WHAT (which god modules must be decomposed, what public surface must be preserved, what quality metrics must hold).

_Requirements: US-1, US-2 | Design: Concrete file structures, class names, pattern selection, per-file LOC budgets_

### FR-2: [Must] Apply Design Patterns Where Appropriate (WHAT)

Each god-module decomposition must use design patterns or structural techniques **appropriate to the internal structure of the responsibilities being separated**. The decomposition is not satisfied by merely fragmenting a 2,000-LOC file into four 500-LOC files of unrelated responsibilities — the resulting components must have cohesive, named responsibilities.

- **FR-2.1**: For each god module, the design phase selects an appropriate decomposition technique (Facade + Composition, Facade + Mixins, Module-level Facade, Strategy, Builder, Functional Decomposition, etc.) and **justifies the selection in design.md** based on the responsibilities being separated.
- **FR-2.2**: A decomposition that produces files ≤ 500 LOC but leaves classes with LCOM4 > 2 or verb diversity > 5 (without justified allowlist) **fails this requirement**, regardless of LOC.
- **FR-2.3**: A decomposition that introduces a pattern not warranted by the structure (e.g., a Builder where there is no construction sequence) **fails this requirement** — patterns are tools, not goals.

> **Why this matters**: Splitting by LOC alone is mechanical. Cohesive decomposition requires identifying the underlying responsibilities and choosing a technique that matches them. The design phase is responsible for that choice; the requirements phase is responsible for stating that the choice must be made and justified.

_Requirements: US-1, US-4 | Design: Pattern selection rationale per package_

### FR-3: [Must] Import Cycle Policy (WHAT)

Module-load circular imports must be eliminated and prevented from regressing. Lazy-import escape hatches in trip-management code must be removed.

- **FR-3.1**: Zero module-load circular cycles in the decomposed code (`lint-imports` runs clean).
- **FR-3.2**: Explicit `lint-imports` contracts enforce:
  - `trip → sensor` forbidden (module-load dependency)
  - `presence_monitor → trip` forbidden at runtime (already broken via `TYPE_CHECKING`; the contract makes intent explicit)
  - `dashboard → trip|emhass|services` forbidden (cross-concern isolation)
  - `calculations` is a leaf — only depends on `const` + `utils` (FORBIDDEN against [trip, emhass, services, dashboard, vehicle, coordinator, sensor, presence_monitor, config_flow]); supplemented by an `independence` contract pairing `calculations` against the full module list to catch reverse-direction imports and ensure full isolation
  - `independence` over `[utils, const]` only (true leaves)
  - Layered architecture: `trip|emhass|dashboard` must NOT import `services`
  - Specific contract syntax and additional rules are **design decisions** (design.md).
- **FR-3.3**: All 7 lazy `from .sensor import ...` calls in trip-management code are removed (US-8).
- **FR-3.4**: `make import-check` runs both `ruff --select I` (import style) and `lint-imports` (cycle detection). Currently only runs `ruff`.
- **FR-3.5**: `pyproject.toml` is updated: the existing `[tool.import-linter]` block (with hyphen — incorrect key, ignored by current import-linter versions) is REMOVED, and a new `[tool.importlinter]` block (no hyphen — official key per import-linter v1.x+ docs) is ADDED with `root_package = "custom_components.ev_trip_planner"` (narrowed from `custom_components` to focus on the integration and avoid scanning HA fixtures). All 7 contracts above are declared under `[[tool.importlinter.contracts]]`.

_Requirements: US-2, US-4, US-8 | Design: Specific lint-imports contract content, replacement mechanism for lazy sensor imports_

### FR-4: [Must] Public API Re-Export Surface Preserved (WHAT)

Each decomposed package must expose the complete public API contract listed in AC-2.4 such that all existing callers continue to resolve their imports without modification.

- **FR-4.1**: Every public name listed in AC-2.4 is importable from the same module path callers use today (`from custom_components.ev_trip_planner.<module> import <Name>`).
- **FR-4.2**: The public surface is machine-readably declared (e.g., `__all__`) so accidental surface changes are detectable by tooling.
- **FR-4.3**: Mechanism (re-export at package `__init__.py`, sub-module direct exposure, `__all__` declaration, etc.) is a **design decision** (design.md).

_Requirements: US-2 | Design: Re-export mechanism, package layout, `__all__` placement_

### FR-5: [Must] Mutation Config Path Update (WHAT)

After god-module decomposition, the names referenced by `pyproject.toml` mutation configuration must remain resolvable so `mutmut` continues to function.

- **FR-5.1**: `[tool.quality-gate.mutation.modules.*]` entries reference module paths that exist after decomposition. Specific path-name updates are a design decision (design.md), driven by the chosen package layout.
- **FR-5.2**: `paths_to_mutate` remains at package level (`["custom_components/ev_trip_planner"]`) — no need to enumerate sub-packages because `mutmut` auto-includes them.
- **FR-5.3**: New sub-module `kill_threshold` entries inherit the parent module's current threshold as a placeholder. Recalibrating thresholds and improving kill rates is **Spec 5 scope**, not this spec.
- **FR-5.4**: `mutmut` runs without `KeyError` or path-not-found errors. Actual mutation score is not validated in this spec.

_Requirements: US-4 (architectural quality, not score) | Design: Specific module path entries, threshold inheritance rules_

### FR-6: [Should] Test File Naming and Splitting Convention (WHAT)

Test file organization must remain coherent after source decomposition.

- **FR-6.1**: Test files testing the public API of a class (e.g., `test_trip_manager.py`) keep their current names — they test the public facade, not internals.
- **FR-6.2**: Test files that test internal sub-module functions are **not** renamed in this spec. Renaming is deferred to Spec 5 where test consolidation improves mutation scores.
- **FR-6.3**: No test file is split into multiple files in this spec — only import paths are updated as needed.
- **FR-6.4**: After all decompositions, every test file's imports resolve correctly (`make test` passes).
- **FR-6.5**: `test_services_core.py` (was 800+ LOC pre-Spec 2 mock_hass removal) is kept as-is; only its imports are updated as needed.

_Requirements: US-3 | Design: Specific import-path updates per test file_

## Non-Functional Requirements

### NFR-1: SOLID Compliance Is the Primary Quality Criterion

LOC ≤ 500 is a **screening metric, not the goal**. The goal is SOLID-compliant code, measurable as follows:

- **NFR-1.1**: **S — Single Responsibility**: LCOM4 ≤ 2 per class (ideal: 1; acceptable: 2 with shared state). Verb diversity ≤ 5 unique action verbs per class (per-class allowlists permitted for cohesive-but-verbose responsibilities, documented in `solid_metrics.py` configuration). Both gated by `solid_metrics.py`.
- **NFR-1.2**: **O — Open/Closed**: Extension points use ABCs/Protocols, not if/elif chains. Verified by code review.
- **NFR-1.3**: **L — Liskov Substitution**: Implementations honor their ABC/Protocol contract. Verified by `pyright` strict-mode method-signature checks.
- **NFR-1.4**: **I — Interface Segregation**: Per-intra-package-ABC unused-method ratio ≤ 0.5 in concrete implementations (`solid_metrics.py` ISP check, implemented as part of this spec — see AC-4.7). HA framework ABCs excluded.
- **NFR-1.5**: **D — Dependency Inversion**: Zero module-load circular cycles (`lint-imports` clean), zero lazy-import escape hatches in trip-management code, zero inline instantiations in `__init__` bodies (collaborators DI-injected). `solid_metrics.py` D-check + `lint-imports` contracts gate this.
- **NFR-1.6**: **Type-hint coverage** ≥ 90% across decomposed modules (`solid_metrics.py` type-hint check).
- **NFR-1.7**: All classes ≤ 20 public methods (existing ARN-002, carried forward; HA `Entity` ABC overrides excluded).
- **NFR-1.8**: Method arity ≤ 5 parameters per function (existing ARN-003, carried forward).

> **Why this NFR is here**: A 480-LOC file with LCOM4 = 5 violates SRP just as much as a 2,500-LOC file with LCOM4 = 5. LOC is necessary but not sufficient. SOLID metrics are the actual quality bar.

### NFR-2: DRY Compliance

- **NFR-2.1**: Each known DRY violation collapses to one canonical location (US-5: `validate_hora`, `is_trip_today`, `calculate_day_index`). Consolidation happens in **Step 0.5** of the implementation sequence — BEFORE any package decomposition (design.md §6.2).
- **NFR-2.2**: Sliding-window code similarity = 0 duplications ≥ 5 consecutive lines across files (`jscpd` or `simian`).
- **NFR-2.3**: Error message strings consolidated in `const.py`.

### NFR-3: KISS Compliance

- **NFR-3.1**: Cyclomatic complexity ≤ 10 per function. C-grade (cc 11-20) is accepted when justified by the function's nature (pattern matching, enum dispatch, multi-category input handling) — the function MUST have a `# CC-N-ACCEPTED:` comment explaining the natural complexity. D-grade (cc > 20) always requires extraction into helpers.
- **NFR-3.2**: Maximum nesting depth ≤ 4 levels per function.
- **NFR-3.3**: No single function > 100 LOC. (The current `register_services()` 657-LOC monolith is the most extreme violation; AC-1.5 mandates its decomposition.)

### NFR-4: Build and Test Gates

- **NFR-4.1**: `make test` passes (≥ 1,820 tests) after each decomposition commit.
- **NFR-4.2**: `make e2e` passes (30 tests) after each decomposition commit.
- **NFR-4.3**: `make e2e-soc` passes (10 tests) after each decomposition commit.
- **NFR-4.4**: `make test-cover` passes with 100% coverage after each decomposition.
- **NFR-4.5**: `pyright` zero errors after each decomposition (including the 16 pre-existing `sensor.py` errors which are FIXED in this spec, not deferred).
- **NFR-4.6**: Mutation config in `pyproject.toml` references only valid module paths — no `KeyError` or path-not-found errors from `mutmut`. Actual mutation score is Spec 5 scope.

### NFR-5: Review and Validation Gates

- **NFR-5.1**: BMAD Consensus Party (Tier B) validates each decomposition: an Architect role, a Test-Architect role, an Adversarial role.
- **NFR-5.2**: Tier A deterministic checks (`make layer3a`) pass before Tier B is invoked.
- **NFR-5.3**: Consensus Party PASS/FAIL + issues documented in `chat.md` per decomposition.
- **NFR-5.4**: Any Consensus Party FAIL blocks further progress on that decomposition until resolved.
- **NFR-5.5**: Within one Consensus Party, agents run sequentially (Winston → Murat → Adversarial). Across packages, Consensus Parties are sequential — each must verify committed state of the previous package before the next decomposition begins.

### NFR-6: Backward Compatibility

- **NFR-6.1**: `services.yaml` unchanged — service IDs and schemas are frozen.
- **NFR-6.2**: HA `setup_entry()` calls `TripManager(...)` and `EMHASSAdapter(...)` with unchanged signatures (NFR-7.2 → AC-2.1, AC-2.2).
- **NFR-6.3**: `config_flow.py` imports from dashboard and services continue to resolve.
- **NFR-6.4**: `coordinator.py` imports `TripManager` and `EMHASSAdapter` continue to resolve.
- **NFR-6.5**: Panel registration in services and `__init__.py` continues to function — service handler functions still callable by HA.

### NFR-7: Final-State SOLID Maximum + Per-Checkpoint Progress

This NFR has **two distinct gates**: a final-acceptance gate (Bar A) and a per-checkpoint progress gate (Bar B). Both must hold.

#### NFR-7.A: Final state — SOLID at MAXIMUM (blocks merge to epic)

At the end of this spec (before the merge to `epic/tech-debt-cleanup`), the entire `custom_components/ev_trip_planner/` codebase must be at maximum SOLID compliance:

- **NFR-7.A.1**: `solid_metrics.py` reports **5/5 letters PASS** (S, O, L, I, D all green) for **every class in `custom_components/ev_trip_planner/`** — without exception. (The previous exemption for `config_flow`, `sensor`, `presence_monitor` is removed because all god modules are now in scope.) Per-class allowlists are permitted for cohesive-but-verbose responsibilities; HA `Entity` ABC required overrides do not count toward verb diversity or public-method ceilings.
- **NFR-7.A.2**: `principles_checker.py` reports **0 violations** in DRY, KISS, YAGNI, LoD, CoI for the decomposed modules.
- **NFR-7.A.3**: `antipattern_checker.py` reports **0 Tier A violations** (25 patterns).
- **NFR-7.A.4**: `lint-imports` reports **0 contract violations** with all 7 contracts (§4.4 of design.md) configured under the corrected `[tool.importlinter]` key.
- **NFR-7.A.5**: `pyright` reports **0 errors** in the decomposed modules. The 16 pre-existing `sensor.py` errors from HA Entity overrides ARE FIXED in this spec (no longer deferred to Spec 7) because the entire package is now in scope.
- **NFR-7.A.6**: `weak_test_detector.py` and `diversity_metric.py` report no regression vs baseline. New regression tests for `[BUG-001]` / `[BUG-002]` (US-10, US-13) must score as strong.
- **NFR-7.A.7**: `llm_solid_judge.py` and `antipattern_judge.py` (Tier B LLM judges) report no semantic regression vs baseline; semantic scores meet the same final-state PASS threshold as Tier A.
- **NFR-7.A.8**: **Bug-tracking obligations.** Both bugs `[BUG-001]` and `[BUG-002]` are tracked in `chat.md` with the 6-column table (BUG-ID, Source, Description, Root Cause, Status, Regression). The `[BUG-002]` row records the user clarification verbatim ("duration_hours no debería existir eso no está en los viajes. Lo que hay es UNA constante que se agrega a la hora de salida del viaje para estimar cuándo vuelve. previous_arrival es previous_departure + constante de clase (será return_buffer_hours o algo así)") and its English translation. Both must be Status=Fixed before merge.

> **What "maximum" means here**: 5/5 SOLID letters PASS, 0 Tier A anti-patterns, 0 DRY violations, 0 KISS violations (cc ≤ 10, nesting ≤ 4, no function > 100 LOC), 0 import-cycle contract violations, 0 pyright errors. Not "improved a bit." Not "better than before." **Maximum**, end-state (with C-grade accepted where justified).

#### NFR-7.B: Per-checkpoint progress (every commit, never regress)

Bar A is the final acceptance criterion. Bar B is the per-step progress check that prevents lazy mid-spec decompositions.

- **NFR-7.B.1**: Before starting, run `make quality-gate` and capture the baseline output. All metrics from all 8 scripts are recorded in `chat.md` as `[BASELINE-XXX]` tags. Baseline commit hash is recorded.
- **NFR-7.B.2**: The 8 quality-gate scripts (required reading before implementation): `solid_metrics.py`, `principles_checker.py`, `antipattern_checker.py`, `mutation_analyzer.py`, `weak_test_detector.py`, `diversity_metric.py`, `llm_solid_judge.py`, `antipattern_judge.py`.
- **NFR-7.B.3**: After **each** decomposition commit (not just at end of spec), run `make quality-gate` and compare to baseline. **Per-checkpoint thresholds:**
  - **Already-passing metrics**: maintain or improve (no regression).
  - **Currently-failing metrics for the module being decomposed**: must show measurable improvement at the commit that addresses them.
  - **SOLID overall**: pass rate must monotonically increase across commits (no temporary regressions); end-state is 5/5 (Bar A).
  - **DRY/KISS principles scores**: improve by ≥ 10% at the commit that addresses them; end-state is 0 violations (Bar A). Note: DRY violations should already be 0 after Step 0.5 pre-flight; subsequent commits only preserve.
  - **Anti-pattern violation count**: decreases monotonically; end-state is 0 Tier A violations (Bar A).
  - **Test weakness count**: decreases by ≥ 10% across the spec; end-state is no regression vs baseline.
  - **Test diversity score**: increases or maintains.
  - **LLM judges**: do not regress; end-state semantic PASS.
  - **Mutation score**: Spec 5 scope; transient path-change artifacts during this spec are acceptable.
- **NFR-7.B.4**: **Exemptions**: Metrics already at theoretical ceiling (LCOM4 = 1, coverage = 100%, type hints = 100%) are exempt from "must improve" — they must merely not regress. They still count as PASS for Bar A.
- **NFR-7.B.5**: Baseline and post-decomposition quality-gate results are committed to the spec's PR as evidence of improvement.

> **Why two bars?** Bar A defines **what "done" means** (5/5 SOLID PASS, end-state). Bar B defines **what "progress" means** (every commit moves toward Bar A and never regresses). Bar B's "≥ 10%" / "≥ 20%" thresholds are floors detecting lazy mid-spec decompositions; Bar A is the absolute final-acceptance criterion. The spec is not done until Bar A holds; intermediate commits must satisfy Bar B.

### NFR-8: Quality-Gate Diagnostic Use

The quality-gate baseline is a **diagnostic tool**, not a final-step verification. The executor must:

1. Run baseline now (`make quality-gate`).
2. Document understanding: in `chat.md`, write 1-2 sentences per metric explaining what it measures and what the baseline value is.
3. Identify improvement opportunities per metric.
4. Target each metric consciously during decomposition — "improve the score," not just "make tests pass."

Example: if `solid_metrics.py` S-letter fails because `trip_manager.py` has too many public methods with too many verbs, the decomposition should group methods by verb family — directly improving S-score.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **HA startup breakage** | If constructor signatures or import paths drift, the integration fails to load. | NFR-6.2/6.3/6.4 gate identical signatures; verify `setup_entry()` callable + tests pass after each decomposition. |
| **Test import breakage** | Tests reaching into private helpers across god modules may break when those helpers move. | Migration mechanism (transitional bridges, phased cleanup) is design-phase scope; FR-6.4 gates tests passing after each decomposition. |
| **Pattern selection mismatch** | Choosing a wrong pattern (e.g., Builder where Strategy fits) creates rework and obscures intent. | FR-2.1 mandates pattern justification in design.md; NFR-5 (Consensus Party) catches semantic mismatches. |
| **LCOM4/verb-diversity gaming** | Decomposing along arbitrary lines to satisfy LCOM4 without genuine cohesion. | NFR-5 Consensus Party validates semantic SRP, not just numeric LCOM4. FR-2.2/2.3 makes "metric-passing but pattern-mismatched" decompositions fail. |
| **Lazy-import removal blocked** | Sensor platform registration timing may make full lazy-import elimination impractical in this spec. | US-8 risk note: defer to Spec 4 with explicit `# TODO(spec-4)` markers + lint-imports contract documenting forbidden dependency. Decision is design-phase, not implementation-phase. |
| **Dashboard `__file__` regression** | Silent template-load failure if path resolution is fragile. | US-7 acceptance criteria specify a path-depth-robust mechanism; design.md specifies it; `make e2e-soc` exercises template loading. |
| **Quality-gate baseline drift** | Baseline measured at the wrong commit invalidates comparison. | NFR-7.1 specifies baseline is captured BEFORE any decomposition begins; baseline commit hash is recorded in `chat.md`. |
| **Scope expansion to 9 modules increases spec duration** | Adding `sensor.py`, `config_flow.py`, `presence_monitor.py` to scope (originally 6 modules) inflates the spec to 10 implementation steps (Step 0.5 + 9 decompositions + Step 10 shim cleanup). | Mitigate by sequencing decomposition by risk: lowest-risk leaves first (calculations → vehicle → dashboard), then composition (emhass), then most-coupled facade (trip), then service registration (services), then HA platform-bound (sensor → config_flow → presence_monitor). Each step is an atomic checkpoint commit; `git revert <SHA>` reverts to the previous green state without disturbing other steps. |
| **Pyright `sensor.py` 16 errors** | Bar A requires zero pyright errors across the entire package; the 16 pre-existing `sensor.py` errors must be fixed in this spec, not deferred. | Sequence the `sensor.py` decomposition AFTER `trip/` decomposition so the `SensorCallbackRegistry` is in place; then narrow `Entity` ABC override types per HA-core conventions during the split-by-entity-class decomposition. |

## Out of Scope

- **Spec 5 mutation score improvement** — Raising mutation kill rate is entirely Spec 5 scope. This spec only updates `pyproject.toml` paths (FR-5).
- **Spec 4 high-arity fixes** — Parameter objects for functions with > 5 params (deferred to Spec 4, except where arity is resolved by the decomposition itself). Full removal of the now-unused `return_buffer_hours` parameter (US-13 AC-13.2) is also deferred to Spec 4.
- **Deep DI for trip → sensor circular dependency** — This spec eliminates lazy imports (US-8); full event-based decoupling of TripManager from sensor platform is deferred (Spec 4 or future).
- **Hypothesis property-based tests** — Tool installed in Spec 2; writing actual property-based tests is generally Spec 5, EXCEPT the [BUG-001]/[BUG-002] invariant test (US-10 AC-10.5) which IS in this spec because it directly verifies the bug-fix.
- **time-machine migration** — Tool installed in Spec 2; migrating conftest.py manual datetime mocking to time-machine is Spec 7.
- **flake8-pytest-style enforcement** — Tool installed in Spec 2; fixing violations is Spec 7.
- **Coverage-driven test renaming** — Renaming `test_coverage_*.py` files to behavior-driven names is Spec 5.
- **`.cover` file cleanup** — Already addressed in Spec 1.
- **Dashboard exception class hierarchy redesign** — Exception narrowing is a design-phase improvement, not a requirement.
- **Pylint R09xx re-enablement** — Confirmed `radon` subsumes these in design phase; enforcement in Spec 7.

> **NOTE — items REMOVED from out-of-scope (now IN scope due to user-directed scope expansion):**
> - `sensor.py` decomposition (1,041 LOC) — was Spec 7; now in Spec 3 (FR-1).
> - `config_flow.py` decomposition (1,038 LOC) — was Spec 7; now in Spec 3 (FR-1).
> - `presence_monitor.py` decomposition (806 LOC) — was Spec 7; now in Spec 3 (FR-1).
> - Pyright `typeCheckingMode = "basic"` 16 errors in `sensor.py` — was Spec 7; now in Spec 3 (NFR-7.A.5, FR-1.7).

## Dependencies

- **Required**: Spec 2 (Test Architecture Reorganization, PR #46) — tests must be organized in `tests/unit/` and `tests/integration/` before structural refactoring.
- **Required**: Tools installed in Spec 0 (`solid_metrics.py`, `import-linter`, `deptry`, `pyright`, `mutmut`) and Spec 2 (`radon` — must be installed before implementation).
- **Required**: **Executor must understand the quality-gate baseline** — `make quality-gate` must be run and all 8 scripts' outputs read and understood **before** starting decomposition.
- **Required**: **Executor must understand each module's internals** — before decomposing, the executor must understand what each god module does, how data flows, and what edge cases exist (US-11).
- **Optional/Parallel**: Spec 1 (Dead Code) — already merged (PR #45). Verify the removed `schedule_monitor.py` and its tests are not referenced.
- **Future**: Spec 4 (High-Arity Fixes) — after Spec 3, parameter lists in decomposed modules may need adjustment; full removal of unused `return_buffer_hours` (US-13 AC-13.2) belongs here.
- **Future**: Spec 5 (Mutation Score Ramp) — mutation config paths updated in this spec; score improvement is a separate spec.
- **External**: BMAD Consensus Party agents available for Tier B validation per decomposition.

## Traceability Notes

- `pure_validate_hora`, `pure_is_trip_today`, `pure_sanitize_recurring_trips` already exist in `utils.py` (post-Spec 1). DRY violations (US-5) are residual duplications still present in god modules; consolidation is Step 0.5 pre-flight.
- The 7 lazy `from .sensor import` lines in `trip_manager.py` (lines 732, 741, 794, 803, 893, 931, 938 in current head) are the explicit targets of US-8.
- `calculations.py:691-699` (`calculate_multi_trip_charging_windows`) is the `[BUG-001]` `ventana_horas` location (US-10).
- `calculations.py:733-735` (`calculate_multi_trip_charging_windows`) is the `[BUG-002]` redundant `+ return_buffer_hours` location (US-13).
- `register_services()` 657 LOC body (line 31 → line 688) and `_populate_per_trip_cache_entry` 266 LOC are the explicit KISS violation targets (US-6).
- `solid_metrics.py` `max_unused_methods_ratio` is currently a stub; AC-4.7 / NFR-1.4 require its implementation as part of this spec (~60-100 LOC fix).

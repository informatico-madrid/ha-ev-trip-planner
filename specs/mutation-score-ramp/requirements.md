---
spec: mutation-score-ramp
basePath: specs/mutation-score-ramp
epic: tech-debt-cleanup
phase: requirements
updated: 2026-05-18
---

# Requirements: Mutation Score Ramp

## Goal

Reach **100% mutation kill rate** for the project — every per-module rate at `1.00`, `make mutation-gate` green with all thresholds ratcheted to `1.00` — through an iterative ramp of real test-quality improvements (and, where production-code structure makes logic untestable, testability refactors). First harden the mutation tooling (Makefile, quality gate, analyzer, pyproject config) so it runs perfectly and gates accurately against the current module structure. 100% means: every mutant is either killed by an honest test, or formally adjudicated genuinely unkillable by ≥2 expert-subagent review (NFR-1) — never gamed by a skip, pragma, lowered threshold, or excluded code.

## User Stories

### US-1: Mutation tooling runs perfectly

**As a** developer running quality checks
**I want to** run `make mutation`, `make mutation-gate`, and `make layer2` without errors
**So that** mutation results are trustworthy and reproducible.

**Acceptance Criteria:**
- [ ] AC-1.1: `make mutation` completes a full run with exit 0; no crash, no unknown-flag error. Measured runtime documented (~9.7 min baseline, 11571 mutants).
- [ ] AC-1.2: `make mutation-gate` runs `mutation_analyzer.py --gate` without traceback and emits the gate table + JSON.
- [ ] AC-1.3: `make layer2` runs the mutation gate, weak-test detector, and diversity metric end-to-end without error.
- [ ] AC-1.4: 0 mutmut timeouts across the full run (regression check vs baseline).
- [ ] AC-1.5: `mutmut results --all true` output parses cleanly — `_other` bucket count is 0 (every mutant maps to a known module).

### US-2: Quality-gate config matches the current module structure

**As a** maintainer
**I want** the pyproject `[tool.quality-gate.mutation.modules.*]` thresholds to reference only modules that exist, named exactly as the analyzer aggregates them
**So that** the gate computes a real per-module verdict instead of silently falling back to the global threshold.

**Acceptance Criteria:**
- [ ] AC-2.1: Stale `dashboard.importer`, `dashboard.builder`, `dashboard.template_manager` threshold entries removed (`dashboard/` was merged into `panel.py`).
- [ ] AC-2.2: Dotted sub-module keys that the analyzer cannot match are rebased to the top-level module name the analyzer produces. The analyzer aggregates by `custom_components.ev_trip_planner.<module>` (path segment 3), so packages collapse: `trip.*`→`trip`, `emhass.*`→`emhass`, `services.*`→`services`, `calculations.*`→`calculations`, `vehicle.*`→`vehicle`.
- [ ] AC-2.3: Every module emitted by `mutmut results` has exactly one matching threshold entry in pyproject; every threshold entry matches a module the analyzer emits (no orphan keys, no unmatched modules).
- [ ] AC-2.4: `make mutation-gate` reports each module against its own threshold (no module silently using `global_kill_threshold` because its key did not match).
- [ ] AC-2.5: A documented mapping (module name as emitted by analyzer ↔ pyproject key ↔ source path) is recorded so future renames stay consistent.

### US-3: Quality gate is green

**As a** maintainer
**I want** `make mutation-gate` to return gate OK
**So that** the mutation gate stops being a known-failing check.

**Acceptance Criteria:**
- [ ] AC-3.1: With current thresholds, 3 modules fail today (`__init__` 32.5% vs 51%, `trip` 47.5% vs 48%, `utils` 86.1% vs 89%). After the ramp, those 3 modules meet or exceed their thresholds via real test improvements.
- [ ] AC-3.2: `make mutation-gate` exits 0 (gate `OK`) on a fresh full mutmut run.
- [ ] AC-3.3: No threshold was lowered to pass the gate, and no code was excluded to pass the gate (verified against git diff of pyproject + mutmut config).

### US-4: Iterative ramp to 100% mutation kill rate

**As a** maintainer
**I want** the mutation kill rate raised in successive iterations until it reaches 100%, each iteration being a real test improvement
**So that** the score climbs progressively and verifiably to the committed target without gaming.

**Acceptance Criteria:**
- [ ] AC-4.1: Baseline recorded before work starts: overall kill rate, per-module kill rates, killed/total counts (from a fresh `make mutation`).
- [ ] AC-4.2: The ramp runs in **as many iterations as the work requires to reach 100%** — the count is not fixed and is decided by the task plan. Each iteration targets specific modules and ends with a re-measured overall kill rate strictly greater than the previous iteration's. The ramp continues until every module's kill rate is `1.00`.
- [ ] AC-4.3: Each iteration's improvement is one or more of: (a) strengthened weak test — adds assertions on values/logic the test already exercises; (b) removed duplicate test; (c) new test covering previously untested behavior; (d) weak test replaced with a strong one; (e) testability refactor (US-5) that makes a previously unkillable mutant killable by an honest test.
- [ ] AC-4.4: Final state of this spec: gate `OK` AND **overall kill rate = 100%** — every mutant is either killed by an honest test or formally adjudicated genuinely unkillable via ≥2 expert-subagent review (NFR-1), with each adjudication logged in `chat.md`/`.progress.md`. A per-iteration delta table documents the climb from baseline to 100%.
- [ ] AC-4.5: After each iteration, raise the satisfied modules' thresholds in pyproject toward `target_final = 1.00` so the gate ratchets upward and cannot regress (the `increment_step` ratchet mechanism is exercised, not just documented). The ramp ends with **every module threshold set to `1.00`**.
- [ ] AC-4.6: `make test` and `make test-cover` still pass (100% coverage) after every iteration — no regression.

### US-5: Production code refactored only to enable testing

**As a** developer
**I want to** refactor production code where its structure makes logic genuinely untestable
**So that** mutants become killable by honest tests rather than hidden by pragmas.

**Acceptance Criteria:**
- [ ] AC-5.1: Any production refactor in this spec is justified in `chat.md` by naming the specific mutant(s)/logic it makes testable.
- [ ] AC-5.2: Refactors preserve public API and behavior — `make test` passes and import-linter contracts hold.
- [ ] AC-5.3: No refactor changes externally observable behavior of any HA entity, service, or config flow.

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | `make mutation` runs a full mutmut run to exit 0 | High | Run completes, exit 0, runtime recorded |
| FR-2 | `make mutation-gate` runs `mutation_analyzer.py --gate` cleanly and prints table + JSON | High | Gate report produced, no traceback |
| FR-3 | `make layer2` runs mutation gate + weak-test detector + diversity metric end-to-end | High | All three sub-steps run, no error |
| FR-4 | Remove stale `dashboard.*` threshold entries from pyproject | High | grep finds no `dashboard.` mutation keys |
| FR-5 | Rebase dotted sub-module threshold keys to analyzer-emitted top-level names | High | Every key matches a module the analyzer emits |
| FR-6 | Ensure every analyzer-emitted module has exactly one threshold entry and vice versa | High | 1:1 module↔key correspondence verified |
| FR-7 | Make the 3 currently-failing modules meet threshold via test improvements | High | `__init__`, `trip`, `utils` all PASS |
| FR-8 | `make mutation-gate` returns gate `OK` | High | Exit 0 on fresh run |
| FR-9 | Execute as many ramp iterations as needed to reach 100% overall kill rate, each iteration raising the score | High | Per-iteration delta table, monotonic increase, final overall rate = 100% |
| FR-10 | Ratchet satisfied modules' thresholds upward toward 1.00 after each iteration | Medium | pyproject thresholds increase, gate stays OK |
| FR-11 | Record baseline + final mutation metrics in spec artifacts | Medium | Baseline and final numbers documented |
| FR-12 | Refactor production code only where needed for testability, API-preserving | Medium | Justified in chat.md, tests + import-linter pass |
| FR-13 | Document the module-name ↔ pyproject-key ↔ source-path mapping | Medium | Mapping table committed in spec |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | **No skip/pragma to dodge a mutant or metric.** `# pragma: no mutate`, `@pytest.mark.mutmut_skip` added to hide failures, blanket `mutmut_skip`, or `-k` test-exclusion args added solely to suppress failures are PROHIBITED. Pre-existing exclusions (`test_solid_metrics`, `test_vehicle_controller_event` — source-inspection tests genuinely incompatible with mutation) MAY remain but MUST NOT be expanded. A super-exceptional new exclusion is permitted ONLY after explicit review and approval by **multiple (≥2) expert subagents**, with the approval recorded in `chat.md`/`.progress.md`. | Count of new skip/pragma constructs added to dodge a mutant or metric | 0 (unless multi-subagent-approved and logged) |
| NFR-2 | Score is improved by real test work, never by lowering thresholds or excluding code | Threshold/exclusion diff | No threshold lowered; no code excluded to pass |
| NFR-3 | Test suite stays green and coverage stays 100% after every iteration | `make test-cover` | Pass, `--cov-fail-under=100` |
| NFR-4 | Full mutmut run remains practical for scheduled CI | Wall-clock | ≤ ~15 min on the project's reference machine |
| NFR-5 | No mutmut timeouts introduced | timeout count | 0 |
| NFR-6 | Public API, import-linter contracts, and HA-observable behavior unchanged by any refactor | `make test`, `lint-imports` | All pass |
| NFR-7 | Each iteration records a one-line What & Why in `chat.md` before its verify step | chat.md entries | One per iteration/task |

## Glossary

- **Mutation testing**: Technique that injects small faults ("mutants") into source code and checks whether the test suite detects them.
- **Mutant**: A single mutated copy of the source (e.g. `+` → `-`, `True` → `False`, condition negated).
- **Killed mutant**: A mutant that caused at least one test to fail — the suite detected the fault. Good.
- **Survived mutant**: A mutant that all tests still passed against — the suite did NOT detect the fault. Bad.
- **Mutation score / kill rate**: `killed / (killed + survived + timeout + no_tests)`, per module and overall.
- **Weak test**: A test that exercises code but asserts little (e.g. only that it ran, or only one trivial value) — lets many mutants survive.
- **Strong test**: A test that asserts on the values and logic it exercises, so mutating that logic makes the test fail.
- **Duplicate test**: A test that verifies behavior already fully covered by another test — adds maintenance cost without adding mutation-killing power.
- **Threshold (per-module)**: Minimum kill rate a module must meet for the gate to pass, from `[tool.quality-gate.mutation.modules.*]`.
- **Ratchet / `increment_step`**: Mechanism that raises a module's threshold after it improves, locking in progress toward `target_final`.
- **Gate**: `mutation_analyzer.py --gate` — compares measured per-module rates to thresholds and returns `OK`/`NOK`.
- **Unkillable mutant**: A surviving mutant for which no honest test can observe a difference (e.g. log-level changes, HA framework-internal registration calls).

## Out of Scope

- Coverage gap closure / removing `pragma: no cover` from source — that is Spec 6's scope (coordinate, do not own).
- SOLID/arity refactoring for its own sake — only testability-driven refactors here.
- CI workflow changes / scheduling the mutmut run in CI — Spec 8.
- Migrating `tests_excluded_from_mutmut/` directory contents — track but do not block on it.
- Changing the mutmut engine, runner, or `mutation_analyzer.py` architecture beyond what AC-1/AC-2 require.

## Definition of Done (measurable)

1. `make mutation`, `make mutation-gate`, `make layer2` all exit 0 with no traceback.
2. pyproject mutation config has 1:1 correspondence with analyzer-emitted modules; no `dashboard.*` keys.
3. **Overall mutation kill rate = 100%** — every per-module kill rate is `1.00`. Every mutant is either killed by an honest test, or formally adjudicated genuinely unkillable by ≥2 expert-subagent review (NFR-1) with the adjudication logged in `chat.md`/`.progress.md`. No mutant is suppressed without that approved adjudication.
4. `make mutation-gate` returns gate `OK` with **every per-module threshold ratcheted to `target_final = 1.00`**.
5. A per-iteration delta table documents the monotonic climb from the 57.1% baseline to 100%.
6. Thresholds only ratcheted upward (never down); `make test-cover` passes at 100% coverage; `make test` and import-linter contracts pass.
7. Zero new skip/pragma constructs added to dodge mutants/metrics (NFR-1) — except multi-subagent-approved, logged adjudications of genuinely unkillable mutants.

## Dependencies / Assumptions

- **Dependencies**: mutmut 3.5.0, `mutation_analyzer.py`, `weak_test_detector.py`, `diversity_metric.py`, pytest, `.venv` activated for all commands.
- **Assumes** the dead-code-elimination spec's module renames are final: `emhass_adapter`→`emhass`, `trip_manager`→`trip`, `vehicle_controller`→`vehicle`, `dashboard/` merged into `panel.py`.
- **Assumes** `mutation_analyzer.py` aggregates per-mutant results by source path segment 3 (top-level module/package name) — verified in the script. Split packages therefore appear as single entries (`trip`, `emhass`, `services`, `calculations`, `vehicle`); per-sub-module gating is NOT available without an analyzer change, which is out of scope.
- **Assumes** the ~9.7 min full-run figure (measured 2026-05-18) holds on the reference machine; reruns are needed per iteration to re-measure.
- **On "unkillable" survivors**: HA framework glue, logging, and voluptuous schema defaults are NOT automatically unkillable. Many such mutants can be killed by refactoring production code for testability (US-5) or by asserting on observable effects. Only a mutant that genuinely cannot be killed after honest effort qualifies for the NFR-1 escape hatch (≥2 expert-subagent adjudication, logged). Reaching 100% means every mutant is killed or so adjudicated — no silent exclusions.

## Related Specs

| Spec | Relationship |
|------|-------------|
| Epic: tech-debt-cleanup | Parent epic — ARN-010 (all modules meet mutation thresholds, global floor 100%) |
| Spec 0: Tooling Foundation | Provided `make mutation`, `make layer2`, quality-gate scaffolding (done) |
| Spec 2: Test Architecture Reorganization | Established `tests/unit`+`tests/integration` layout and mutmut `tests_dir` (done) |
| Spec 3: SOLID Refactoring | Renamed modules into packages; this spec's config cleanup rebases keys to that structure (done) |
| Spec 4b: Dead Code Elimination | Removed orphaned tests; final module names assumed by this spec (done) |
| Spec 6: Coverage Gap Closure | Overlaps — covering IO paths often kills mutants; coordinate, separate ownership |
| Spec 8: Security & CI Hardening | Will schedule the mutmut run in CI; out of scope here |

## Verification Contract

**Project type**: `library`
(Custom HA integration: a Python package with no standalone server/UI entry point this spec touches. The mutation ramp is exercised entirely via `make` targets and pytest — no browser, no API surface. E2E suites exist for the integration but are unrelated to this spec.)

**Entry points**:
- `make mutation` → `.venv/bin/mutmut run --max-children=4`
- `make mutation-gate` → `python3 .claude/skills/quality-gate/scripts/mutation_analyzer.py . --gate`
- `make layer2` → mutation gate + `weak_test_detector.py` + `diversity_metric.py`
- `pyproject.toml` sections `[tool.mutmut]` and `[tool.quality-gate.mutation.*]`
- `make test` / `make test-cover` (regression guard)

**Observable signals**:
- PASS: `make mutation` exits 0, run completes, 0 timeouts. `make mutation-gate` prints `RESULT: ✅ OK` and exits 0. Gate table shows **every module's `kill_rate == 1.00` against a threshold of `1.00`**. Overall kill rate in JSON `== 1.0`. Every surviving-then-removed mutant traces to either an honest test or a logged ≥2-subagent adjudication. `make test-cover` exits 0 at 100% coverage.
- FAIL: any `make` target exits non-zero or prints a Python traceback. `mutation-gate` prints `RESULT: ❌ NOK` with a Failed-modules list. Overall kill rate below `1.0`, or any module below `1.00`. A module appears in `mutmut results` with no matching pyproject key (falls back to global threshold). `_other` bucket non-zero. Overall kill rate flat or lower across an iteration. A mutant suppressed without a logged multi-subagent adjudication.

**Hard invariants**:
- No threshold lowered; no source/test excluded to pass the gate (NFR-2).
- No new `pragma: no mutate` / `mutmut_skip` / suppressive `-k` arg (NFR-1) unless ≥2-subagent-approved and logged.
- Public API, import-linter contracts, and HA-observable behavior unchanged (NFR-6).
- Test suite stays green at 100% coverage after every iteration (NFR-3).

**Seed data**:
- Activated `.venv` with mutmut 3.5.0 and dev dependencies installed.
- A completed `mutmut run` (mutmut cache populated) before any `--gate` invocation.
- Clean working tree on branch `mutation-score-ramp` (epic `tech-debt-cleanup`).

**Dependency map**:
- Shares `pyproject.toml` with all quality-gate layers and `[tool.mutmut]` config.
- Shares `tests/unit/` + `tests/integration/` with the whole project — test edits here affect coverage and Layer 1/2 for every module.
- `mutation_analyzer.py` is shared with the quality-gate skill (Layer 2 / `step-03-layer2.md`).

**Escalate if**:
- A module's surviving mutants appear genuinely unkillable and meeting threshold would require a skip/pragma — escalate for ≥2-expert-subagent review (NFR-1).
- The analyzer's segment-3 aggregation proves insufficient (real need for per-sub-module gating) — requires an analyzer change, which is out of scope; escalate for a scope decision.
- A required testability refactor would change a public API or HA-observable behavior.
- Full mutmut runtime exceeds ~15 min on the reference machine (NFR-4 breach).

## Unresolved Questions

- Per-sub-module gating (`trip.crud_mixin`, `services.handlers`, …) is impossible with the current analyzer (segment-3 aggregation). Confirmed scope decision: rebase keys to top-level module names for THIS spec; defer any analyzer enhancement. Flagging in case stakeholders want sub-module granularity instead.
- `definitions` has a 0.45 threshold but ~100% measured kill rate — ratchet it up to ~1.00 as part of AC-4.5, or leave loose? Assumption: ratchet it up (it is already met).
- The number of ramp iterations is unbounded and decided by the task plan — as many as needed to reach 100%. Per-iteration jump size is unconstrained per the user directive; only the final state (100%) is fixed.
- The proportion of mutants that ultimately require the NFR-1 adjudication escape hatch (vs. killed outright) is unknown until the ramp is executed; it must be minimized by aggressive testability refactoring (US-5) before any mutant is declared unkillable. If the adjudicated set grows large enough to suggest a tooling/architecture gap, escalate for a scope decision.

## Next Steps

1. User approves this requirements.md.
2. Run `/ralphharness:design` — design phase: produce the threshold-rebasing plan (analyzer-emitted module list ↔ pyproject keys), the ratchet workflow, and the per-iteration module-targeting strategy.
3. `/ralphharness:tasks` — decompose into tooling-fix tasks (US-1/US-2/US-3) then the ramp iterations to 100% (US-4) — the task plan decides the iteration count — each with measure/verify steps.
4. `/ralphharness:implement` — execute the ramp.

<!-- Changed: initial requirements for mutation-score-ramp — tooling/config hardening + green gate + exercised ratchet + ≥4 ramp iterations; 100% framed as epic-level target, not this spec's claim. -->
<!-- Changed: 100% mutation kill rate is now THIS spec's committed deliverable and Definition of Done (Goal, US-4, AC-4.x, FR-9, DoD, Verification Contract). Iteration count unfixed (unbounded, task-plan-decided) — supersedes the prior "≥4 iterations". Removed the Out-of-Scope bullet excluding literal 100%. 100% kept honest: every mutant killed by an honest test or formally adjudicated unkillable via ≥2 expert-subagent review (NFR-1); NFR-1/NFR-2 unchanged. -->

---
spec: mutation-score-ramp
basePath: specs/mutation-score-ramp
epic: tech-debt-cleanup
phase: requirements
updated: 2026-05-21
---

# Requirements: Mutation Score Ramp

## Goal

Reach **100% mutation kill rate** for the project — every per-module rate at `1.00`, `make mutation-gate` green with all thresholds ratcheted to `1.00` — through an iterative ramp of real test-quality improvements (and, where production-code structure makes logic untestable, testability refactors). First harden the mutation tooling (Makefile, quality gate, analyzer, pyproject config) so it runs perfectly and gates accurately against the current module structure. 100% means: every mutant is either killed by an honest test, or formally adjudicated genuinely unkillable by ≥2 expert-subagent review (NFR-1) — never gamed by a skip, pragma, lowered threshold, or excluded code.

## 2026-05-22 Revision — Effective-100% supersedes literal-100% (AUTHORITATIVE)

> **This section supersedes the literal "every per-module rate == 1.00" target wherever it appears below.** It is the result of `/bmad-technical-research` (artifact: `_bmad-output/planning-artifacts/research/technical-mutation-testing-php-vs-python-research-2026-05-22.md`) and the human's directive to define the genuinely-unkillable residue precisely before continuing.

**Why the literal-100% target was a planning error.** Academic survey data shows **less than 10% of mutants are genuinely equivalent** ([arXiv 2024](https://arxiv.org/pdf/2404.09241)). Infection (PHP) — where the human reaches "100%" — already separates **MSI** from **Covered MSI** and annotates the genuinely-equivalent residue with `@infection-ignore-all`. So even in PHP, "100%" means *effective* 100%: kill everything killable, formally annotate the small equivalent residue. The literal "every module 1.00 AND ≤10 pragmas AND equivalents exist" combination in the original Goal/DoD is self-contradictory and drove fabrication (reviewer flagged FABRICATION on tasks 2.20, 2.22; 153-172 pragmas added then removed under NFR-1b).

**The corrected target — Effective-100% MSI:**

```
effective_MSI = killed / (total − registered_equivalent)   →   target = 1.00
```

- **Maximize the raw kill rate honestly first** (real tests, integration-first, multi-assert, US-5 refactors). The real baseline is **56.9%** (task 1.1: 11571 mutants, 6581 killed, 4989 survived). The honest raw ceiling for a well-tested HA integration is ~85-95%, NOT 56.9%.
- **The genuinely-unkillable residue is documented, not eliminated**, in a persistent **Equivalent-Mutant Registry** (`specs/mutation-score-ramp/equivalent-mutants.md`): one dossier per registered mutant (id, file:line, original→mutated, taxonomy category, the decision-test argument proving no test can differentiate, human-approval quote, date).
- **Every `# pragma: no mutate` MUST reference a registry entry id.** No naked pragmas; no mass-category labels.
- **Pragma ceiling reframed:** the arbitrary "~10 project-wide" cap is replaced by "minimized and individually-justified; expect more than 10 given HA framework glue, but the registered set must stay percentage-bounded (target ≤~10% of mutants) and every entry carries a per-mutant dossier + human approval." A registry approaching the 37%-survivor figure is a red flag of gaming.

**Hard prerequisite (was silently deferred for weeks):** `make mutation` is BLOCKED on Python 3.14 by a `dbus_fast` incompatibility (`TypeError: access must be a PropertyAccess class`, reproduced 2026-05-22). No kill-rate number is real until mutmut runs on a compatible interpreter (Python 3.12 is installed). This is now task 5.1, the gate for all subsequent measurement.

**Persistence for new code:** the registry and gate must outlive this spec — when new code adds new survivors, each must be killed or registered (with dossier + approval) before merge. This is task 5.5.

**Autonomy model (human decision 2026-05-22) — reconciles NFR-1 with unattended execution.** The autonomous run NEVER escalates-and-waits mid-flight: killable mutants are killed; the 4 community-recognized obvious-intrinsic categories (idempotent-arithmetic, log/diagnostic-only, performance-only, type-infeasible-default) are **auto-registered + pragma'd with a dossier** (pre-authorized); `framework-absorbed-arg` and anything ambiguous is **parked** as `CANDIDATE-PENDING-APPROVAL` (dossier only, no pragma, no block). The loop reaches a **clean planned stop** at task 5.6 when 0 killable survivors remain, where the human resolves all parked candidates in one approval pass. NFR-1's human-approval guarantee is preserved exactly where it matters (the `framework-absorbed-arg` category that hid the prior gaming); it is delegated to pre-authorization only for the 4 obviously-intrinsic classes.

**Uniformity & cache (constraints C-A..C-C in tasks.md):** all mutation work runs on a single `.venv` rebuilt in place on Python 3.12 (no second venv); every `mutmut` invocation uses identical args (`--max-children=4`, CLI flags never override `[tool.mutmut]`); the mutmut cache is cleared before the authoritative re-baseline so no Python-3.14 artifact poisons results.

**Definition of Done (revised):** Effective-100% MSI on a fresh real run; the Equivalent-Mutant Registry is complete, minimized, percentage-bounded, and fully human-approved; every pragma maps 1:1 to a registry entry; `make test` + `make test-cover` (100%) + `make import-check` green; the persistence gate fails on any unregistered survivor. The literal "every module kill_threshold == 1.00" of the original DoD is reinterpreted as "every module's *effective* rate == 1.00".

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
- [ ] AC-5.4: Every US-5 refactor follows SOLID, DRY, KISS — extract pure helpers (single responsibility), reuse via shared module (DRY), keep API minimal (KISS).
- [ ] AC-5.5: For every pragma added in the spec, evidence of a US-5 attempt is recorded in `chat.md`: the source lines considered, the helper signature attempted, and the reason extraction was infeasible (e.g. HA framework call where the call *is* the outcome). No pragma may be added without this evidence.

### US-6: Strengthen existing tests with multi-attribute assertions (assertion density)

**As a** developer raising the mutation kill rate
**I want** every behavioural test to assert on every relevant attribute of the returned value/state/dispatched call
**So that** a single test kills many mutants instead of one — and no mutant slips through because the test only checked one attribute.

**Background**: Inspection of the current suite shows many tests with 1–2 `assert` lines on multi-attribute returns (dicts, dataclasses, dispatched-call args). A mutation on any *un-asserted* attribute survives even though the test already executes the mutated line. Strengthening assertions (no new tests) is the cheapest way to reclaim kills.

**Acceptance Criteria:**
- [ ] AC-6.1: For every module still below 100% kill rate, a survivor-driven audit lists tests that *execute* a surviving mutant but assert on too few attributes; each is strengthened in-place (no new test files needed).
- [ ] AC-6.2: When a function returns a dict, the strengthened test asserts on every key relevant to the test's purpose — not just one. When a function returns a dataclass, every field touched by the function under test is asserted.
- [ ] AC-6.3: When a function dispatches a call (HA service, coordinator refresh, log emission), the test asserts on the full argument tuple/kwargs dict (domain, service, data, blocking flag) — not just that the call happened.
- [ ] AC-6.4: When a function emits a log line, the strengthened test asserts on the exact log constant *and* every interpolated value (or uses the extracted `_LOG_*` constant directly so mutations on it fail).
- [ ] AC-6.5: Audit evidence (the survivor → existing-test mapping + the strengthened-assert diff) is logged in `chat.md` per iteration.

### US-7: Integration-first testing for HA framework glue

**As a** developer killing mutants in modules dominated by HA framework glue (`config_flow`, `services`, `panel`, `sensor`, `__init__`, `coordinator`)
**I want** the suite to lean on `pytest-homeassistant-custom-component`-backed integration tests that go through real HA core, registries, and config-entry lifecycle
**So that** mutations on framework call args (domain/service/data, schema defaults, panel kwargs) become observable through HA state instead of being hidden by mocks.

**Background**: A large share of surviving mutants are arg/string mutations on `hass.services.async_call(...)`, `async_register_panel(...)`, voluptuous schema defaults, etc. Unit tests mock these calls; the mutation changes the mocked arg, and no assertion notices. An integration test driving the real HA core *exercises* the wired-up effect — the wrong arg surfaces as a missing entity, missing panel, missing schema field.

**Acceptance Criteria:**
- [ ] AC-7.1: Each module dominated by HA glue (≥30% of its survivors classified as "framework call args" or "schema defaults") gets at least one integration-level test exercising the real HA flow end-to-end via the test harness.
- [ ] AC-7.2: Integration tests assert on the *observable* HA-side effect: registered entity/service/panel id, config-entry state, schema-validated value — not on mock call args.
- [ ] AC-7.3: Where the existing unit test only verifies "the mock was called", it is either replaced by an integration test (preferred) or *complemented* by a multi-attribute assert covering every call argument (AC-6.3).
- [ ] AC-7.4: Pre-existing source-inspection exclusions (`test_solid_metrics`, `test_vehicle_controller_event`) are not expanded; new integration tests do not introduce new mutmut exclusions (NFR-1).

### US-8: Mutmut tooling tuned per Hovmöller's 15 rules

**As a** maintainer of the mutation gate
**I want** the mutmut configuration in `pyproject.toml` to follow the documented best-practice rules (mutate only covered lines, bound stack depth, optional type-check filter, explicit test-file exclusion)
**So that** the gate measures real test gaps — not unreachable code paths or transitive-incidental tests — and the kill rate is comparable across iterations.

**Reference**: `mutmut.readthedocs.io` config reference + Anders Hovmöller, *"Mutation testing in practice"* (kodare.net, 2016).

**Acceptance Criteria:**
- [ ] AC-8.1: `[tool.mutmut]` in `pyproject.toml` sets `mutate_only_covered_lines = true` (rule 1) — mutants are generated only for lines actually executed by the test suite.
- [ ] AC-8.2: `[tool.mutmut]` sets `max_stack_depth` (rule 3) to bound transitive coverage — value chosen per design.md, justified in `chat.md`.
- [ ] AC-8.3: `do_not_mutate` already excludes `tests/**` and `conftest.py` (rule 2) — verified, no regression.
- [ ] AC-8.4: A baseline run on the tuned config records the new total-mutant count and per-module kill rate as the **authoritative re-baseline**; previous deltas remain in `.progress.md` for history but the gate ratchet rebases to the new numbers.
- [ ] AC-8.5: The 15-rule compliance table (rule ↔ requirement/AC ↔ status) is committed in `design.md` and re-audited at every gate checkpoint.

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
| FR-14 | Strengthen existing tests with multi-attribute assertions before writing new tests | High | Each iteration logs "tests strengthened" count and survivor delta attributable to assertion density |
| FR-15 | Add at least one integration test (real HA harness) per HA-glue-dominated module | High | Integration test file added; asserts on HA-side observable effect; module's survivor count strictly drops |
| FR-16 | Tune mutmut config per the 15 Hovmöller rules (covered-lines, stack-depth, do_not_mutate) | High | `[tool.mutmut]` includes `mutate_only_covered_lines`, `max_stack_depth`; verified by grep + baseline rerun |
| FR-17 | Audit every pragma in the suite for US-5 evidence; remove any pragma without it | High | `chat.md` shows per-pragma US-5 attempt log; pragmas without evidence removed and module re-mutmut'd |
| FR-18 | Replace generic test data (0, 1, "", None) with distinctive values where it kills numeric/string mutants | Medium | Audit diff shows replaced literals; per-module kill rate strictly increases |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | **Pragmas are real, scarce, and human-escalated.** `# pragma: no mutate`, `@pytest.mark.mutmut_skip`, blanket `mutmut_skip`, or `-k` exclusion args are NOT a normal tool — they are an emergency hatch reserved for mutants the broader testing community has documented as intrinsically unkillable (e.g. `__version__` constants, performance-only `break`-vs-`continue` where the loop terminates regardless, debug-only branches behind a compile-time constant). The bar: a reference-class similar to the well-known PHP/Infection community list (~10 pragmas across a project 10× this size). **Before adding any pragma, the executor MUST escalate to the human** — the human approves or rejects in writing in `chat.md`. The pre-existing `test_solid_metrics` / `test_vehicle_controller_event` exclusions MAY remain but MUST NOT be expanded. The prior `≥2`-subagent procedure is INSUFFICIENT — it does not replace human escalation. | Pragmas added without prior human approval; total pragma count | 0 unapproved; total ≤ ~10 across the whole project |
| NFR-1b | **Remove pragmas added without human escalation in earlier iterations.** The 118 pragmas previously labeled "verified not US-5 applicable" (iterations 13–18) were added without the human-escalation step required by NFR-1. They must be re-evaluated one by one: for each, either (a) write a real test / refactor (US-5/US-6/US-7) that kills the mutant, or (b) escalate to the human and obtain written approval to keep it. Any pragma whose justification is "HA framework glue", "string case mutation", "default_value on `.get()`", "log text", or similar mass-category label is presumed removable and must be retried with the integration-first + multi-assert strategy. | Pragmas surviving the re-audit without human approval | 0 |
| NFR-2 | Score is improved by real test work, never by lowering thresholds or excluding code | Threshold/exclusion diff | No threshold lowered; no code excluded to pass |
| NFR-3 | Test suite stays green and coverage stays 100% after every iteration | `make test-cover` | Pass, `--cov-fail-under=100` |
| NFR-4 | Full mutmut run remains practical for scheduled CI | Wall-clock | ≤ ~15 min on the project's reference machine |
| NFR-5 | No mutmut timeouts introduced | timeout count | 0 |
| NFR-6 | Public API, import-linter contracts, and HA-observable behavior unchanged by any refactor | `make test`, `lint-imports` | All pass |
| NFR-7 | Each iteration records a one-line What & Why in `chat.md` before its verify step | chat.md entries | One per iteration/task |
| NFR-8 | **Multi-attribute assertion density.** A behavioural test that touches a multi-attribute value (dict, dataclass, dispatched call) MUST assert on every attribute relevant to the test's stated purpose. Tests that assert "only the call happened" or "only one key" leave mutants on the un-asserted attributes alive and are considered weak; they MUST be strengthened in place. | Per strengthened test: number of additional assertions vs prior version; per module: drop in surviving mutants attributable to assertion strengthening | ≥1 added assertion per strengthened test; survivor delta logged |
| NFR-9 | **Integration-first for HA glue.** Modules whose survivors are ≥30% "framework call args" or "schema defaults" MUST grow at least one integration test using `pytest-homeassistant-custom-component` that drives the real HA core and asserts on the HA-side effect (registered entity/service/panel id, config-entry data, schema-validated value). Mocks remain only where the interaction is *itself* the outcome and no observable HA-side effect exists. | Integration tests added per HA-glue module; assertions on HA-side state | ≥1 integration test per qualifying module |
| NFR-10 | **Distinctive test data.** Test fixtures and parametrised cases MUST use distinguishable, realistic values — not `0`/`1`/`""`/`None` as defaults. A test that uses `vehicle_id = ""` lets a mutation that changes `"vehicle_id"` to `"XXvehicle_idXX"` survive because the mocked `.get()` returns the same `""` in both cases. Each iteration's test diff is reviewed for generic defaults; replacements with realistic constants (`"tesla-model-3"`, `42.7`, `"NFKD"` for accent-stripping) are recorded. | Generic-default occurrences in iteration diff | 0 introduced; existing flagged and replaced where they hide mutants |
| NFR-11 | **US-5 evidence is mandatory before any pragma.** For every existing pragma in the codebase and every pragma proposed in this spec, `chat.md` MUST contain: the mutant id, the source lines, the helper signature considered for extraction, the reason extraction was infeasible (or, equivalently, the integration-test attempted and why it could not observe the effect), and the human's written approval. A pragma without this dossier is invalid. | Per-pragma dossier completeness | 100% of remaining pragmas have a complete dossier with human approval |
| NFR-12 | **SOLID / DRY / KISS for US-5 refactors.** Extracted helpers are single-responsibility (one input shape, one return shape), reused across callers (no duplicated helper per file), and minimal (no premature abstraction). Helpers live in a shared `_helpers.py` per package; tests for the helpers are unit-level and assertion-dense (NFR-8). | Per-refactor: duplication count (`grep -c` of the extracted pattern still present in source); helper LOC | 0 duplicated patterns remaining; helper LOC bounded by single-responsibility |
| NFR-13 | **Tuned mutmut config.** `[tool.mutmut]` in `pyproject.toml` reflects rules 1–3 of the Hovmöller 15: `mutate_only_covered_lines = true`, `max_stack_depth` set explicitly, `do_not_mutate` excludes tests and conftest. The 15-rule table in `design.md` is kept current. | grep of `[tool.mutmut]` for each setting | All three present and correct |

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
2. pyproject mutation config has 1:1 correspondence with analyzer-emitted modules; no `dashboard.*` keys; `[tool.mutmut]` carries `mutate_only_covered_lines = true`, an explicit `max_stack_depth`, and a `do_not_mutate` excluding tests/conftest (NFR-13 / Hovmöller rules 1–3).
3. **Overall mutation kill rate = 100%** — every per-module kill rate is `1.00`. Mutants are killed by honest tests (multi-attribute asserts per NFR-8, integration tests for HA glue per NFR-9, distinctive data per NFR-10) and US-5 refactors (NFR-12). Pragmas are the rare exception, each carrying the NFR-11 dossier *and* the human's written approval from NFR-1; the project-wide pragma count is reference-class small (~10 max).
4. `make mutation-gate` returns gate `OK` with **every per-module threshold ratcheted to `target_final = 1.00`**.
5. A per-iteration delta table documents the monotonic climb from the 57.1% baseline to 100% — including the iterations that *remove* pragmas added without human approval (NFR-1b) and replace them with real tests/refactors.
6. Thresholds only ratcheted upward (never down); `make test-cover` passes at 100% coverage; `make test` and import-linter contracts pass.
7. Every surviving pragma in the repo at completion has: (a) human written approval in `chat.md`, (b) the NFR-11 dossier (mutant id, source, helper signature considered, reason extraction failed, integration-test attempt and outcome), (c) belongs to a community-recognised intrinsically-unkillable category. Any pragma without all three is removed.
8. The iteration that re-audits the 118 prior pragmas (NFR-1b) is recorded in `chat.md` with per-pragma verdict (kept-with-approval | removed-and-killed-by-test | removed-and-killed-by-refactor).
9. Each below-100% module gains at least one new integration test using `pytest-homeassistant-custom-component` (NFR-9) where the survivor classification flags HA glue dominance.

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
<!-- Changelog 2026-05-21 (hot revision, NO progress reset): supersedes the ≥2-subagent pragma path with mandatory HUMAN escalation (NFR-1) — pragmas are now scarce, reference-class ~10 across the project. Adds NFR-1b: re-audit and mostly REMOVE the 118 prior "verified not US-5 applicable" pragmas. New user stories US-6 (multi-attribute asserts), US-7 (integration-first for HA glue), US-8 (Hovmöller 15-rule tooling tune). New NFRs 8–13: assertion density, integration-first, distinctive test data, pragma dossier, SOLID/DRY/KISS, tuned mutmut config. New FRs 14–18 covering strengthened tests, integration tests, mutmut config tuning, pragma audit, distinctive data. DoD rewritten: kill via tests/refactor — pragma is exception with human approval + community-recognised category. Completed Phase 1 + Phase 2 (149/159 tasks) preserved untouched. -->

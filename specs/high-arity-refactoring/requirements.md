# Requirements: High-Arity Refactoring

## Goal
Close the arity tech-debt opened in epic `tech-debt-cleanup` AC-4.1–4.9 AND audit all `# pragma: no cover` marks: (1) audit existing `qg-accepted` arity suppressions for honest rationale, (2) wrap the 3 remaining non-accepted high-arity functions with `@dataclass(frozen=True)` parameter objects, (3) remove dead backward-compat kwargs from `_populate_per_trip_cache_entry`, and (4) audit every `# pragma: no cover` mark — remove or justify each one.

---

## User Stories

### US-1: Audit Existing `qg-accepted` Arity Marks
**As a** maintainer
**I want to** verify every `qg-accepted` arity suppression has a specific, honest rationale
**So that** suppressions represent genuine design trade-offs, not shortcuts

**Acceptance Criteria:**
- [ ] AC-1.1: Every `qg-accepted` comment for an arity violation states the actual reason (framework constraint, algorithm invariant, canonical API) — not just "needed all params"
- [ ] AC-1.2: Any mark whose rationale is generic/vague ("helper needs all params", "needs all context") is flagged for wrapping and its suppression removed
- [ ] AC-1.3: Audit findings are documented in a short inline comment update or noted in the PR description

---

### US-2: Wrap Three Remaining Non-Accepted High-Arity Functions
**As a** developer
**I want to** call `_compute_window_start`, `calculate_charging_window_pure`, and `_populate_profile` via a typed parameter object
**So that** call sites are readable, parameters are named at the call site, and the arity gate passes without suppressions

**Acceptance Criteria:**
- [ ] AC-2.1: `calculations/windows.py` — `calculate_charging_window_pure` (6p) gains a `ChargingWindowPureParams` dataclass; function signature becomes `(params: ChargingWindowPureParams) -> Dict[str, Any]`
- [ ] AC-2.2: `calculations/windows.py` — `_compute_window_start` (7p) gains a `WindowStartParams` dataclass; function signature becomes `(params: WindowStartParams) -> datetime`
- [ ] AC-2.3: `calculations/power.py` — `_populate_profile` (6p) gains a `PopulateProfileParams` dataclass; function signature becomes `(params: PopulateProfileParams) -> None`
- [ ] AC-2.4: Each new dataclass uses `@dataclass(frozen=True)` with `kw_only=True`, co-located in the same module as the target function, named `<FunctionName>Params`
- [ ] AC-2.5: All callers of the three functions (within `calculations/` and tests) are updated to use the new dataclass
- [ ] AC-2.6: The `# qg-accepted:` comment for each wrapped function is removed

---

### US-3: Remove Dead Backward-Compat Kwargs from `_populate_per_trip_cache_entry`
**As a** developer
**I want to** remove the 6 unused kwargs kept for test compatibility in `_populate_per_trip_cache_entry`
**So that** the method signature honestly reflects its actual interface and test callers use `PerTripCacheParams`

**Acceptance Criteria:**
- [ ] AC-3.1: `emhass/adapter.py:_populate_per_trip_cache_entry` — the 6 optional kwargs (`hora_regreso`, `pre_computed_inicio_ventana`, `pre_computed_fin_ventana`, `pre_computed_charging_window`, `adjusted_def_total_hours`, `soc_cap`) are removed from the signature
- [ ] AC-3.2: All test callers that pass any of those kwargs are updated to use only `PerTripCacheParams`
- [ ] AC-3.3: After cleanup the `qg-accepted` arity comment reflects the true arity (self + params = 2 effective params) or is removed entirely if `make layer3a` passes without it

---

### US-4: Fix Any `qg-accepted` Marks with Weak Rationale (Discovered During Audit)
**As a** maintainer
**I want to** replace weak suppressions with proper dataclass wrappers
**So that** `qg-accepted` only covers genuinely immovable arity (framework constraints, algorithm invariants)

**Acceptance Criteria:**
- [ ] AC-4.1: For each mark identified as weak in US-1, the function is wrapped following the pattern in US-2
- [ ] AC-4.2: The weak `qg-accepted` comment is removed after wrapping; the function no longer appears in `make layer3a` output
- [ ] AC-4.3: If no weak marks are found, US-4 is a no-op — no wrapping required

**Initial assessment of borderline marks** (to evaluate during implementation):
- `calculate_charging_window_pure` — `# qg-accepted: arity=6 is the charging window API — domain inputs only` — weak; "domain inputs" does not explain why a param object is impossible → **wrap it** (already covered by US-2)
- `_compute_window_start` — `# qg-accepted: arity=7 — chain algorithm needs all context for window start` — weak; no reason a `WindowStartParams` is impossible → **wrap it** (already covered by US-2)
- `_populate_profile` — `# qg-accepted: arity=6 — helper needs all params for profile population` — weak; private helper, no external API constraint → **wrap it** (already covered by US-2)

---

### US-5: Audit and Remediate `# pragma: no cover` Marks
**As a** maintainer
**I want to** verify every `# pragma: no cover` suppression is genuinely untestable code — not a coverage shortcut
**So that** the 100% coverage requirement reflects real test coverage, not suppressed gaps

**Acceptance Criteria:**
- [ ] AC-5.1: Scan all source files in `custom_components/ev_trip_planner/` for `# pragma: no cover`
- [ ] AC-5.2: Classify each mark as: (A) **Legitimate** — TYPE_CHECKING block, `__repr__`/`__str__` boilerplate, `if __name__ == "__main__"`, unreachable defensive code with documented reason; (B) **Removable** — code that can be tested but isn't; (C) **Needs justification** — no comment explaining why it's untestable
- [ ] AC-5.3: For each Class B mark: write the missing test (or note why the test is impossible), then remove the pragma
- [ ] AC-5.4: For each Class C mark: add a specific inline justification (`# pragma: no cover — <reason>`) or write the test and remove the pragma
- [ ] AC-5.5: Class A marks (genuinely untestable) remain — with explicit justification added if missing
- [ ] AC-5.6: `make test` coverage does not regress (100% still passes after removing suppressions + adding tests)

---

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | New dataclasses use `@dataclass(frozen=True, kw_only=True)` | High | pyright passes; ruff passes (no RUF009/B006 violations) |
| FR-2 | New dataclasses named `<FunctionName>Params`, defined in same module as target function | High | Code review / naming audit |
| FR-3 | `ChargingWindowPureParams` created in `calculations/windows.py` | High | AC-2.1 |
| FR-4 | `WindowStartParams` created in `calculations/windows.py` | High | AC-2.2 |
| FR-5 | `PopulateProfileParams` created in `calculations/power.py` | High | AC-2.3 |
| FR-6 | Dead kwargs removed from `_populate_per_trip_cache_entry` | High | AC-3.1–3.3 |
| FR-7 | All callers (prod + test) updated for changed signatures | High | `make test` passes |
| FR-8 | `make layer3a` reports zero arity violations or all remaining have documented `qg-accepted` | High | `make layer3a` output |
| FR-9 | `_validate_field` in `config_flow/main.py:264` is explicitly assessed — excluded if effective arity ≤ 5 (self excluded) | Low | Comment in PR confirming effective arity = 5 |
| FR-10 | No new `qg-accepted` marks added for functions that can reasonably be wrapped | High | Code review |
| FR-11 | All `# pragma: no cover` marks are scanned and classified (A/B/C) | High | AC-5.1–5.2 |
| FR-12 | Class B pragmas: missing tests written, pragma removed | High | AC-5.3 |
| FR-13 | Class C pragmas: justification added or test written + pragma removed | Medium | AC-5.4 |
| FR-14 | Class A pragmas: justification comment present (add if missing) | Low | AC-5.5 |
| FR-15 | `make test` still passes at 100% coverage after pragma removals | High | AC-5.6 |

---

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Type safety | pyright basic mode | Zero type errors |
| NFR-2 | Test coverage | pytest-cov line coverage | No regression vs. pre-change baseline |
| NFR-3 | Code style | ruff + pylint | Zero new violations |
| NFR-4 | Arity gate | `make layer3a` | Zero unaccepted violations |
| NFR-5 | All quality gates | `make check` | Full pass |

---

## Glossary

- **qg-accepted**: Inline comment (`# qg-accepted: <rationale>`) that suppresses a quality gate violation. Must state a specific reason why the violation is genuinely immovable.
- **parameter object**: A `@dataclass(frozen=True)` that groups related function parameters into a single named, typed argument.
- **frozen dataclass**: A Python dataclass with `frozen=True` — instances are immutable after construction. Project standard for param objects.
- **high-arity function**: Any function with more than 5 parameters (excluding `self` for methods). Threshold enforced by `solid_metrics.py` in `make layer3a`.
- **kw_only**: Dataclass option (`kw_only=True`) requiring all fields to be passed as keyword arguments at instantiation. Recommended for 5+ field param objects.
- **backward-compat kwargs**: Unused optional parameters retained only so existing test call sites don't break. These are dead code and must be removed.
- **weak rationale**: A `qg-accepted` comment that describes the symptom ("needs all params") rather than the actual constraint (e.g., "HA framework callback signature is fixed by the event bus contract").
- **pragma: no cover**: Coverage suppression comment. Legitimate uses: `TYPE_CHECKING` blocks, `__repr__`/`__str__` boilerplate, unreachable defensive code. Illegitimate: code that could be tested but wasn't. Requires inline justification.

---

## Out of Scope

- Functions already confirmed as valid `qg-accepted` (do not touch):
  - `_try_populate_window` (11p) — BMAD consensus 2026-05-17, inherent algorithm arity
  - `_propagate_deficits` (10p) — BMAD consensus 2026-05-17
  - `_build_milestone` (8p) — BMAD consensus 2026-05-17
  - `calculate_deficit_propagation` (9p) — BMAD consensus, public API
  - `calculate_multi_trip_charging_windows` (8p) — BMAD consensus, public API
  - `calculate_power_profile` / `calculate_power_profile_from_trips` (8p each) — BMAD consensus
  - All `trip/_sensor_callbacks.py` callbacks (6p) — HA framework dispatch, signature not under our control
  - `calculate_energy_needed` / `calculate_trip_time` in `core.py`/`windows.py` — `qg-accepted` with specific rationale ("canonical domain API")
- Not a full re-audit of Spec 3 SOLID work
- Not adding `__post_init__` validation logic to any param dataclass
- Not refactoring complexity violations (`cc-accepted` marks are a separate concern)
- `# pragma: no cover` in test files themselves (only source files in `custom_components/`)
- Not touching `config_flow/main.py:_validate_field` if effective arity (excluding `self`) is ≤ 5

---

## Dependencies

- Spec 3 (`3-solid-refactor`) — merged via PR #47. All post-Spec3 module locations are stable.
- Epic `tech-debt-cleanup` — AC-4.1–4.6 status to be updated in `.epic-state.json` after this spec closes.

---

## Success Criteria

- `make layer3a` exits zero with no unaccepted arity violations
- `make check` (test + lint + typecheck) exits zero
- `_populate_per_trip_cache_entry` has no dead kwargs
- Every `qg-accepted` arity comment in `calculations/` states a specific, honest constraint (not "needs all params")
- All `# pragma: no cover` marks in `custom_components/` are classified and either justified with a specific reason or removed with test coverage added

---

## Verification Contract

**Project type**: `library`

**Entry points**:
- `calculations/windows.py` — `calculate_charging_window_pure`, `_compute_window_start`
- `calculations/power.py` — `_populate_profile`
- `emhass/adapter.py` — `EMHASSAdapter._populate_per_trip_cache_entry`

**Observable signals**:
- PASS looks like:
  - `make layer3a` exits 0 with no arity violations listed
  - `make test` exits 0, same test count as before
  - `make typecheck` exits 0 (pyright: 0 errors)
  - `make lint` exits 0 (ruff: 0 violations)
  - `_populate_per_trip_cache_entry` signature shows only `(self, params: PerTripCacheParams)`
- FAIL looks like:
  - `make layer3a` reports any function with arity > 5 and no `qg-accepted` comment
  - `make test` shows any test failures or import errors
  - pyright reports type errors on new dataclass fields or call sites
  - ruff reports RUF009 (mutable default in dataclass field)

**Hard invariants**:
- No existing test may be deleted to make the suite pass — only updated to use new param objects
- `qg-accepted` marks for BMAD-consensus functions (`_try_populate_window`, `_propagate_deficits`, `_build_milestone`, all sensor callbacks) must not be removed
- `make test` coverage must not regress (100% must hold after pragma removals + new tests)

**Seed data**:
- No runtime system state required — this is a pure Python library refactor
- All verification via `make check` (unit tests + static analysis)

**Dependency map**:
- `3-solid-refactor` spec — shares `calculations/` and `emhass/adapter.py`; verify no merge conflicts
- `solid-refactor-coverage` spec — test coverage for SOLID refactor; any caller updates must remain covered

**Escalate if (pragma audit)**:
- More than 10 Class B pragmas found (significant test-writing effort — reassess scope with user)
- A pragma covers HA framework integration code that genuinely cannot be unit-tested (document and keep as Class A)

**Escalate if (arity)**:
- A `qg-accepted` audit finds more than 3 weak marks (scope expansion risk — check with user before wrapping all)
- Removing backward-compat kwargs from `_populate_per_trip_cache_entry` causes test failures that require non-trivial test rewriting (may indicate the kwargs are used in integration tests, not just unit tests)
- pyright reports errors in caller code that require changes outside `calculations/` or `emhass/adapter.py`

---

## Unresolved Questions

- `_validate_field(self, ...)` in `config_flow/main.py:264` — declared 6 params; excluding `self` leaves 5. Confirm effective arity ≤ 5 at implementation time; if so, no action needed and existing `qg-accepted` comment can be removed as a minor cleanup.
- Epic closure — does this spec own updating `.epic-state.json` AC-4.1–4.9 status, or is that the epic coordinator's responsibility?

---

## Next Steps
1. Approve requirements — user reviews and confirms scope (3 wraps + 1 cleanup + 1 audit)
2. Tasks phase — generate implementation tasks from these requirements
3. Implement — create dataclasses, update callers, remove dead kwargs, remove weak `qg-accepted` marks
4. Verify — run `make check` + `make layer3a`; confirm all gates pass
5. Epic closure — update AC-4.1–4.9 status in `.epic-state.json`

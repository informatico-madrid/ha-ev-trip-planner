---
spec: mutation-score-ramp
basePath: specs/mutation-score-ramp
epic: tech-debt-cleanup
phase: design
updated: 2026-05-21
---

# Design: Mutation Score Ramp

## Overview

Phased delivery: (Phase A) harden the mutation tooling and rebase `pyproject.toml` mutation keys so the gate computes a real per-module verdict, then fix the 3 gate-failing modules to lock the gate green; (Phase B) ramp the remaining modules worst-first through iterations of honest test improvement and US-5 testability refactors, ratcheting each satisfied module's threshold toward `1.00` until `make mutation-gate` is `OK` with every per-module rate = `1.00`. The only honest path to 100% for a genuinely intrinsic/equivalent mutant is the NFR-1 `≥2`-expert-subagent adjudication gate.

## 2026-05-22 Revision — Effective-100% model (AUTHORITATIVE, supersedes literal-100%)

> Supersedes the Overview's "every per-module rate = 1.00" and the "literal 100%" Technical Decision. Driven by `/bmad-technical-research` + human directive. See `requirements.md` § "2026-05-22 Revision".

### R1. Effective-MSI definition

```
effective_MSI = killed / (total − registered_equivalent)        target = 1.00
```

This mirrors Infection's **Covered MSI** + `@infection-ignore-all` model. Mechanism in mutmut: a registered-equivalent mutant carries `# pragma: no mutate` (removing it from the denominator), and **every such pragma references a registry entry id** — so effective-100% emerges from the existing per-module gate without any analyzer change. The honest order is: (1) maximize raw kill rate via tests/refactors, (2) register only the genuinely-unkillable residue.

### R2. Interpreter-compatibility component (the unblock)

`make mutation` crashed in mutmut's clean-test import phase on **Python 3.14**: the `homeassistant → habluetooth → bleak → dbus_fast` chain hit `dbus_fast.service.dbus_property` → `TypeError: access must be a PropertyAccess class` (reproduced 2026-05-22). Plain `pytest` collects fine (2761 tests) but mutmut's import model double-loads `dbus_fast`, breaking the `PropertyAccess` isinstance check. **Resolution:** `.venv` rebuilt in-place on **Python 3.12** (2026-05-22). All commands use `.venv/bin/python` (Makefile line ~250 fixed). 2761 tests pass. bleak import succeeds. All `.progress.md` numbers after iteration ~13 are stale/fabricated and MUST be discarded; the Python-3.12 full run is the sole authoritative source.

### R3. Equivalent-Mutant Registry artifact

**File:** `specs/mutation-score-ramp/equivalent-mutants.md` (persistent, outlives this spec).

**Effective-MSI formula:** `effective_MSI = killed / (total_mutants − registered_equivalent) = 1.00`. Every `# pragma: no mutate` MUST reference a registry entry id (e.g., `# pragma: no mutate # EQ-001`).

**Per-entry dossier schema:**

| Field | Content |
|---|---|
| `id` | Unique registry id (e.g., `EQ-001`) |
| `file:line` | Source file and line number |
| `original` → `mutated` | Mutation transformation |
| `category` | One of the taxonomy categories |
| `decision_test` | Argument proving NO test can differentiate mutant from original |
| `status` | `REGISTERED-AUTO` | `CANDIDATE-PENDING-APPROVAL` | `HUMAN-APPROVED` | `REJECTED` |
| `human_approval` | Verbatim `HUMAN APPROVED:` quote + date (when status is `HUMAN-APPROVED`) |
| `date` | ISO date of registration |

**Taxonomy (the only acceptable categories):** (1) idempotent-arithmetic (`*1`,`/1`,`+0`,`-0`); (2) log/diagnostic-only (text/level, no behavioral/state effect); (3) performance-only (`break`↔`continue` where the loop terminates regardless; `__version__`); (4) type-infeasible-default (caught by mypy/pyright); (5) framework-absorbed-arg (HA normalizes/ignores the mutated value, producing identical observable HA state — must be PROVEN per-mutant, never assumed). The first four are pre-authorized for auto-registration; (5) and anything else are parked for human approval.

**Taxonomy (the only acceptable categories):** (1) idempotent-arithmetic (`*1`,`/1`,`+0`,`-0`); (2) log/diagnostic-only (text/level, no behavioral/state effect); (3) performance-only (`break`↔`continue` where the loop terminates regardless; `__version__`); (4) type-infeasible-default (caught by mypy/pyright); (5) framework-absorbed-arg (HA normalizes/ignores the mutated value, producing identical observable HA state — must be PROVEN per-mutant, never assumed).

### R4. Persistence gate for new code

Beyond this spec: any new survivor introduced by future code must be **killed or registered** (dossier + human approval) before merge. The gate FAILS on any survivor that has neither a kill nor a registry entry. Documented in contributor docs so new code/tests consult the registry rather than re-discovering "unkillable" mutants.

### R5. Reframed pragma ceiling + autonomy model (human decision 2026-05-22)

The arbitrary "~10 project-wide" cap (NFR-1) is replaced by: **minimized, individually-justified, percentage-bounded (target ≤~10% of mutants).** Expect more than 10 entries given HA framework glue; each still needs its own dossier. No mass-category labels — those are presumed killable until a per-mutant decision-test proves otherwise.

**Autonomy model (so the loop runs unattended for hours, finishes in one go, never deadlocks):**

| Survivor class | Action during autonomous run | Human gate |
|---|---|---|
| Killable | Write the real test (NFR-8/9/10/12) | none |
| Obvious-intrinsic — the 4 pre-authorized categories (idempotent-arithmetic, log/diagnostic-only, performance-only, type-infeasible-default) | AUTO-REGISTER + `# pragma: no mutate`, dossier, status `REGISTERED-AUTO` | batch-ratified at 5.6, non-blocking |
| `framework-absorbed-arg` or anything else | PARK as `CANDIDATE-PENDING-APPROVAL` (dossier only, NO pragma, NO block) | single human approval pass at 5.6 |

This reconciles NFR-1 with unattended execution: the loop never escalates-and-waits mid-flight. It reaches a **clean planned stop** at task 5.6 when 0 killable survivors remain; the human then resolves the parked candidates in one sitting. The `framework-absorbed-arg` gate is preserved precisely because that category is where the prior 153-172-pragma gaming hid (NFR-1b).

## Architecture

### A. Overall phased flow

```mermaid
graph TB
    subgraph PhaseA["Phase A — Tooling & Config Hardening (US-1/2/3)"]
        A1[Verify make mutation / mutation-gate / layer2 run clean] --> A2[Rebase pyproject mutation keys to analyzer-emitted names]
        A2 --> A3[Remove stale dashboard.* keys + dotted keys]
        A3 --> A4[Fix __init__, trip, utils via honest tests]
        A4 --> A5{mutation-gate == OK?}
        A5 -->|no| A4
        A5 -->|yes| B0
    end
    subgraph PhaseB["Phase B — Worst-first Ramp to 100% (US-4)"]
        B0[Pick next worst module by kill rate] --> B1[Ramp iteration]
        B1 --> B2{All modules rate == 1.00?}
        B2 -->|no| B0
        B2 -->|yes| DONE[Gate OK, all thresholds 1.00]
    end
```

### B. Per-iteration ramp loop (the unit of work in Phase B and step A4)

```mermaid
graph TB
    M1[Targeted mutmut run on iteration module] --> M2[List survivors via mutmut results --all true]
    M2 --> M3[Classify each survivor]
    M3 -->|weak/missing test| T1[Strengthen / dedupe / add / replace test]
    M3 -->|structure makes logic untestable| T2[US-5 testability refactor of production code]
    M3 -->|candidate intrinsic/equivalent| ADJ[NFR-1 adjudication sub-flow]
    T1 --> RM[Re-run targeted mutmut on module]
    T2 --> RM
    ADJ -->|approved no-mutate| RM
    ADJ -->|rejected| T2
    RM --> RG{module rate improved & test/cover green?}
    RG -->|no| M2
    RG -->|yes| RAT[Ratchet module threshold up via increment_step]
    RAT --> CP{Gate checkpoint due?}
    CP -->|yes| FULL[Full ~10-min mutmut run + make mutation-gate]
    CP -->|no| NEXT[Next iteration]
    FULL --> NEXT
```

### C. NFR-1 adjudication sub-flow (decision #3/#4)

```mermaid
sequenceDiagram
    participant Dev as Ramp executor
    participant E1 as Expert subagent 1
    participant E2 as Expert subagent 2
    participant Log as chat.md / .progress.md
    Dev->>Dev: US-5 refactor attempted FIRST and exhausted
    Dev->>E1: Mutant id + source + test evidence "claim: intrinsic/equivalent"
    Dev->>E2: Same package, independent (blinded) review
    E1-->>Dev: verdict + reasoning
    E2-->>Dev: verdict + reasoning
    alt Both APPROVE
        Dev->>Dev: Add # pragma: no mutate to that exact line
        Dev->>Log: Log mutant id, both subagents, both verdicts
    else Any REJECT
        Dev->>Dev: Refactor for testability OR write stronger test
    end
```

## Components

This spec edits configuration and tests; it has no runtime "components" in the service sense. The design components are the *artifacts and mechanisms* the tasks phase operates on.

### C1. pyproject mutation config (`[tool.quality-gate.mutation]`)
**Purpose**: Source of per-module thresholds the analyzer compares against.
**Responsibilities**: 1:1 key↔analyzer-module correspondence; hold the ratchet state (`kill_threshold` per module, `increment_step`, `target_final`).

### C2. `mutation_analyzer.py` (read-only this spec)
**Purpose**: Aggregates `mutmut results --all true` by path **segment 3** (`custom_components.ev_trip_planner.<segment3>`), emits gate `OK`/`NOK`.
**Constraint**: NOT modified (out of scope). Design works *around* its segment-3 aggregation by rebasing keys.

### C3. Targeted-run mechanism
**Purpose**: Fast per-iteration feedback without a full ~10-min run.
**Interface** (verified against installed mutmut 3.5.0): `mutmut run` accepts positional `[MUTANT_NAMES]...` which support glob patterns. A module-scoped run is:
```bash
.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.config_flow.*"
```
`paths_to_mutate` stays untouched (config-only, not a CLI flag); the positional glob is the targeted mechanism. For split packages, segment 3 is the package name, so `"custom_components.ev_trip_planner.trip.*"` re-runs the whole `trip` aggregate. Re-running mutants updates the same cache the analyzer reads — no config edit, no scoping file.

### C4. Ratchet mechanism
**Purpose**: Lock in progress; gate cannot regress.
**Interface**: after a module's measured rate ≥ its current `kill_threshold + increment_step` (0.01), raise that module's `kill_threshold` toward `target_final = 1.00`. Final state: every module `kill_threshold = 1.00`.

## Phase A — Tooling & Config Hardening (US-1, US-2, US-3)

### A.1 Verify the three make targets run clean (US-1)

| Target | Command | Pass signal | AC |
|---|---|---|---|
| `make mutation` | `.venv/bin/mutmut run --max-children=4` | exit 0, full run, runtime recorded (~9.7 min / 583 s baseline), 0 timeouts, `_other` bucket 0 | AC-1.1, AC-1.4, AC-1.5 |
| `make mutation-gate` | `mutation_analyzer.py . --gate` | gate table + JSON printed, no traceback | AC-1.2 |
| `make layer2` | gate + `weak_test_detector.py` + `diversity_metric.py` | all 3 sub-steps run, no error | AC-1.3 |

`_other`-bucket check (AC-1.5): grep `mutmut results --all true` for any line not matching `custom_components.ev_trip_planner.<seg>...`; expect 0. Timeout check (AC-1.4): grep for `: timeout`; expect 0.

**Authoritative baseline (binding for all of Phase A and Phase B)**: The per-module baseline table in `research.md` (overall 48.9%, `__init__` 51.5%, `trip` 46.8%, …) is **SUPERSEDED / stale** and MUST NOT be used for any decision. The **fresh full `make mutation` run executed in this step A.1 is the SOLE authoritative baseline** for every per-module kill rate, the worst-first ordering (B.1), the failing-module list (A.3), and the overall rate (B.6). Every specific per-module percentage quoted anywhere in this design — the A.3 figures (`__init__` ~32.5%, `trip` ~47.5%, `utils` ~86.1%), the B.1 worst-first ordering, the B.6 baseline row `57.1%` overall — is **"expected from prior runs — to be confirmed/replaced by the A.1 authoritative full run"** and carries no decision weight until that run replaces it. There is a known discrepancy for `__init__` (research.md reports 51.5%, requirements and design A.3 report ~32.5%); this is **resolved by the A.1 run**, whose number is authoritative. The design deliberately rests no decision on a number it does not trust — A.1 produces the trusted numbers, and B.1 references this statement for ordering.

### A.2 Threshold-rebasing plan (US-2)

The analyzer keys modules by **path segment 3**. Any pyproject key with a dot inside the module portion (`trip.manager`, `emhass.adapter`, …) can never match — the analyzer emits `trip`, `emhass`, etc. Every dotted key silently falls back to `global_kill_threshold`. `dashboard.*` keys are fully dead (`dashboard/` merged into `panel.py`).

**Authoritative mapping table** (analyzer-emitted name ↔ current pyproject key(s) ↔ corrected key ↔ source path):

| Analyzer-emitted module | Current pyproject key(s) | Action | Corrected key | Source path |
|---|---|---|---|---|
| `calculations` | `calculations.core/.windows/.power/.schedule/.deficit` (5 dotted) | collapse 5→1 | `calculations` | `custom_components/ev_trip_planner/calculations/` |
| `trip` | `trip.manager/.crud_mixin/.soc_mixin/.power_profile_mixin/.schedule_mixin` (5 dotted) | collapse 5→1 | `trip` | `custom_components/ev_trip_planner/trip/` |
| `emhass` | `emhass.adapter/.index_manager/.load_publisher/.error_handler/.cache_entry_builder` (5 dotted) | collapse 5→1 | `emhass` | `custom_components/ev_trip_planner/emhass/` |
| `services` | `services.handlers/._handler_factories/.cleanup/.dashboard_helpers/.presence/._lookup` (6 dotted) | collapse 6→1 | `services` | `custom_components/ev_trip_planner/services/` |
| `vehicle` | `vehicle.controller/.strategy/.external` (3 dotted) | collapse 3→1 | `vehicle` | `custom_components/ev_trip_planner/vehicle/` |
| `config_flow` | `config_flow` | keep | `config_flow` | `custom_components/ev_trip_planner/config_flow/` |
| `presence_monitor` | `presence_monitor` | keep | `presence_monitor` | `custom_components/ev_trip_planner/presence_monitor/` |
| `coordinator` | `coordinator` | keep | `coordinator` | `custom_components/ev_trip_planner/coordinator.py` |
| `panel` | `panel` | keep | `panel` | `custom_components/ev_trip_planner/panel.py` |
| `sensor` | `sensor` | keep | `sensor` | `custom_components/ev_trip_planner/sensor/` |
| `utils` | `utils` | keep | `utils` | `custom_components/ev_trip_planner/utils.py` |
| `definitions` | `definitions` | keep | `definitions` | `custom_components/ev_trip_planner/definitions.py` |
| `diagnostics` | `diagnostics` | keep | `diagnostics` | `custom_components/ev_trip_planner/diagnostics.py` |
| `yaml_trip_storage` | `yaml_trip_storage` | keep | `yaml_trip_storage` | `custom_components/ev_trip_planner/yaml_trip_storage.py` |
| `__init__` | `__init__` | keep | `__init__` | `custom_components/ev_trip_planner/__init__.py` |
| `const` | (none) | **ADD if analyzer emits it** | `const` | `custom_components/ev_trip_planner/const.py` |
| `frontend` | (none) | **ADD if analyzer emits it** | `frontend` | `custom_components/ev_trip_planner/frontend/` |
| — | `dashboard.importer/.builder/.template_manager` (3) | **DELETE (stale)** | — | merged into `panel.py` |

**Keys to remove**: 3 `dashboard.*` keys (FR-4, AC-2.1).
**Dotted keys to collapse**: 24 dotted keys → 5 top-level keys (`calculations`, `trip`, `emhass`, `services`, `vehicle`) (FR-5, AC-2.2).
**Keys to verify/add**: after the first full run in step A.1, list the *exact* module set the analyzer emits; add a key for every emitted module with no key (`const`, `frontend` likely), and delete any key with no emitted module (AC-2.3).

**Collapsed-key threshold rule (deterministic)**: when collapsing N dotted sub-module keys into one top-level key, the collapsed key's `kill_threshold` is set to **the module's true measured rate from the A.1 authoritative full run**. Because A.3 fixes the failing modules via real honest tests *before* the gate is declared green, and Phase B only ever ratchets thresholds upward, setting the collapsed threshold to the measured rate never lowers a real bar — NFR-2 is preserved.

After rebasing, every module the analyzer prints has exactly one matching key, and `make mutation-gate` reports each module against its own threshold (AC-2.4). The mapping table above is committed in `design.md` and echoed into `.progress.md` (AC-2.5, FR-13).

### A.3 Lock the gate green (US-3)

After A.2, the A.1 authoritative full run is expected to identify 3 failing modules: `__init__`, `trip`, `utils` (expected from prior runs `__init__` ~32.5%, `trip` ~47.5%, `utils` ~86.1% — *to be confirmed/replaced by the A.1 authoritative full run*; see A.1) measured below their **existing** thresholds (`__init__` 51, `trip` 48, `utils` 89).

**Decision (locked, interview #1)**: Phase A4 fixes `__init__`, `trip`, `utils` *first via real honest tests* so each module meets its **existing** 51/48/89 threshold — then the gate is `OK` (AC-3.1, AC-3.2, FR-7, FR-8). No threshold is lowered, no code is excluded, and no module's `kill_threshold` is rebased down to its measured rate to make the gate pass (AC-3.3, NFR-2) — verified by `git diff` of `pyproject.toml` `[tool.mutmut]` + `[tool.quality-gate.mutation]`. The ramp (Phase B) raises these modules further toward `1.00` only after they already meet 51/48/89.

## Phase B — Iterative Ramp Design (US-4)

### B.1 Worst-first module ordering

After Phase A's fresh full run, order modules ascending by measured kill rate. The ordering below is **expected from prior runs — to be confirmed/replaced by the A.1 authoritative full run** (see the Authoritative-baseline statement in A.1): `config_flow` (~31%) → `panel` (~38%) → `services` (~38%) → `sensor` (~39%) → `coordinator` (~38%) → `trip`/`emhass`/`presence_monitor` → `calculations` → `utils`/`diagnostics`/`definitions`. The *exact* order is fixed by the A.1 authoritative full-run numbers, never by the stale `research.md` baseline. Worst-first maximises overall-rate delta per iteration (a module with the most survivors moves the aggregate most).

### B.2 Per-iteration loop structure

Each iteration targets one module (or a small package). Steps:
1. **Measure**: `mutmut run --max-children=4 "custom_components.ev_trip_planner.<module>.*"` (targeted, fast).
2. **Enumerate survivors**: `mutmut results --all true | grep "<module>" | grep ": survived"`.
3. **Classify** each survivor (see Testability-refactor strategy + adjudication workflow).
4. **Improve**: strengthen weak test / dedupe / add new test / replace weak test / US-5 refactor (AC-4.3).
5. **Re-measure targeted**: re-run step 1 for that module; confirm module rate strictly up.
6. **Regression guard**: `make test` and `make test-cover` (`--cov-fail-under=100`) both green (AC-4.6, NFR-3).
7. **Ratchet**: raise that module's `kill_threshold` toward `1.00` (B.3).
8. **Record**: one-line What & Why in `chat.md` before verify (NFR-7); append delta row.

### B.3 Ratchet workflow (AC-4.5, FR-10)

After step 5 confirms a module's measured rate `r`:
- New `kill_threshold = min(r, target_final)` — i.e. ratchet up to the rate just achieved, never above `1.00`, never down (NFR-2).
- The `increment_step = 0.01` floor guarantees each iteration's ratchet is a real, ≥1-point move (the ratchet "is exercised, not just documented").
- Modules already at `1.00` measured get `kill_threshold = 1.00`.
- Ramp end-state: **every** module `kill_threshold = 1.00`, `status = "passing"`. `definitions` (loose 0.45 today, ~100% measured) is ratcheted to `1.00` per resolved Unresolved-Question.

### B.4 Gate checkpoints (decision #2)

Targeted runs give fast feedback but not the true overall aggregate. A **full `make mutation` (~10 min) + `make mutation-gate`** is run at each checkpoint to capture the exact overall delta. Checkpoint cadence: after every Phase-A completion, and after every N ramp iterations (N decided by task plan; recommended N=2–3 to bound the ~10-min cost). The final iteration always ends on a full-run checkpoint proving overall rate = `1.00`.

### B.5 Iteration entry / exit criteria

**Entry**: previous iteration's regression guard green; target module selected per worst-first order; survivor list freshly enumerated.
**Exit**: target module's measured kill rate strictly greater than at entry; `make test` + `make test-cover` green at 100%; module threshold ratcheted; delta row appended; What & Why logged. An iteration that raises a previously-unkillable mutant to killable via US-5 also counts (AC-4.3e).

### B.6 Per-iteration delta table format

Maintained in `.progress.md` (and mirrored in `chat.md`):

| Iter | Module(s) | Survivors before | Survivors after | Module rate before→after | Overall rate (last full run) | Improvement type(s) | Threshold ratcheted to |
|---|---|---|---|---|---|---|---|
| 0 (baseline) | — | — | — | — | A.1 authoritative full run (expected ~57.1% from prior runs — replaced by the A.1 number) | — | — |
| 1 | `__init__` | … | … | (A.1 measured)→… | (full-run @ checkpoint) | strengthened+new | … |
| … | … | … | … | … | … | … | … |
| N (final) | — | 0 | 0 | all 100% | **100.0%** | — | all 1.00 |

Overall rate must be **monotonically non-decreasing** and strictly increase across the ramp (AC-4.2); the final row shows `100.0%` (AC-4.4, FR-9).

## Testability-refactor Strategy (US-5)

### When a survivor needs a production refactor vs a stronger test

Decision rule applied per survivor:

| Symptom | Verdict |
|---|---|
| Mutated logic *is* exercised by a test, but the test asserts too little (return value, intermediate state) | **Stronger/new test** — no refactor |
| Logic is unreachable from any honest test because it is buried in an un-injected dependency, a closure capture, a private branch with no observable effect, or HA-framework glue with no seam | **US-5 refactor** — extract the logic to a pure, directly-callable function/method so a test can assert on it |
| Mutation has *no* behavioural difference at all (mathematically equivalent / intrinsic) even after a refactor exposing it | **NFR-1 adjudication** (last resort) |

### Refactor constraints (AC-5.2, AC-5.3, NFR-6)

- **API-preserving**: public entry points (HA entities, services, config-flow steps, `async_setup_entry`) keep the same signatures and behaviour.
- **Import-linter contracts hold**: `make import-check` / `lint-imports` green — the layered contract (`trip`/`emhass`/`dashboard` must not import `services`) is not violated by any extraction.
- **HA-observable behaviour unchanged**: no change to any entity state, service result, or config-flow outcome; `make test` proves it.
- Every refactor names, in `chat.md`, the specific mutant(s)/logic it makes testable (AC-5.1, FR-12). Typical pattern: extract a closure body or an inline branch into a module-level pure helper, then unit-test that helper directly.
- Source-inspection test exclusions (`test_solid_metrics`, `test_vehicle_controller_event`) MAY remain but MUST NOT be expanded (NFR-1).

## Pragma Policy (NFR-1, NFR-1b, NFR-11) — HUMAN-ESCALATED, REFERENCE-CLASS SCARCE

A `# pragma: no mutate` comment is **not** a routine tool in this spec. It is an emergency hatch reserved for mutants the broader testing community has documented as intrinsically unkillable. Reference class: PHP/Infection-style projects 10× the size of this codebase carry roughly 10 pragmas total, on functions whose untestability is well-understood (e.g. `__version__` constants, `break`-vs-`continue` performance optimisations where the loop terminates regardless, debug-only branches behind compile-time flags). The project-wide ceiling for THIS spec is the same order of magnitude: **~10 pragmas total**.

### Prior pragma audit (NFR-1b) — supersedes the historical ≥2-subagent workflow

The 118 pragmas labelled "verified not US-5 applicable" in iterations 13–18 were added through a ≥2-subagent workflow that did NOT include human escalation. That workflow is RETIRED. Those 118 pragmas are presumed removable and MUST be re-audited one by one:

| Prior label (presumed removable) | Default outcome | Real path to kill |
|---|---|---|
| "HA framework call args / glue" | Remove pragma, write integration test (NFR-9) | Drive real HA core via `pytest-homeassistant-custom-component`, assert on observable side effect (registered entity, panel id, schema-validated value). |
| "Log text / None-in-log" | Remove pragma, extract `_LOG_*` constants, multi-assert (NFR-8) + caplog | Helper function returns the constant, test asserts on the exact log line. |
| "default_value on `.get()`" | Remove pragma, refactor to pure helper (US-5) + assertion-dense unit test (NFR-8) | Pattern in `services/_helpers.py` — `get_str`, `get_str_fallback`, `get_str_nested`, `get_bool`, `get_vehicle_id`. Tests assert exact return for present, missing-with-default, missing-without-default. |
| "String case on encoding param" | Remove pragma, replace generic test data (NFR-10), assert on output | Use distinctive accented input (`"árbol"`, `"João"`) so a `"NFKD"`→`"nfkd"` mutation produces a different normalised output. |
| "Numeric constant in default" | Remove pragma, distinctive parametrised test (NFR-10) | Test the boundary value AND a value just inside/outside (so `100.0`→`101.0` swaps the truth of a `<=` check). |
| "Event dispatcher returning None" | Remove pragma, multi-assert on side effects (NFR-8) | Spy on the dispatcher; assert on event name + payload + count, not just "called once". |
| "Pure math intrinsic" | Likely keep, but ESCALATE to human first | Only after a documented attempt at boundary parametrisation fails. |

### Workflow for ANY pragma proposal (new or retained)

```mermaid
sequenceDiagram
    participant Dev as Executor
    participant H as Human
    participant Chat as chat.md
    participant Code as source / tests
    Dev->>Dev: US-5 helper extraction attempted
    Dev->>Dev: NFR-8 multi-assert strengthening attempted
    Dev->>Dev: NFR-9 integration test attempted
    Dev->>Dev: NFR-10 distinctive test data attempted
    Note over Dev: All four attempts must be DOCUMENTED in chat.md
    Dev->>Chat: Write dossier (mutant id, source, helpers tried, integration test outcome, data variants tried)
    Dev->>H: ESCALATE — request pragma approval
    H-->>Dev: APPROVE (with reasoning) | REJECT
    alt APPROVED in writing
        Dev->>Code: Add # pragma: no mutate to that one line
        Dev->>Chat: Append human approval verbatim
    else REJECTED
        Dev->>Dev: Pick a different US-5/US-6/US-7 strategy and retry
    end
```

### Hard rules (DoD #7, NFR-11)

1. **No pragma without human approval, in writing, in `chat.md`.** The ≥2-subagent procedure does NOT substitute for human approval — it has been retired for this spec.
2. **No pragma without a complete NFR-11 dossier** — every retained pragma carries: mutant id, original/mutated source, US-5 helper signature considered + why it failed, NFR-8 assertion strengthening attempted + why it failed, NFR-9 integration test attempted + why it failed, NFR-10 distinctive test data attempted + why it failed.
3. **No pragma on bad architecture.** A survivor caused by an un-injected dependency, a god-object, or a non-substitutable closure MUST be refactored (US-5) — not pragma'd.
4. **Pre-existing exclusions** (`test_solid_metrics`, `test_vehicle_controller_event`) MAY remain but MUST NOT be expanded.
5. **Project ceiling: ~10 pragmas.** If the count drifts above ~10 during the ramp, that is a signal to escalate the *strategy*, not to add more pragmas — likely a missing integration-test pattern or a refactor opportunity not yet attempted.

## Mutmut Best-Practice Compliance (Hovmöller 15 Rules)

Reference: mutmut official docs (`mutmut.readthedocs.io`) + Anders Hovmöller, *"Mutation testing in practice"* (kodare.net, 2016). Each rule, its mapping to this spec, and its status under the hot revision:

| # | Rule | Spec mapping | Status & action |
|---|---|---|---|
| 1 | `mutate_only_covered_lines = true` — only mutate executed lines | US-8 AC-8.1, NFR-13, FR-16 | **IMPLEMENTED**: set in `[tool.mutmut]` 2026-05-21. Post-tune re-baseline run (2026-05-21) could not complete full mutation evaluation due to Python 3.14 / bleak / dbus_fast dependency incompatibility in `pytest-homeassistant-custom-component`; config verified present. |
| 2 | `do_not_mutate` excludes tests, conftest, generated code | US-8 AC-8.3 | **IMPLEMENTED**: `paths_to_mutate` restricts to `custom_components/ev_trip_planner` — tests implicitly excluded. Explicit `do_not_mutate` key not needed (verified via mutmut 3.5.0 source). |
| 3 | `max_stack_depth` to keep tests localised | US-8 AC-8.2, NFR-13 | **IMPLEMENTED**: set to `8` in `[tool.mutmut]` 2026-05-21. Justification: covers HA's typical fixture→integration→module→helper chain (6–8 frames) without rewarding incidental transitive coverage. Full justification in chat.md. |
| 4 | `type_check_command` filters mutants invalid under types | (optional) | **DEFERRED**: project uses partial typing; adding `type_check_command` (e.g. `mypy`) would require mypy to pass on all mutants. Most mutants change string literals and default values — type signature mutations are rare. ROI unclear; defer unless mypy adoption increases. |
| 5 | Pragmas only for genuinely equivalent/intrinsic mutants | NFR-1, NFR-11, US-5, prior-audit table above | **ACTION**: re-audit 118 prior pragmas; remove all without complete NFR-11 dossier + human approval. |
| 6 | Loop: measure → classify → write test → re-run → revert mutation → confirm pass | B.2 per-iteration loop | **OK** for honest iterations; **ACTION**: the loop step "write a test to try to kill it" was previously skipped in favour of pragmas — re-enforced by NFR-8/9/10 and the iteration template. |
| 7 | US-5 refactor (testability) BEFORE pragma | US-5, NFR-11 | **ACTION**: every retained-pragma proposal documents the US-5 attempt; refactor first, pragma last. |
| 8 | Formal adjudication for each pragma | NFR-1 (human escalation) | **ACTION**: human escalation is now the adjudication; ≥2-subagent procedure retired. |
| 9 | Strong tests that assert observable effects, not stubs | US-6, NFR-8 | **ACTION**: assertion-density audit per module; multi-attribute asserts on dict/dataclass/dispatched-call returns. |
| 10 | 100% line coverage before measuring kill rate | NFR-3, AC-4.6 | **OK**: `make test-cover --cov-fail-under=100` already enforced. |
| 11 | Integration tests with real framework for glue code | US-7, NFR-9 | **ACTION**: each HA-glue-dominated module grows an integration test using `pytest-homeassistant-custom-component`. |
| 12 | Granular per-module targeting | B.1, C3 (positional mutmut globs) | **OK**: targeted runs in place via positional globs. |
| 13 | No pragma-as-shortcut — write a test or refactor | NFR-1, NFR-1b, NFR-11 | **ACTION**: 118 prior pragmas re-audited under this rule. |
| 14 | Kill rate monotonically non-decreasing | AC-4.2 | **OK** for honest moves; **WATCH**: pragma removals may locally *drop* the kill rate before refactor/test work pushes it back up — this is acceptable so long as the iteration ends above its entry rate. |
| 15 | Classify survivors: (a) weak test, (b) untestable structure, (c) intrinsic/equivalent, (d) bad architectural design | US-5 testability strategy table | **ACTION**: classification re-applied per module with the new strategies (NFR-8/9/10), so very few survivors land in (c) and none in (d) without a refactor. |

A re-audit of this table runs at every gate checkpoint and at every iteration's "Measure + classify" sub-task.

## Multi-Attribute Assertion Pattern (US-6, NFR-8)

The single highest-leverage move available in this spec is to strengthen the assertions on tests that *already exercise* a surviving mutant. One test with N relevant assertions kills N mutants the same test previously left alive — no new test files, no fixture churn.

### Decision tree for a survivor whose corresponding test exists

```dot
digraph multi_assert {
    "Survivor X exercised by test T?" [shape=diamond];
    "Test T asserts every relevant attribute of return/state/call?" [shape=diamond];
    "Strengthen T (add asserts)" [shape=box];
    "Survivor X in callee not asserted by T" [shape=diamond];
    "Add direct test for callee" [shape=box];
    "Apply NFR-9 integration test" [shape=box];

    "Survivor X exercised by test T?" -> "Test T asserts every relevant attribute of return/state/call?" [label="yes"];
    "Survivor X exercised by test T?" -> "Survivor X in callee not asserted by T" [label="no"];
    "Test T asserts every relevant attribute of return/state/call?" -> "Strengthen T (add asserts)" [label="no → cheapest fix"];
    "Test T asserts every relevant attribute of return/state/call?" -> "Apply NFR-9 integration test" [label="yes → try integration"];
    "Survivor X in callee not asserted by T" -> "Add direct test for callee" [label="yes"];
}
```

### Concrete strengthening patterns

| Return shape | Weak pattern (1–2 asserts, leaves mutants) | Strong pattern (multi-assert, kills more mutants) |
|---|---|---|
| `dict` | `assert result["status"] == "ok"` | `assert result == {"status": "ok", "vehicle_id": "tesla-3", "trip_id": "T-42", "soc": 73.5, "deadline": expected_iso}` — every key relevant to the function's contract |
| `dataclass` | `assert obj.id == "x"` | `assert obj == ExpectedTrip(id="x", description="commute", soc=73.5, hora_regreso=time(18, 30), deficit_hours=2.0)` — equality on the full dataclass when applicable |
| dispatched call (`hass.services.async_call`) | `mock.assert_called_once()` | `mock.assert_called_once_with("trip", "create", {"vehicle_id": "tesla-3", "description": "commute", "soc": 73.5}, blocking=True)` |
| log emission | `assert "LOAD" in caplog.text` | `assert _LOG_DEFERRABLE_LOAD_PUBLISHED in caplog.text` *and* asserts on the interpolated `vehicle_id`/`load_id` values |
| iterable | `assert len(items) == 3` | `assert items == [Trip(id="A", soc=10), Trip(id="B", soc=20), Trip(id="C", soc=30)]` — pinning order *and* every field |

### Where to look for cheap wins

Per module audit during "Measure + classify" sub-task:
1. List survivors.
2. Run `mutmut tests-for-mutant <id>` for each survivor.
3. Diff the existing test against the function under test — count the number of attributes the test fails to assert.
4. Rank survivors by "smallest assertion-density delta closes the kill" and strengthen those first.

## Integration-First Strategy for HA Glue (US-7, NFR-9)

Modules with ≥30% of survivors classified as "framework call args" or "schema defaults" have a structural test-quality problem that pure unit tests cannot reach: the mocked framework absorbs the mutation. The fix is **driving the real HA core through `pytest-homeassistant-custom-component`** and asserting on the HA-side observable effect.

### Integration-test bias by module class

| Module class | Symptoms | Integration-test seam |
|---|---|---|
| `config_flow/*` | Voluptuous schema-default mutations survive; "form key not asserted" | Walk the real `async_step_user`/`async_step_init` flow; submit valid and edge-case inputs; assert on the persisted `config_entry.data` / `options` dict. |
| `services/*` | `hass.services.async_call(...)` arg mutations survive | Register the integration in a real test `hass`; call the service; assert on `hass.states.async_get(...)` and on the persisted trip/vehicle state. |
| `panel.py` | `async_register_panel(...)` kwargs mutations survive | Register the integration; query `frontend.async_get_panels(hass)`; assert on every panel kwarg (sidebar title, icon, module_url, embed_iframe, require_admin). |
| `sensor/*` | Entity attribute mutations survive | Setup the integration; query the entity registry and `hass.states`; assert on `state`, `attributes`, `unique_id`, `device_class`, `state_class`, `unit_of_measurement`. |
| `__init__.py` | Lifecycle hook mutations survive | Exercise `async_setup_entry` + `async_unload_entry` against a real `hass`; assert on hass.data domain contents before/after. |
| `coordinator.py` | `update_interval` and refresh-call mutations survive | Run real coordinator with a freezer-controlled clock; assert on `last_update_success`, `data` shape, and that `update_interval == timedelta(seconds=30)` exactly. |
| `presence_monitor/*` | State-change listener mutations survive | Fire real `hass.bus.async_fire`/state-change events; assert on the observable side effect (entity updated, log emitted, notification dispatched). |

### Where mocks remain (and how to use them safely)

Mocks remain only where the mock call *is* the outcome and no HA-side observable exists — e.g. an external HTTP call to an upstream service. Even there, NFR-8 still applies: the mock assertion checks every relevant arg.

## Distinctive Test Data Strategy (NFR-10)

Generic defaults (`""`, `0`, `1`, `None`, `True`) are silent enablers of survivors. A mutation that swaps `data.get("vehicle_id", "")` to `data.get("vehicle_id", "XX")` survives if the test sets `vehicle_id = ""` because both branches return `""`. The fix is choosing distinctive values:

| Domain | Generic (leaks mutants) | Distinctive (kills mutants) |
|---|---|---|
| Vehicle id | `""`, `"v1"` | `"tesla-model-3"`, `"renault-zoe-2024"` |
| Trip id | `"t1"` | `"trip-monday-commute-7am"` |
| SOC | `0`, `100` | `73.5`, `42.7` (avoid round 0/100 boundaries that interact with default-value mutations) |
| Time | `time(0,0)` | `time(18, 30)` (avoid midnight default) |
| Strings to be normalised | `"abc"` | `"árbol"`, `"João"` (ensures `NFKD`/`ascii` mutations show up) |
| Booleans | `True` as default | Explicitly pass `True` AND `False` as parametrised cases |
| Lists | `[]` | `[Trip("A"), Trip("B")]` — distinguishable elements with order pinned |

Each iteration's "Improve" sub-task includes a quick scan: `grep` the changed tests for generic literals and replace them where they hide mutants.

## SOLID / DRY / KISS Refactor Constraints (NFR-12)

All US-5 refactors honour:

- **SRP**: extracted helpers do one thing — read a key from a dict with a default, build a URL path, normalise a string. One input shape, one return shape.
- **DRY**: helpers live in a shared `_helpers.py` per package (`services/_helpers.py` already exists; extend the pattern to `trip/_helpers.py`, `emhass/_helpers.py` as needed). No per-file copies.
- **KISS**: no premature abstraction — three similar lines is fine; introduce a helper when the 4th call site arrives, or when extracting a helper *enables a test* that was previously infeasible.
- **OCP/LSP/ISP/DIP** stay implicit: helpers are pure functions; substitution is trivial; the import-linter contracts hold.

The helper's existence MUST enable at least one new assertion-dense unit test. A helper extracted without a corresponding test is a refactor without justification (AC-5.1) and is rejected.

## Technical Decisions

| Decision | Options Considered | Choice | Rationale |
|---|---|---|---|
| Fix segment-3 key mismatch | (a) modify analyzer to gate per sub-module; (b) rebase pyproject keys to top-level names | (b) rebase keys | Analyzer change is explicitly out of scope (req. Assumptions); rebasing is config-only, low-risk, and matches what the analyzer already emits. |
| Targeted-run mechanism | (a) temporary `paths_to_mutate` scoping file; (b) `mutmut run <MUTANT_NAMES>` glob | (b) positional glob | Verified in installed mutmut 3.5.0: `mutmut run` accepts `[MUTANT_NAMES]...` with globs. No config mutation, no race with the shared cache, reversible. |
| Re-measure cadence | (a) full run every iteration; (b) targeted per iteration + full at checkpoints | (b) | Full run is ~10 min; targeted run on one module is seconds-to-minutes. Checkpoints still give the exact overall delta (interview #2). |
| Module ordering | (a) by survivor count; (b) by kill rate ascending (worst-first); (c) by LOC | (b) worst-first by rate | Locked interview #1. Lowest-rate modules have most headroom; moves the aggregate fastest and front-loads risk. |
| Failing-module strategy in Phase A | (a) rebase thresholds down to measured; (b) fix via tests first | (b) fix first | Locked interview #1: `__init__`/`trip`/`utils` fixed by real tests before the gate is declared green — no threshold lowered (AC-3.3, NFR-2). |
| 100% for equivalent mutants | (a) accept <100%; (b) `≥2`-subagent adjudicated `# pragma: no mutate` | (b) | Locked interview #3/#4 + NFR-1: the only honest path to a literal 100% when a mutant is provably equivalent. |
| Collapsed-key threshold value | (a) max of merged; (b) lowest of merged thresholds; (c) module's true measured rate from the A.1 authoritative full run | (c) true measured rate | Single deterministic rule: the collapsed key's `kill_threshold` = the module's A.1-measured rate. Max could raise a sub-module's bar above its real rate and fail the gate spuriously; "lowest of merged" is ambiguous when sub-module thresholds diverge. Measured rate is unambiguous; since A.3 fixes failing modules via real tests first and Phase B only ratchets upward, it never lowers a real bar (NFR-2). |

## File Structure

| File | Action | Phase | Purpose |
|---|---|---|---|
| `pyproject.toml` | Modify | A | Remove 3 `dashboard.*` keys; collapse 24 dotted keys → 5 top-level keys; add `const`/`frontend` keys if analyzer emits them; ratchet `kill_threshold`s during Phase B; final `target_final`-aligned values. |
| `specs/mutation-score-ramp/design.md` | Create | A | This document — mapping table + ramp design. |
| `specs/mutation-score-ramp/.progress.md` | Modify | A+B | Append mapping table, baseline, per-iteration delta table, learnings. |
| `specs/mutation-score-ramp/chat.md` | Create/Modify | B | One-line What & Why per iteration (NFR-7); refactor justifications (AC-5.1); adjudication logs (NFR-1). |
| `tests/unit/**`, `tests/integration/**` | Modify/Create | A+B | Strengthen/dedupe/add/replace tests per iteration (AC-4.3). Files chosen per module under ramp. |
| `custom_components/ev_trip_planner/**` | Modify | B (only as needed) | US-5 testability refactors — API-preserving, justified in `chat.md`. May be zero files if all survivors are killable by tests alone. |
| `specs/mutation-score-ramp/.ralph-state.json` | Modify | A | Set `awaitingApproval = true` at end of design phase. |

**Create**: 2 (`design.md`, `chat.md`).
**Modify**: `pyproject.toml`, `.progress.md`, `.ralph-state.json`, plus an iteration-determined set of test files and (only where required) production files.

## Error Handling & Failure Modes

| Failure mode | Detection | Handling |
|---|---|---|
| mutmut timeout regression | `mutmut results --all true` shows `: timeout` lines (baseline 0) | Investigate the slow mutant; if a new test introduced an unbounded path, fix the test. NFR-5 = 0 timeouts. Escalate if intrinsic. |
| `_other` bucket non-zero | grep for lines not matching `custom_components.ev_trip_planner.<seg>...` | A new/renamed source path the analyzer's regex misses → reconcile the mapping table; if a true regex gap, escalate (analyzer change is out of scope). |
| Module whose survivors resist both tests and refactor | Iteration cannot raise module rate after honest effort | Enter NFR-1 adjudication; if the adjudicated set is large, escalate for a scope decision (possible tooling/architecture gap). |
| Full-run time exceeds ~15 min (NFR-4) | Wall-clock of `make mutation` at a checkpoint | Escalate (NFR-4 breach). Mitigations to propose: higher `--max-children`, lower per-mutant `timeout` from 600 s — but only as an escalated scope decision, not silently. |
| Gate `NOK` after a rebase | `make mutation-gate` exit 1 | Expected before ramp completes; only a *blocking* failure if a key still mismatches (module falls back to global) — re-check the 1:1 mapping. |
| Coverage drops below 100% | `make test-cover` `--cov-fail-under=100` fails | Iteration's exit criterion not met; fix tests before ratcheting (NFR-3). |
| Import-linter contract broken by a refactor | `make import-check` / `lint-imports` fails | Revert/redo the extraction so the layered contract holds (NFR-6). |

## Test Strategy

> This spec's "tests" are the project's pytest suite plus the mutation harness itself. The mutation kill rate *is* the test-quality metric. There is no new product code with its own unit tests; the deliverable is stronger tests + a correct gate.

### Test Double Policy

| Type | Use in this spec |
|---|---|
| **Stub** | Existing HA fixtures that stub `hass`, config entries, external HTTP — kept; new tests should assert on *real* observable effects, not just that a stub was reached. |
| **Fake** | In-memory HA test harness (`pytest-homeassistant-custom-component`) — used for integration-level tests where a real HA core object is needed. |
| **Mock** | Only where the *interaction* is the observable outcome (e.g. a service call dispatched, a coordinator refresh triggered). Over-mocking is the documented root cause of survivors — minimise. |
| **Fixture** | `conftest.py` fixtures providing known config-entry / trip / vehicle state — extend as needed for new strong tests. |

### Mock Boundary

| Component | Unit test | Integration test | Rationale |
|---|---|---|---|
| `mutation_analyzer.py` (gate) | Real (run against real cache) | Real | Verifying it via `make mutation-gate` — no doubles; it is the harness under test. |
| `pyproject.toml` mutation config | Real (parsed by analyzer) | Real | Correctness verified by gate output, not in isolation. |
| Production modules under ramp (`config_flow`, `trip`, `services`, …) | Real logic; Stub only true external I/O (HTTP, HA core internals) | Fake HA core | Survivors are mostly *caused* by mocks hiding behaviour — new tests assert real return values/state. |
| HA framework registration glue (`panel.async_register_panel`, schema defaults) | Mock only where the call itself is the outcome; else US-5-refactor to expose logic | Fake HA core | Decision #3: framework glue is not auto-unkillable; refactor or assert observable effect first. |

### Fixtures & Test Data

| Component | Required state | Form |
|---|---|---|
| Ramp executor (each iteration) | Populated mutmut cache from a prior `mutmut run` | Produced by `make mutation` / targeted run |
| `mutation-gate` verification | `pyproject.toml` with rebased 1:1 keys | The config file itself (C1) |
| New strong tests for `config_flow` | Valid + invalid config-entry input, generated schema | `conftest.py` factory / inline constants |
| New strong tests for `trip`/`services` | Trip with known SOC/line items, vehicle, tenant/entry | Existing `conftest.py` factories, extended |
| Adjudication | Mutant id + `mutmut show`/`tests-for-mutant` output | Captured into `chat.md` |

### Test Coverage Table

| Component / Mechanism | Test type | What to assert | Test double |
|---|---|---|---|
| `make mutation` | integration | Exit 0, full run, 0 timeouts, `_other` = 0, runtime ≤ ~15 min | none |
| `make mutation-gate` | integration | Prints gate table + JSON, no traceback; final run prints `RESULT: ✅ OK` | none |
| `make layer2` | integration | gate + weak-test detector + diversity metric all run, no error | none |
| pyproject mutation config | integration | Every analyzer-emitted module has exactly one key; no orphan key; no `dashboard.*` key | none |
| Each ramp iteration | integration | Target module measured kill rate strictly increased vs entry | none |
| Regression guard per iteration | unit+integration | `make test` green; `make test-cover` exit 0 at 100% coverage | existing HA fixtures |
| Production refactors (US-5) | unit+integration | `make test` green; `lint-imports` green; HA-observable behaviour unchanged | Fake HA core |
| Final state | integration | Overall kill rate JSON `== 1.0`; every module `kill_rate == 1.00` vs threshold `1.00` | none |
| NFR-1 adjudications | manual | Each `# pragma: no mutate` traces to a logged ≥2-subagent approval in `chat.md` | none |

### Test File Conventions

Discovered from the repo:
- **Test runner**: `pytest` 9.x (`.venv/bin/python -m pytest`), `asyncio_mode = auto`.
- **Test location**: `tests/unit/` and `tests/integration/`; `python_files = test_*.py`.
- **Unit command**: `make test` → `pytest tests/unit tests/integration -v --tb=short`.
- **Coverage command**: `make test-cover` → adds `--cov=custom_components.ev_trip_planner --cov-fail-under=100`.
- **Mutation commands**: `make mutation` (full), `mutmut run "custom_components.ev_trip_planner.<module>.*"` (targeted), `make mutation-gate`, `make layer2`.
- **E2E**: `tests/e2e/*.spec.ts` (Playwright) — exists but unrelated to this spec; not run here.
- **Mock cleanup**: pytest fixtures with function scope (`asyncio_default_fixture_loop_scope = function`); HA fixtures auto-teardown.
- **Markers**: `unit`, `integration`, `slow`, `mutmut_skip` — `mutmut_skip` MUST NOT be newly applied (NFR-1).
- **Pre-existing mutmut exclusions** (`-k "not test_solid_metrics and not test_vehicle_controller_event"`): may remain, must not be expanded.

## Traceability

| Req | Design element |
|---|---|
| US-1 / FR-1,2,3 / AC-1.1–1.5 | Phase A.1 verification table; error-handling `_other`/timeout rows |
| US-2 / FR-4,5,6,13 / AC-2.1–2.5 | Phase A.2 mapping table; C1; technical decision "Fix segment-3 mismatch" |
| US-3 / FR-7,8 / AC-3.1–3.3 | Phase A.3; decision "Failing-module strategy"; NFR-2 git-diff check |
| US-4 / FR-9,10,11 / AC-4.1–4.6 | Phase B.1–B.6; C3, C4; delta table format |
| US-5 / FR-12 / AC-5.1–5.3 | Testability-refactor Strategy; NFR-6 constraints |
| NFR-1 | Adjudication workflow; decision "100% for equivalent mutants" |
| NFR-2 | Decisions "Failing-module strategy", "Collapsed-key threshold value"; git-diff verification |
| NFR-3 | B.2 step 6; B.5 exit criteria; Test Coverage "Regression guard" row |
| NFR-4 | Error-handling "Full-run time exceeds ~15 min" row; B.4 checkpoint cost note |
| NFR-5 | Error-handling "mutmut timeout regression" row; A.1 timeout check |
| NFR-6 | Testability-refactor constraints; import-linter contract handling |
| NFR-7 | B.2 step 8; chat.md in File Structure |

## Unresolved Questions

- Whether the analyzer emits `const` and `frontend` as their own segment-3 modules is confirmed only after Phase A.1's full run; the mapping table is finalised then (handled, not blocking).
- The number of ramp iterations is unbounded and decided by the tasks phase (per requirements); design supports any count.
- The proportion of mutants needing the NFR-1 escape hatch is unknown until the ramp runs; minimised by mandatory US-5-first.

## Implementation Steps

Phases A and most of B are complete (149/159 tasks). The steps below cover the remaining work and the **hot revision** introduced 2026-05-21.

1. **A.1** — DONE. Run `make mutation` (record runtime, timeouts, `_other` count); run `make mutation-gate` and `make layer2`; confirm all exit cleanly (AC-1.x).
2. **A.2** — DONE. Capture the exact analyzer-emitted module set; rewrite `[tool.quality-gate.mutation.modules.*]`: delete 3 `dashboard.*` keys, collapse 24 dotted keys → 5 top-level keys, add any missing key; verify 1:1 correspondence (AC-2.x).
3. **A.3** — DONE. Ramp-iterate `__init__`, `trip`, `utils` with honest tests until each meets its threshold; confirm `make mutation-gate` = `OK` without lowering any threshold (AC-3.x).
4. **B (loop, iters 1–18)** — DONE for the iterations recorded in `.progress.md` / `task_review.md`.
5. **B′ (tooling hot revision, NEW)** — Tune `[tool.mutmut]` per Hovmöller rules 1–3 (NFR-13, US-8): set `mutate_only_covered_lines = true`, choose and justify an explicit `max_stack_depth`; rerun a full `make mutation` to record the **post-tune authoritative re-baseline** (AC-8.4). Previous per-module counts/ratios remain in `.progress.md` as history; iteration B″ targets the new numbers.
6. **B″ (pragma re-audit + real-kill ramp, NEW)** — For each below-100% module (currently 11 of 15) and for every existing pragma:
   - **Strengthen first (US-6 / NFR-8)** — audit existing tests that already exercise the survivor; add multi-attribute asserts on every relevant return/state/call key. Cheapest move, biggest leverage.
   - **Integration test for HA glue (US-7 / NFR-9)** — for modules with ≥30% glue-classified survivors, add at least one `pytest-homeassistant-custom-component`-backed test asserting on HA-side observable effect.
   - **Refactor for testability (US-5 / NFR-12)** — extract pure helpers under SOLID/DRY/KISS; tests on the helpers assertion-dense.
   - **Distinctive data (NFR-10)** — replace generic `""`/`0`/`None` test inputs with distinguishing values where they hide mutants.
   - **Re-audit pragmas (NFR-1b)** — for every existing pragma in the file under iteration, decide: (a) test it out (preferred), (b) refactor + test (US-5), or (c) escalate to the human (NFR-1) with the full NFR-11 dossier.
   - Re-measure targeted; run `make test` + `make test-cover` (100%); ratchet threshold upward (never down).
7. **B″ (checkpoints)** — Every N iterations: full `make mutation` + `make mutation-gate`; append overall-rate delta row; re-audit the Hovmöller 15-rule table.
8. **Pragma proposal flow** — Whenever the executor proposes a pragma (existing-to-retain or new-to-add): produce the NFR-11 dossier in `chat.md`; ESCALATE to the human; await written approval; only then add (or retain) the pragma. The ≥2-subagent procedure is RETIRED — it does NOT replace human approval.
9. **Final** — Confirm gate `OK`, overall kill rate `1.00`, every module threshold `1.00`; remaining pragmas number in the single digits with full NFR-11 dossiers and human approval; finalise delta table and mapping table in `.progress.md`; mark prior-iteration history clearly versus the post-revision ramp.

<!-- Changelog 2026-05-18: initial design.md for mutation-score-ramp — Phase A tooling/config hardening + green gate, Phase B worst-first ramp to 100%, targeted-run via mutmut positional globs, ratchet to 1.00, ≥2-subagent NFR-1 adjudication. -->
<!-- Changelog 2026-05-18: fixed spec-reviewer findings #9/#10/#13 — removed the rejected threshold-rebase-down narrative from A.3; added the A.1 authoritative-baseline statement marking research.md per-module figures stale and all quoted percentages as to-be-confirmed; made the collapsed-key threshold rule a single deterministic rule (A.1 true measured rate) in both A.2 and the Technical Decisions table. -->
<!-- Changelog 2026-05-21 (HOT REVISION, no progress reset): supersedes the ≥2-subagent pragma path. Pragma policy is now HUMAN-ESCALATED and reference-class scarce (~10 project-wide ceiling, à la PHP/Infection). New section "Mutmut Best-Practice Compliance (Hovmöller 15 Rules)" maps each rule to a spec requirement. New "Multi-Attribute Assertion Pattern (US-6, NFR-8)" guides strengthening existing tests as the cheapest kill-rate lever. New "Integration-First Strategy for HA Glue (US-7, NFR-9)" prescribes `pytest-homeassistant-custom-component`-backed tests for config_flow/services/panel/sensor/__init__/coordinator/presence_monitor. New "Distinctive Test Data Strategy (NFR-10)" eliminates generic-default mutant hides. New "SOLID / DRY / KISS Refactor Constraints (NFR-12)" governs US-5 helper shape and placement. Implementation Steps re-numbered with the B′ (tooling tune) and B″ (re-audit + real-kill ramp) phases. Prior 118 "verified not US-5 applicable" pragmas are presumed removable under NFR-1b and must be re-audited one by one with human escalation. -->

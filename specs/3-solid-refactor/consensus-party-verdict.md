---
name: consensus-party-verdict
description: BMAD Consensus Party final verdict on remaining SOLID and antipattern violations after deterministic quality-gate checks
metadata:
  type: semantic
  created: 2026-05-12
---

# BMAD Consensus Party — Final Verdict

**Date:** 2026-05-12
**Spec:** 3-solid-refactor
**Purpose:** Evaluate whether remaining Tier A SOLID/antipattern violations are real problems or acceptable design trade-offs

## Method

BMAD Consensus Party (Iteration 2) with 4 agents:
- **Winston** 🏗️ — System Architect (distributed systems, patterns)
- **Amelia** 👩‍💻 — Senior Developer (code quality, refactoring)
- **Murat** 🧪 — Master Test Architect (testing, code metrics)
- **John** 📋 — Product Manager (pragmatism, user impact)

## Final Verdict Table

| # | Violation | Tier A | Tier B Verdict | Action |
|---|-----------|--------|----------------|--------|
| 1 | EMHASSAdapter 18 public methods | FAIL | **FALSE POS** (4/4) — facade pattern | Document with `# qg-accepted:` |
| 2 | VehicleController 9 public methods | FAIL | **FALSE POS** (4/4) — facade + strategy | Document with `# qg-accepted:` |
| 3 | PresenceMonitor 11 public methods | FAIL | **PARTIAL** — some thin wrappers worth trimming | Low priority, fix when natural |
| 4 | AP01: FlowHandler 650 LOC (>500) | FAIL | **PARTIAL** — accept trade-off for now | Fix now: extract entity scanning |
| 5 | AP07: EMHASSAdapter 27 attrs, PresenceMonitor 29 attrs | FAIL | **LIKELY FALSE POS** — composition-based | Document with `# qg-accepted:` |
| 6 | AP08: 8 methods with arity >5 | FAIL | **PARTIAL** — only 1 genuinely problematic | Fix now: bundle params |
| 7 | AP12: 4 dead abstract base classes | FAIL | **CONFIRM** (4/4) — truly unused | Fix now: delete |
| 8 | AP13: 23 classes with delegation_ratio >0.8 | FAIL | **FALSE POS** (4/4) — facade pattern | Document with `# qg-accepted:` |
| 9 | AP18: Branch explosion (7+ if-elif) | FAIL | **PARTIAL** — acceptable until more events added | Fix now: dict dispatch |
| 10 | AP22: 59 bare `# pragma: no cover` | FAIL | **CONFIRM** (4/4) — maintenance liability | Fix now: add reason= |
| 11 | AP23: Duplicate code (importer vs __init__) | FAIL | **FALSE POS** (4/4) — standard Python re-export | Document with `# qg-accepted:` |

## Clear FALSE POSITIVE (4 items — no action, just document)

1. **EMHASSAdapter 18 methods** — Legitimate facade delegating to IndexManager, LoadPublisher, ErrorHandler. Public method count on a facade is not a SOLID violation.
2. **VehicleController 9 methods** — Facade with strategy pattern for vehicle charging control. Method count matches external interface, not internal complexity.
3. **AP13 (high delegation ratio >0.8)** — By definition, a facade has high delegation. This is the intended architecture.
4. **AP23 (duplicate code)** — `dashboard/__init__.py` uses standard Python re-export pattern (`from .importer import X` + `__all__`). Not code duplication.

## Clear CONFIRM (2 items — fix immediately)

1. **AP12: 4 dead abstract base classes** in `dashboard/_base.py`:
   - `DashboardComponentProtocol` — unused
   - `DashboardImporterProtocol` — unused
   - `DashboardStorageStrategy` — unused
   - `DashboardTemplateStrategy` — unused

2. **AP22: ~23 bare `# pragma: no cover`** in `template_manager.py` without `reason=` or explanatory comment. The other ~36 have inline comments but the 23 bare ones need proper annotation.

## PARTIAL — Fix now (2 items)

1. **AP08: High arity — only `_populate_per_trip_cache_entry`** (11 params, 5 are unused test-compatibility dummies). Bundle params into a dataclass.
2. **AP18: Branch explosion in _sensor_callbacks.py:143** with 7+ if-elif branches for event dispatch. Replace with dict-dispatch map.

## Accept as-is — Fix now (1 item)

1. **AP01: EVTripPlannerFlowHandler at 650 LOC**. Extract entity scanning logic into a dedicated `config_flow/_entities.py` module. 650 LOC is manageable but not ideal.

## Low priority

1. **PresenceMonitor 11 methods** — Has thin wrapper methods. Trim when refactoring is natural.

## Key Decision

Per SKILL.md Tier A vs Tier B conflict resolution:
> "When Tier A (deterministic AST) reports a violation but Tier B (BMAD consensus) says it is a FALSE POSITIVE, Tier B wins."

False positives are documented with `# qg-accepted:` comments adjacent to the flagged elements per SKILL.md line 301.

## False Positive Documentation Locations

| False Positive | Source File | Line | qg-accepted marker |
|----------------|-------------|------|-------------------|
| EMHASSAdapter 18 methods | `emhass/adapter.py` | 22 | Yes |
| VehicleController 9 methods | `vehicle/controller.py` | 67 | Yes |
| AP07 EMHASSAdapter attrs | `emhass/adapter.py` | 22 | Yes |
| AP13 high delegation | `emhass/adapter.py` | 22 | Yes |
| AP13 high delegation | `vehicle/controller.py` | 67 | Yes |
| AP13 high delegation | `presence_monitor/__init__.py` | 47 | Yes |
| AP23 duplicate code | `dashboard/__init__.py` | — | Yes |

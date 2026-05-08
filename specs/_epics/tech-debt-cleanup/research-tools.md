# Tech Debt Cleanup — Tools, Skills & Scripts Assessment

**Date:** 2026-05-08
**Epic:** tech-debt-cleanup

---

## 1. Layer 1: Test Execution — Tools

| Tool | Installed? | Version | Status | Notes |
|------|-----------|---------|--------|-------|
| pytest | Yes | 7.4+ | Working | Core test runner |
| pytest-cov | Yes | 7.0.0 | Working | Coverage reporting |
| mutmut | Yes | 3.5.0 | Working | Mutation testing |
| Playwright (E2E) | Yes | Latest | Working | E2E test framework |

**Baseline metrics** (from `mutation_analyzer.py` run on 2026-05-08):
- Overall kill rate: **49%** (7,593 killed / 15,511 mutants)
- 17 source modules analyzed
- Tests: 1,755 passed (1 known pre-existing failure)
- Coverage: 100% configured (via `--cov-fail-under=100`)

**Per-module mutation scores** (from pyproject.toml quality-gate config, latest mutmut run):

| Module | Score | Threshold | Status |
|--------|-------|-----------|--------|
| definitions | 100% | 45% | PASSING |
| diagnostics | 93% | 28% | PASSING |
| utils | 89% | 89% | PASSING |
| calculations | 72% | 71% | PASSING |
| vehicle_controller | 55% | 55% | PASSING |
| emhass_adapter | 53% | 53% | PASSING |
| presence_monitor | 52% | 52% | PASSING |
| schedule_monitor | 50% | 50% | PASSING |
| yaml_trip_storage | 51% | 50% | PASSING |
| __init__ | 52% | 51% | IN PROGRESS |
| trip_manager | 47% | 46% | IN PROGRESS |
| dashboard | 35% | 35% | IN PROGRESS |
| services | 38% | 38% | IN PROGRESS |
| config_flow | 31% | 31% | IN PROGRESS |
| coordinator | 38% | 37% | IN PROGRESS |
| sensor | 39% | 38% | IN PROGRESS |
| panel | 38% | 37% | IN PROGRESS |

---

## 2. Layer 2: Test Quality — Tools

| Script | Location | Status | Notes |
|--------|----------|--------|-------|
| weak_test_detector.py | `.agents/skills/quality-gate/scripts/` | Available | Detects A1-A8 weak test patterns |
| mutation_analyzer.py | `.agents/skills/quality-gate/scripts/` | Available | Kill-map, gate mode, per-module |
| diversity_metric.py | `.agents/skills/quality-gate/scripts/` | Available | Levenshtein edit distance |

All Layer 2 scripts are available and importable. The weak_test_detector has a known caveat: high false-positive rate for tests using pytest fixtures for implicit verification (1,704 weak tests flagged in last gate).

---

## 3. Layer 3: Code Quality — Tools

| Tool | Installed? | Version | Status | Notes |
|------|-----------|---------|--------|-------|
| ruff | Yes | 0.15.9 | Working | Linting + format check |
| pylint | Yes | 4.0.5 | Working | Score: 10.00/10 (1 new C0200 warning) |
| mypy | Yes | 1.20.0 | **BROKEN** | Fails on `homeassistant` stubs: `Type statement only supported in Python 3.12+` (running Python 3.14) |
| pyright | Yes | 1.1.409 | Available | 32 pre-existing HA Entity override errors |
| black | Yes | 26.3.1 | Working | Formatting |
| isort | Yes | 8.0.1 | Working | Import sorting |

### Critical Issue: mypy is broken
mypy fails with a Python 3.14 syntax incompatibility in `homeassistant` package stubs. This blocks the `make mypy` target entirely.

**Workaround:** Use pyright instead (already installed) or skip mypy until the HA stubs are updated.

### Ruff lint status: PASSING (2 minor warnings in last gate, now fixed)

---

## 4. Layer 4: Security & Defense — Tools

| Tool | Priority | Installed? | Status |
|------|----------|-----------|--------|
| bandit | Required | **NO** | Missing |
| safety / pip-audit | Required | **NO** | Missing |
| gitleaks | Required | **NO** | Missing |
| semgrep | Recommended | **NO** | Missing |
| checkov | Recommended | **NO** | Missing |
| deptry | Recommended | **NO** | Missing |
| vulture | Recommended | **NO** | Missing |
| trivy | Optional | **NO** | Missing |

**All 8 Layer 4 security tools are MISSING.** The quality-gate skill is designed to run all of them, but none are installed in the virtual environment or system PATH.

---

## 5. Available Skills (Relevant to Quality/Testing)

### Fully Available & Configured
| Skill | Location | Description |
|-------|----------|-------------|
| `quality-gate` | `.agents/skills/quality-gate/` | 5-layer gate (L3A smoke test, L1 tests, L2 quality, L3B BMAD, L4 security) with 9+ scripts |
| `quality-gate` | `.github/skills/quality-gate/` | Simpler 3-layer variant |
| `quality-gate` | `.claude/skills/quality-gate/` | Another variant |
| `python-testing-patterns` | `.agents/skills/` (symlink) | Python testing best practices |
| `python-security-scanner` | `.agents/skills/` (symlink) | Python vulnerability detection guidance |
| `home-assistant-best-practices` | `.agents/skills/` (symlink) | HA automation/dashboard patterns |
| `python-performance` | `.agents/skills/` (symlink) | Python performance optimization |

### NOT Found
| Skill | Expected Location | Status |
|-------|-------------------|--------|
| `mutation-testing` | `.claude/skills/` or `.agents/skills/` | **NOT FOUND** (skill referenced in quality-gate but not installed) |
| `mutation-gate` | `.agents/skills/` | **NOT FOUND** |
| `simplify` | `.agents/skills/` | **NOT FOUND** |

---

## 6. Makefile Targets

| Target | Command | Status |
|--------|---------|--------|
| `make test` | pytest | Working |
| `make test-cover` | pytest --cov | Working |
| `make test-verbose` | pytest -vv -s | Working |
| `make lint` | ruff + pylint | Working (pylint 1 C0200 warning) |
| `make mypy` | mypy | **BROKEN** (HA stubs Python 3.14 issue) |
| `make format` | black + isort | Working |
| `make check` | test + lint + mypy | **Blocks on mypy** |
| `make e2e` | run-e2e.sh | Available |
| `make e2e-soc` | run-e2e-soc.sh | Available (SOC capping suite) |
| **`make quality-gate`** | N/A | **MISSING target** |
| **`make mutation`** | N/A | **MISSING target** |

---

## 7. CI/CD

| File | Status |
|------|--------|
| `.github/workflows/python-tests.yml` | Runs pytest only (no mutation, no coverage, no lint) |
| `.github/workflows/playwright.yml.disabled` | DISABLED |

CI is minimal: only pytest with verbose output. No mutation testing, no coverage gates, no linting, no E2E.

---

## 8. Plans & Documentation

| Document | Location | Status |
|----------|----------|--------|
| `quality-gate-iterative-architecture.md` | `plans/` | Comprehensive 4-option analysis, recommends Option D (hybrid with L3A smoke test) |
| `mutation-testing-guide.md` | `plans/` | Basic mutmut workflow guide |
| `mutation-quality-gate.md` | `plans/` | Mutation gate concept |
| `quality-gate-latest.json` | `_bmad-output/quality-gate/` | Last gate: FAIL (1 test failure + 2 ruff errors) |

---

## 9. Gap Analysis

### Missing Tools (Must Install)
1. **bandit** (`pip install bandit`) — Required by quality-gate L4
2. **safety** or **pip-audit** (`pip install safety` or `pip install pip-audit`) — Required by L4
3. **gitleaks** (`brew install gitleaks` or binary download) — Required by L4
4. **semgrep** (`pip install semgrep` or binary) — Recommended L4, has custom HA rules
5. **checkov** (`pip install checkov`) — Recommended L4
6. **deptry** (`pip install deptry`) — Recommended L4
7. **vulture** (`pip install vulture`) — Recommended L4

### Broken Tools (Need Fix)
1. **mypy** — Python 3.14 incompatibility with HA stubs. Fix: upgrade HA or pin Python version, or skip mypy and rely on pyright.

### Missing Makefile Targets
1. **`make quality-gate`** — No orchestrator target exists for the 5-layer quality gate
2. **`make mutation`** — No shortcut for `mutmut run`
3. **`make quality-gate-iterative`** — Planned in `quality-gate-iterative-architecture.md` but never implemented

### Missing Skills
1. **`mutation-testing`** — Referenced by quality-gate skill but not installed
2. **`mutation-gate`** — Listed in available skills but files not found on disk
3. **`simplify`** — Listed in available skills but files not found on disk

### CI/CD Gaps
1. No mutation testing in CI
2. No coverage gates in CI
3. No linting in CI
4. Playwright workflow is disabled
5. No quality-gate automation

---

## 10. Recommendations (Order of Priority)

### Before Starting Cleanup — Must Do
1. **Install Layer 4 security tools** (bandit, gitleaks, pip-audit, semgrep)
   - These are required by the quality-gate skill and needed for a complete assessment
   - Estimated effort: 30 min total
2. **Fix mypy breakage** — Either pin Python to 3.12/3.13 or switch to pyright-only typing
3. **Add `make quality-gate` target** — Orchestrate the 5-layer pipeline from quality-gate skill

### Should Do Before Major Cleanup
4. **Add mutation testing to CI** — `mutmut run --no-run` + threshold check
5. **Enable Playwright CI workflow** — Currently disabled
6. **Add coverage gates to CI** — `--cov-fail-under=100`
7. **Install mutation-testing skill** — Referenced but not present

### Can Do Incrementally
8. Add `make mutation` shortcut for quick mutation score checks
9. Implement `quality-gate-iterative` target as planned in `plans/quality-gate-iterative-architecture.md` (Option D architecture)
10. Add security scanning to CI pipeline

---

## 11. Current State Summary

The project has a **robust quality-gate infrastructure** (skills, scripts, pyproject.toml configuration, iterative architecture plan) but is missing the **runtime tools** to execute it. The core test/mutation/quality tools (pytest, mutmut, ruff, pylint, black, isort) are installed and working. The security scanning layer (Layer 4) is entirely absent. CI is minimal and misses most quality checks. The biggest blockers to immediate progress are the mypy breakage and the missing Layer 4 tools.

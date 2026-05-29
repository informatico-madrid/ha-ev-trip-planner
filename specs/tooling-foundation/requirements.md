# Requirements: Tooling Foundation

## Goal

Install missing security and quality tools, migrate from mypy to pyright, create a comprehensive quality gate Makefile target, establish baseline metrics, and update CI—all while maintaining backward compatibility with existing development workflows.

---

## User Stories

### US-1: Security Vulnerability Detection
**As a** developer
**I want to** run security scans that detect secrets, vulnerabilities, and anti-patterns
**So that** I can catch security issues before they reach production

**Acceptance Criteria:**
- [x] AC-1: `make security-bandit` runs Bandit against custom_components/ and exits with proper status code
- [x] AC-2: `make security-audit` runs pip-audit and reports dependency vulnerabilities
- [x] AC-3: `make security-gitleaks` detects secrets in git history (gitleaks binary installed)
- [x] AC-4: Semgrep installed with custom rules for HA-specific anti-patterns (unsafe yaml.load, eval)

### US-2: Type Checker Migration
**As a** developer
**I want to** use pyright instead of mypy for type checking
**So that** I get faster, more accurate type analysis compatible with Python 3.14

**Acceptance Criteria:**
- [x] AC-5: pyproject.toml `[tool.mypy]` section removed entirely, `[tool.pyright]` added with Python 3.14 target
- [x] AC-6: `make typecheck` runs pyright (not mypy); `make mypy` deprecated with warning
- [x] AC-7: `make check` calls `typecheck` instead of `mypy`

### US-3: Quality Gate Orchestration
**As a** developer
**I want to** run a single command that validates all quality dimensions
**So that** I get immediate feedback on code health before committing

**Acceptance Criteria:**
- [x] AC-8: `make quality-gate` runs 4 layers in sequence (fail-fast): Layer 1 (Test: `make test`), Layer 2 (Test Quality: mutation_analyzer.py --gate), Layer 3 (Code Quality: lint, typecheck, deptry, vulture), Layer 4 (Security: bandit, semgrep)

### US-4: Dead Code and Import Consistency
**As a** developer
**I want to** detect dead code and import inconsistencies
**So that** I can keep the codebase maintainable and catch unused dependencies

**Acceptance Criteria:**
- [x] AC-12: deptry installed and configured (excludes tests, ignores DEP003)
- [x] AC-13: vulture installed and configured (80% confidence, excludes tests)

### US-5: Mutation Testing Shortcut
**As a** developer
**I want to** run mutation testing with a simple Makefile target
**So that** I can verify test effectiveness without remembering mutmut syntax

**Acceptance Criteria:**
- [x] AC-11: `make mutation` runs `mutmut run --until=100`; results integrate with quality-gate thresholds in pyproject.toml

### US-6: E2E Suite Extensibility
**As a** developer
**I want to** add new E2E test suites without modifying the quality gate
**So that** I can test different aspects of the system independently

**Acceptance Criteria:**
- [x] AC-8.1: E2E suite pattern defined: `{suite-name}`.
- [x] AC-8.2: Layer 1 auto-discovers all `e2e-*` targets via Makefile wildcard pattern
- [x] AC-8.3: Adding a new E2E suite (e.g., `e2e-charging`) requires no changes to quality-gate targets
- [x] AC-8.4: `make layer1` runs all E2E suites; `make layer1-ci` excludes all E2E suites

### US-7: Backward Compatibility
**As a** developer
**I want to** existing Makefile targets to continue working
**So that** my muscle memory and CI scripts don't break

**Acceptance Criteria:**
- [x] AC-9: All existing targets work identically: `make test`, `make lint`, `make format`
  - **E2E suites**: All E2E targets must continue working:
    - Standard suite: `make e2e`
    - SOC suite: `make e2e-soc`
    - Future suites: Follow pattern `e2e-{suite-name}`

### US-8: CI/CD Integration
**As a** maintainer
**I want to** CI to run the same quality gate as developers
**So that** PRs are automatically validated

**Acceptance Criteria:**
- [x] AC-10: .github/workflows/python-tests.yml updated with pyright (replaces mypy), security scan (bandit, semgrep), import consistency check (deptry), and runs on Python 3.14

### US-9: TypeScript Tooling
**As a** developer writing E2E tests
**I want to** TypeScript type checking and linting
**So that** I catch type errors in E2E tests before runtime

**Acceptance Criteria:**
- [x] AC-11: .eslintrc.json extends "plugin:@typescript-eslint/recommended", package.json includes "typecheck": "tsc --noEmit" script, and tsc/eslint configured for tests/e2e/*.ts files

### US-10: Baseline Metrics
**As a** tech lead
**I want to** capture baseline quality metrics before improvements
**So that** I can measure progress over time

**Acceptance Criteria:**
- [x] AC-12: `make quality-baseline` creates _bmad-output/quality-gate/baseline/ directory with snapshots across 3 layers:
  - **Layer 1 (Test Execution)**: pytest, coverage, mutation_analyzer.py --gate, mutation kill-map, make e2e
  - **Layer 2 (Test Quality)**: weak_test_detector.py (A1-A8 rules), diversity_metric.py
  - **Layer 3 (Code Quality)**: ruff, pyright, solid_metrics.py (Tier A AST), llm_solid_judge.py (Tier B LLM context), principles_checker.py (DRY/KISS/YAGNI/LoD/CoI), antipattern_checker.py (Tier A 25 patterns AST), antipattern_judge.py (Tier B 25 patterns LLM context)
  - All outputs timestamped in subdirectory, with `latest/` symlink for easy comparison

### US-11: Additional Quality Tools
**As a** developer
**I want to** additional tools for code quality and CI performance
**So that** I can prevent regressions and speed up testing

**Acceptance Criteria:**
- [x] AC-13: import-linter installed (prevents circular imports post-refactoring)
- [x] AC-14: pre-commit installed with hooks (ruff, pyright, bandit, deptry)
- [x] AC-15: pytest-randomly installed (catches hidden inter-test dependencies)
- [x] AC-16: pytest-xdist installed (parallel test execution, 3-5x CI speedup)
- [x] AC-17: refurb installed (Python modernization suggestions)

---

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Install bandit security linter | High | AC-1.1 |
| FR-2 | Install pip-audit dependency scanner | High | AC-1.2 |
| FR-3 | Install gitleaks binary for secret detection | High | AC-1.3 |
| FR-4 | Install semgrep static analyzer | High | AC-1.4 |
| FR-5 | Install pyright type checker | High | AC-2.1, AC-2.2 |
| FR-6 | Remove mypy configuration and target | High | AC-2.1, AC-2.3, AC-2.4 |
| FR-7 | Create Makefile security targets | High | AC-1.1, AC-1.2, AC-1.3, AC-1.5 |
| FR-8 | Create Makefile typecheck target (pyright) | High | AC-2.3 |
| FR-9 | Create Makefile mutation target | High | AC-5.1 |
| FR-10 | Create Makefile quality-gate target | High | AC-3.1 - AC-3.6 |
| FR-11 | Create Makefile quality-baseline target | High | AC-9.1, AC-9.2 |
| FR-12 | Install deptry import consistency checker | Medium | AC-4.1 |
| FR-13 | Install vulture dead code detector | Medium | AC-4.2 |
| FR-14 | Update .eslintrc.json for TypeScript | Medium | AC-8.1 |
| FR-15 | Add TypeScript scripts to package.json | Medium | AC-8.2 |
| FR-16 | Update pyproject.toml version to 3.14 | High | AC-2.2 |
| FR-17 | Update CI workflow with quality gates | High | AC-7.1 - AC-7.4 |
| FR-18 | Update documentation references (mypy→pyright) | Medium | AC-2.1 - AC-2.5 |
| FR-19 | Verify all existing Makefile targets work | Critical | AC-9.1 - AC-9.5 |
| FR-20 | Run antipattern_checker.py baseline | Medium | AC-12.3 |
| FR-21 | Install import-linter | Medium | AC-13 |
| FR-22 | Install pre-commit | Medium | AC-14 |
| FR-23 | Install pytest-randomly | Medium | AC-15 |
| FR-24 | Install pytest-xdist | Medium | AC-16 |
| FR-25 | Install refurb | Medium | AC-17 |
| FR-26 | Define E2E suite naming pattern | High | AC-8.1 |
| FR-27 | Layer 1 auto-discovers E2E suites | High | AC-8.2 |
| FR-28 | New E2E suites require no gate changes | High | AC-8.3 |
| FR-29 | layer1-ci excludes all E2E suites | High | AC-8.4 |

---

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Type checker performance | Time for full typecheck | < 30 seconds |
| NFR-2 | Quality gate performance | Total execution time | < 5 minutes |
| NFR-3 | Tool compatibility | Python version | 3.14 (matching CI) |
| NFR-4 | Security scan reliability | False positive rate | < 5% (config tuned for HA patterns) |
| NFR-5 | Backward compatibility | Breaking changes to existing targets | 0 |
| NFR-6 | Documentation completeness | All new targets documented in `make help` | 100% |
| NFR-7 | CI parity | CI uses same commands as local dev | 100% |

---

## Verification Contract

**Project type**: `fullstack`

**Entry points**:
- `make security`, `make security-bandit`, `make security-audit`, `make security-gitleaks`, `make security-semgrep`
- `make typecheck`, `make mutation`, `make quality-gate`, `make quality-baseline`
- `make test`, `make lint`, `make format`, `make check`, `make e2e` (existing)
- CLI: `bandit`, `pip-audit`, `gitleaks`, `semgrep`, `pyright`, `deptry`, `vulture`, `mutmut`
- CI: `.github/workflows/python-tests.yml`

**Observable signals**:
- **PASS looks like**:
  - `make typecheck`: Exit code 0, pyright reports "0 errors" in summary
  - `make security-bandit`: Exit code 0, "No issues identified"
  - `make quality-gate`: Each layer prints "=== Layer N: ===" and final "=== Quality Gate PASSED ==="
  - `make check`: All three sub-commands (test, lint, typecheck) complete without error
  - CI job: green checkmark, all steps pass

- **FAIL looks like**:
  - `make typecheck`: Exit code 1, pyright prints error with file:line:column
  - `make security-bandit`: Exit code 1, prints issue severity (LOW/MEDIUM/HIGH) with CWE link
  - `make quality-gate`: Stops at failing layer, prints which layer failed
  - `make check`: Stops at first failing sub-command, prints which one failed
  - CI job: red X, step logs show which check failed

**Hard invariants**:
- Existing `make test`, `make lint`, `make format`, `make e2e`, `make e2e-soc` MUST work identically (AC-6)
- `make check` MUST run the same checks (test + lint + typecheck), just with pyright instead of mypy
- CI MUST use Python 3.14 (not 3.11 or 3.12)
- _bmad-output/ MUST be in .gitignore (prevents committing generated files)
- pyproject.toml `[tool.mypy]` section MUST be completely removed (no partial migration)

**Seed data**:
- Python 3.14 virtual environment at `.venv/`
- Existing tests in `tests/` directory (pytest-based)
- Existing E2E tests in `tests/e2e/*.ts` and `tests/e2e-dynamic-soc` (Playwright/TypeScript)
- Custom component code in `custom_components/ev_trip_planner/`
- Existing quality-gate configuration in pyproject.toml `[tool.quality-gate.mutation]`

**Dependency map**:
- **Epic**: tech-debt-cleanup
- **Shared state**: pyproject.toml, Makefile (global project tools)
- **No conflicting specs**: None (this is foundation work, other specs build on it)

**Escalate if**:
- `make typecheck` takes > 60 seconds (indicates misconfiguration)
- Existing targets break after changes (AC-6 failure)
- gitleaks binary installation fails (binary install may need sudo)
- CI fails but local passes (environment skew)
- pyright reports > 100 type errors (likely configuration issue, not real problems)

---

## Glossary

| Term | Definition |
|------|------------|
| **bandit** | Python security linter that finds common security issues (hardcoded passwords, SQL injection, etc.) |
| **pip-audit** | CLI tool that scans Python dependencies for known vulnerabilities (CVEs) |
| **gitleaks** | Secret scanner that searches git history for API keys, tokens, passwords |
| **semgrep** | Static analysis tool supporting multiple languages with customizable rules |
| **pyright** | Microsoft's type checker for Python (faster, more accurate than mypy) |
| **mypy** | Legacy Python type checker being replaced by pyright |
| **deptry** | Tool that detects missing, unused, or transitive dependencies in Python projects |
| **vulture** | Tool that finds unused/dead code in Python (complements test coverage) |
| **mutmut** | Mutation testing tool for Python that modifies code to verify test effectiveness |
| **quality gate** | Orchestration target that runs all quality checks in layers, failing fast if any fail |
| **mutation kill rate** | Percentage of mutants (code changes) that tests detect; higher = better tests |
| **fail-fast** | Stop execution immediately when any step fails (vs. continue and report all errors) |

---

## Out of Scope

- **Fixing existing type errors**: Installing pyright will likely reveal new type errors; fixing those is separate work
- **Fixing existing security issues**: bandit/semgrep may find vulnerabilities; remediation is separate work
- **Removing dead code**: vulture will identify dead code; removal is separate work
- **Achieving 100% mutation score**: Baseline documentation only; improving scores is Spec 1 work
- **Test code quality**: Quality gate excludes tests/ from some checks (bandit, deptry, vulture)
- **tests/ha-manual/**: **OBSOLETE** - Not part of quality gate, confirmed unused and unreliable. This directory is a relic from before E2E automation existed. Use `make e2e` and `make e2e-soc` for E2E testing instead.
- **Performance optimization**: Quality gate may be slow; optimization is future work
- **Custom Semgrep rules**: Only basic HA-specific rules (yaml.load, eval); comprehensive rulepack is separate work

---

## Dependencies

### Prerequisites
- Python 3.14 installed and available as `python3`
- Existing `.venv/` virtual environment
- `make` installed
- `git` installed
- `node` and `npm` installed (for TypeScript tooling)
- sudo access (for gitleaks binary installation to /usr/local/bin/)

### External Dependencies
- PyPI packages: bandit, pip-audit, semgrep, deptry, vulture, pyright, mutmut
- GitHub release: gitleaks binary (zadduk/gitleaks or gitleaks/gitleaks)
- npm packages: @typescript-eslint/parser, @typescript-eslint/eslint-plugin (already installed)

### Related Specs
- **Spec 1 (Mutation Testing)**: Depends on quality-gate thresholds in pyproject.toml
- **Spec 3 (Post-Spec Validation)**: Uses deptry output to verify import consistency

---

## Success Criteria

1. All 17 ACs pass (AC-1 through AC-17) plus 4 E2E extensibility ACs (AC-8.1 through AC-8.4)
2. `make quality-gate` completes in < 5 minutes on fresh checkout
3. No existing Makefile targets break (AC-9 verified, including all E2E suites)
4. CI passes with new quality checks
5. Baseline metrics documented for future comparison
6. Developer onboarding docs updated (copilot-instructions.md reflects pyright, not mypy)

---

## Acceptance Criteria Mapping

| AC | Mapped To | Status |
|----|-----------|--------|
| AC-1: make security-bandit | FR-1, FR-7 | ✅ Complete |
| AC-2: make security-audit | FR-2, FR-7 | ✅ Complete |
| AC-3: make security-gitleaks | FR-3, FR-7 | ✅ Complete |
| AC-4: semgrep installed | FR-4, FR-7 | ✅ Complete |
| AC-5: pyproject.toml mypy→pyright | FR-5, FR-6 | ✅ Complete |
| AC-6: make typecheck (pyright) | FR-8 | ✅ Complete |
| AC-7: make check updated | FR-6, FR-19 | ✅ Complete |
| AC-8.1: E2E suite pattern defined | FR-26 | ✅ Complete |
| AC-8.2: Layer 1 auto-discovers E2E suites | FR-27 | ✅ Complete |
| AC-8.3: New E2E suites need no gate changes | FR-28 | ✅ Complete |
| AC-8.4: layer1-ci excludes all E2E | FR-29 | ✅ Complete |
| AC-9: existing targets work (all E2E suites) | FR-19 | ✅ Complete |
| AC-10: CI workflow updated | FR-17 | ✅ Complete |
| AC-11: make mutation shortcut | FR-9 | ✅ Complete |
| AC-12: deptry installed | FR-12 | ✅ Complete |
| AC-13: vulture installed | FR-13 | ✅ Complete |
| AC-14: TS tooling (tsc, ESLint) | FR-14, FR-15 | ✅ Complete |
| AC-15: _bmad-output/ in .gitignore | **Already Done** | ✅ Complete |
| AC-16: quality-baseline snapshot | FR-11, FR-20 | ✅ Complete |
| AC-17: import-linter installed | FR-21 | ✅ Complete |
| AC-18: pre-commit installed | FR-22 | ✅ Complete |
| AC-19: pytest-randomly installed | FR-23 | ✅ Complete |
| AC-20: pytest-xdist installed | FR-24 | ✅ Complete |
| AC-21: refurb installed | FR-25 | ✅ Complete |

---

## Unresolved Questions

- **gitleaks installation method**: Research recommends binary install to /usr/local/bin/ (requires sudo). Alternative: download to project-local bin/ and add to PATH? Decision: Use system binary for consistency with other tools.
- **pip-audit vs safety**: Research chose pip-audit. Any reason to prefer safety? Decision: pip-audit is maintained by PyPA (Python Packaging Authority), more authoritative.
- **Semgrep ruleset**: Basic rules defined (yaml.load, eval). Should we add more HA-specific patterns? Decision: Start minimal, expand in future work.
- **Quality gate in CI**: Should quality-gate replace existing test job, or run in parallel? Decision: Add to existing python-tests.yml for now, separate workflow later if needed.

---

## Next Steps

1. Create tasks.md from requirements (Task Generation phase)
2. Verify AC-9 baseline: Run all existing Makefile targets and document current behavior
3. Install Python tools via pip to .venv/
4. Install gitleaks binary to /usr/local/bin/ (requires sudo)
5. Update pyproject.toml (remove mypy, add pyright/bandit/deptry/vulture configs)
6. Create .gitleaks.toml and .semgrep.yml
7. Update .eslintrc.json (add extends)
8. Update Makefile (new targets, update existing targets, update help)
9. Verify AC-9: Re-run all existing targets to confirm no breakage
10. Create _bmad-output/quality-gate/ directory
11. Run `make quality-baseline` to capture initial state
12. Run antipattern_checker.py and document findings
13. Update .github/workflows/python-tests.yml
14. Update .github/copilot-instructions.md (mypy → pyright references)
15. Update .vscode/settings.json if needed
16. Set awaitingApproval=true and await user signoff

<!-- Changed: Initial requirements creation — all user stories, FRs, NFRs, and verification contract defined -->

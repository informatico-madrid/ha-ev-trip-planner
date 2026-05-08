# Tasks: Tooling Foundation

**Total task count**: 18

**Phase breakdown**:
- Phase 1 (POC - Make It Work): 8 tasks
- Phase 2 (Refactoring): 2 tasks
- Phase 3 (Testing): 2 tasks
- Phase 4 (Quality Gates): 4 tasks (added documentation update)
- Phase 5 (PR Lifecycle): 2 tasks (added cleanup task)

---

## Phase 1: Make It Work (POC)

**Goal**: Install all tools, create configuration files, add Makefile targets, and prove they work end-to-end.

- [x] 1.1 Install Python quality and security tools
  - **Do**: Install all pip packages in single command: bandit[toml], pip-audit, semgrep, deptry, vulture, pyright, import-linter, refurb, pytest-randomly, pytest-xdist, pre-commit
  - **Files**: requirements_dev.txt
  - **Done when**: All packages installed in .venv/, `which bandit pip-audit semgrep deptry vulture pyright` all return paths
  - **Verify**: `.venv/bin/bandit --version && .venv/bin/pip-audit --version && .venv/bin/semgrep --version && .venv/bin/deptry --version && .venv/bin/vulture --version && .venv/bin/pyright --version`
  - **Commit**: `chore(dev): install security and quality tools via pip`
  - _Requirements: FR-1, FR-2, FR-4, FR-5, FR-12, FR-13, FR-21, FR-22, FR-23, FR-24, FR-25_
  - _Design: Tool Installation Strategy_

- [x] 1.2 Update requirements_dev.txt with new tools
  - **Do**: Add bandit[toml], pip-audit, semgrep, deptry, vulture, pyright-nodecli, import-linter, refurb, pytest-randomly, pytest-xdist, pre-commit; remove mypy line
  - **Files**: requirements_dev.txt
  - **Done when**: File updated with new tools, mypy removed
  - **Verify**: `grep -E "bandit|pip-audit|semgrep|deptry|vulture|pyright|import-linter|refurb|pytest-randomly|pytest-xdist|pre-commit" requirements_dev.txt && ! grep mypy requirements_dev.txt`
  - **Commit**: `chore(dev): update requirements_dev.txt with quality tools`
  - _Requirements: FR-1, FR-2, FR-4, FR-5, FR-6, FR-12, FR-13, FR-16, FR-21, FR-22, FR-23, FR-24, FR-25_
  - _Design: Python Tooling Dependencies_

- [x] 1.3 Install gitleaks binary system-wide
  - **Do**: Download gitleaks 8.18.4 for linux x64, extract to /usr/local/bin/ with sudo (using SUDO_PASS env var), verify installation
  - **Files**: /usr/local/bin/gitleaks (system binary)
  - **Commands**:
    ```bash
    wget -q https://github.com/gitleaks/gitleaks/releases/download/v8.18.4/gitleaks_8.18.4_linux_x64.tar.gz -O /tmp/gitleaks.tar.gz
    tar -xzf /tmp/gitleaks.tar.gz -C /tmp/
    echo "$SUDO_PASS" | sudo -S mv /tmp/gitleaks /usr/local/bin/
    rm /tmp/gitleaks.tar.gz
    ```
  - **Done when**: `gitleaks --version` outputs version 8.18.4 or higher
  - **Verify**: `gitleaks --version | grep -q "gitleaks version"`
  - **Commit**: `chore(security): install gitleaks binary for secret detection`
  - _Requirements: FR-3_
  - _Design: Secret Detection Tooling_

  **Sudo constraint note**: Uses `echo "$SUDO_PASS" | sudo -S` for non-interactive sudo. **ONLY gitleaks installation requires sudo**—all other tools use pip (no sudo needed). For containerized/CI environments without sudo, task 2.2's `scripts/install-tools.sh` should include alternative installation logic (e.g., download to project-local `bin/` directory and add to PATH).

- [x] 1.4 [P] Create .gitleaks.toml configuration
  - **Do**: Create config with allowlist for tests/, .venv/, node_modules/, _bmad-output/ directories
  - **Files**: .gitleaks.toml
  - **Done when**: File exists with extendDefault=true and allowlist paths
  - **Verify**: `cat .gitleaks.toml | grep -q "extendDefault"`
  - **Commit**: `config(security): add gitleaks configuration`
  - _Requirements: FR-3_
  - _Design: Secret Detection Configuration_

- [x] 1.5 [P] Create .semgrep.yml configuration
  - **Do**: Create rules for HA-specific anti-patterns (yaml.load, eval)
  - **Files**: .semgrep.yml
  - **Done when**: File exists with ha-unsafe-yaml-load and ha-dangerous-eval rules
  - **Verify**: `cat .semgrep.yml | grep -q "ha-unsafe-yaml-load"`
  - **Commit**: `config(security): add semgrep rules for HA patterns`
  - _Requirements: FR-4_
  - _Design: Static Analysis Rules_

- [x] 1.6 Update pyproject.toml: remove mypy, add new tool configs
  - **Do**: Remove [tool.mypy] section entirely; add [tool.pyright] with Python 3.14 target; add [tool.bandit], [tool.deptry], [tool.vulture], [tool.import-linter]; update pylint py-version to 3.14
  - **Files**: pyproject.toml
  - **Done when**: No [tool.mypy] in file; [tool.pyright] exists with pythonVersion="3.14"; pylint py-version="3.14"
  - **Verify**: `! grep -q "\[tool.mypy\]" pyproject.toml && grep -q "\[tool.pyright\]" pyproject.toml && grep 'py-version = "3.14"' pyproject.toml`
  - **Commit**: `config(python): migrate from mypy to pyright, add quality tool configs`
  - _Requirements: FR-5, FR-6, FR-14, FR-16, FR-18_
  - _Design: Python Project Configuration_

- [x] 1.7 Update .eslintrc.json with TypeScript extends
  - **Do**: Add `"extends": ["eslint:recommended", "plugin:@typescript-eslint/recommended"]` to existing config
  - **Files**: .eslintrc.json
  - **Done when**: extends array includes @typescript-eslint/recommended
  - **Verify**: `cat .eslintrc.json | grep -q "@typescript-eslint/recommended"`
  - **Commit**: `config(typescript): add TypeScript ESLint recommended rules`
  - _Requirements: FR-14, FR-15_
  - _Design: TypeScript Linting Configuration_

- [x] 1.8 POC Checkpoint: Verify all tools run successfully
  - **Do**: Run each tool to prove installation works: bandit (dry run), pip-audit, semgrep (version), deptry (version), vulture (version), pyright (version), gitleaks (version)
  - **Files**: None (verification only)
  - **Done when**: All tools execute without error
  - **Verify**: `.venv/bin/bandit --version && .venv/bin/pip-audit --version && .venv/bin/semgrep --version && .venv/bin/deptry --version && .venv/bin/vulture --version && .venv/bin/pyright --version && gitleaks --version && echo POC_TOOLS_PASS`
  - **Commit**: `chore(poc): verify all quality tools installed and functional`
  - _Requirements: FR-1, FR-2, FR-3, FR-4, FR-5_
  - _Design: Tool Installation Validation_

---

## Phase 2: Refactoring

**Goal**: Build Makefile orchestration layer with clean architecture, maintain backward compatibility.

- [x] 2.1 Create Makefile targets: layers, security, typecheck, quality-gate
  - **Do**: Add .PHONY targets for layer1, layer1-ci, layer2, layer3, layer4; quality-gate, quality-gate-ci; security-bandit, security-audit, security-gitleaks, security-semgrep; typecheck (pyright); dead-code, unused-deps, import-check, refurb; test-parallel, test-random; e2e-lint; pre-commit-install, pre-commit-run, pre-commit-update; quality-baseline. Update mypy target to run pyright with deprecation warning. Update check target to use typecheck. Add bilingual help text for all new targets.

    **E2E auto-discovery**: layer1 target uses wildcard pattern `e2e-%` to auto-discover E2E suite targets. This integrates with existing `e2e` and `e2e-soc` targets. Headed/debug variants (e2e-debug, e2e-headed) are NOT auto-discovered—only the base suite names are valid for layer1. This satisfies FR-27 (auto-discovery) and FR-29 (layer1-ci excludes E2E).
  - **Files**: Makefile
  - **Done when**: All new targets defined; layer1 auto-discovers e2e-% targets via wildcard pattern; mypy target shows warning; help includes all targets
  - **Verify**: `grep -q "^layer1:" Makefile && grep -q "^quality-gate:" Makefile && grep -q "^typecheck:" Makefile && make help | grep -q "typecheck"`
  - **Commit**: `feat(makefile): add quality gate layers and security targets`
  - _Requirements: FR-7, FR-8, FR-9, FR-10, FR-11, FR-17, FR-19, FR-20, FR-26, FR-27, FR-28, FR-29_
  - _Design: Makefile Orchestration Layer, E2E Suite Auto-Discovery_

- [x] 2.2 Create scripts and directory structure
  - **Do**: Create scripts/install-tools.sh (pip installs + gitleaks download), scripts/quality-baseline.sh (snapshot all metrics), _bmad-output/quality-gate/baseline/ directory
  - **Files**: scripts/install-tools.sh, scripts/quality-baseline.sh, _bmad-output/quality-gate/baseline/
  - **Done when**: Scripts executable, directory exists
  - **Verify**: `test -x scripts/install-tools.sh && test -x scripts/quality-baseline.sh && test -d _bmad-output/quality-gate/baseline/`
  - **Commit**: `feat(scripts): add tool installation and baseline snapshot scripts`
  - _Requirements: FR-3, FR-11, FR-20_
  - _Design: Tool Installation Scripts, Quality Baseline Automation_

---

## Phase 3: Testing

**Goal**: Verify backward compatibility and test new Makefile targets.

- [x] 3.1 [P] Verify AC-9: All existing targets work identically
  - **Do**: Run each existing target and verify exit code 0: test, lint, format, e2e, e2e-soc, check. Confirm no behavior changes.
  - **Files**: Makefile (verification only)
  - **Done when**: All existing targets pass without error; check target runs typecheck (pyright) instead of mypy
  - **Verify**: `make test && make lint && make format --check && make check && echo EXISTING_TARGETS_PASS`
  - **Commit**: `test(makefile): verify backward compatibility of existing targets`
  - _Requirements: FR-5, FR-6, FR-8, FR-18, FR-19_
  - _Design: Backward Compatibility Validation_

- [x] 3.2 [P] Test new Makefile targets
  - **Do**: Run each new target: typecheck, security-bandit, layer1, layer2, layer3, layer4, quality-baseline. Verify they execute and produce output.
  - **Files**: Makefile (verification only)
  - **Done when**: All new targets execute; quality-baseline creates files in _bmad-output/quality-gate/baseline/
  - **Verify**: `make typecheck && make security-bandit && make quality-baseline && ls _bmad-output/quality-gate/baseline/ && echo NEW_TARGETS_PASS`
  - **Commit**: `test(makefile): verify new quality gate targets functional`
  - _Requirements: FR-7, FR-8, FR-9, FR-10, FR-11, FR-20_
  - _Design: Quality Gate Target Testing_

---

## Phase 4: Quality Gates

**Goal**: All local checks pass, update CI, create PR.

- [ ] 4.1 V1 [VERIFY] Full local CI: typecheck + lint + existing tests
  - **Do**: Run complete local CI: typecheck (pyright), lint (ruff, pylint), test (pytest)
  - **Verify**: `make typecheck && make lint && make test && echo V1_PASS`
  - **Done when**: No type errors, no lint errors, all tests pass
  - **Commit**: `chore(tools): pass quality checkpoint` (if fixes needed)
  - _Requirements: FR-5, FR-8, FR-17, FR-19_
  - _Design: Quality Gate Validation_

- [ ] 4.2 Update CI workflow with quality gate steps
  - **Do**: Add layer4 security step (bandit, semgrep) and quality-gate-ci step (layer1-ci through layer4) to .github/workflows/python-tests.yml
  - **Files**: .github/workflows/python-tests.yml
  - **Done when**: CI workflow has layer4 and quality-gate-ci steps
  - **Verify**: `grep -q "layer4" .github/workflows/python-tests.yml && grep -q "quality-gate-ci" .github/workflows/python-tests.yml`
  - **Commit**: `ci(workflow): add quality gate layers to python-tests.yml`
  - _Requirements: FR-17, FR-29_
  - _Design: CI Integration_

- [ ] 4.3 Create .pre-commit-config.yaml
  - **Do**: Create pre-commit config with hooks: ruff, ruff-format, pyright, bandit, deptry
  - **Files**: .pre-commit-config.yaml
  - **Done when**: Config file exists with all 5 hooks defined
  - **Verify**: `cat .pre-commit-config.yaml | grep -q "id: ruff" && cat .pre-commit-config.yaml | grep -q "id: pyright"`
  - **Commit**: `config(pre-commit): add hooks for ruff, pyright, bandit, deptry`
  - _Requirements: FR-22_
  - _Design: Pre-commit Hook Configuration_

- [ ] 4.4 Update project documentation: mypy→pyright references
  - **Do**: Update all documentation files that reference mypy to use pyright instead. Files to update: `.github/copilot-instructions.md`, `docs/development-guide.md`, `README.md` (if mentions mypy). Also add new quality-gate documentation (make quality-gate, layers, security targets).
  - **Files**: .github/copilot-instructions.md, docs/development-guide.md, README.md (if applicable)
  - **Done when**: All "mypy" references replaced with "pyright"; new quality-gate commands documented
  - **Verify**: `! grep -r "mypy" .github/copilot-instructions.md docs/ 2>/dev/null; grep -q "quality-gate" docs/development-guide.md || grep -q "quality-gate" README.md`
  - **Commit**: `docs: update references from mypy to pyright, document quality-gate`
  - _Requirements: FR-18_
  - _Design: Documentation Updates_

---

## Phase 5: PR Lifecycle

**Goal**: Create PR, monitor CI, resolve issues, validate completion.

- [ ] 5.1 Create PR and validate completion
  - **Do**:
    1. Verify on feature branch: `git branch --show-current`
    2. Push branch: `git push -u origin $(git branch --show-current)`
    3. Create PR: `gh pr create --title "feat: Tooling Foundation - Quality Gates, Security Tools, Pyright Migration" --body "Implements quality gate layers, security tooling, mypy→pyright migration. Maintains 100% backward compatibility."`
    4. Monitor CI: `gh pr checks --watch`
    5. If CI fails: read failure, fix locally, push, re-verify
  - **Verify**: `gh pr checks` shows all green
  - **Done when**: All CI checks pass, PR ready for review
  - **Commit**: None (PR creation only)
  - _Requirements: FR-17_
  - _Design: PR Creation and CI Validation_

- [ ] 5.2 Clean up SUDO_PASS from .env (post-PR)
  - **Do**: After PR is merged and all CI validates successfully, remove the temporary `SUDO_PASS` line from `.env` file. Use `sed` to delete only the line containing `SUDO_PASS=`, preserving all other `.env` content.
  - **Commands**:
    ```bash
    sed -i '/^SUDO_PASS=/d' .env
    ```
  - **Files**: .env (remove one line only)
  - **Done when**: `! grep -q "SUDO_PASS" .env` AND `.env` still exists with other content
  - **Verify**: `! grep -q "SUDO_PASS" .env && test -f .env`
  - **Commit**: None (local cleanup only, no commit needed)
  - _Requirements: None_ (security cleanup)
  - _Design: Post-PR Cleanup_

---

## Unresolved Questions

None at task generation time.

---

## Notes

**POC shortcuts taken**:
- Hardcoded tool versions in research.md (use latest stable in implementation)
- Minimal HA-specific semgrep rules (yaml.load, eval only)
- E2E suite auto-discovery uses simple `e2e-%` wildcard pattern on Makefile

**Production TODOs**:
- Expand semgrep rules with more HA-specific patterns
- Add baseline metrics documentation in _bmad-output/quality-gate/baseline/README.md
- Create .vscode/settings.json if not exists (python.linting.mypyEnabled: false)
- Add antipattern_checker.py baseline run output to _bmad-output/
- Implement sudo-free gitleaks installation in scripts/install-tools.sh for CI environments

**Sudo Usage Policy** (CRITICAL):
- **ONLY task 1.3 (gitleaks installation) requires sudo** — all other tools use pip without sudo
- Sudo is used via `echo "$SUDO_PASS" | sudo -S` to read password from `.env` variable
- Task 5.2 cleans up `SUDO_PASS` from `.env` after PR completion
- No other tasks should use sudo under any circumstance

**E2E verification**: Not applicable—quality tools are CLI-based, verified via Makefile targets.

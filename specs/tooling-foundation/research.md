# Research: Tooling Foundation

## Goal
Install missing tools, fix broken tooling, add Makefile targets, establish baseline metrics.

---

## Executive Summary

**Feasibility**: High | **Risk**: Low | **Effort**: Medium (8-12 Story Points)

All tools are well-documented, actively maintained, and compatible with Home Assistant custom components.

**Current State Analysis:**
- AC-0.15 (_bmad-output/ in .gitignore): **ALREADY COMPLETE** (line 103)
- AC-0.14 (TS tooling): **PARTIALLY COMPLETE** (.eslintrc.json, tsconfig.e2e.json exist)
- AC-0.9 (existing targets): Must verify before making changes

**Implementation Order (CRITICAL - do not change):**
1. Install tools (pip + binary)
2. Create config files (pyproject.toml, .gitleaks.toml, .semgrep.yml)
3. Create/update Makefile targets
4. Verify existing targets still work (AC-0.9)
5. Update documentation files
6. Create _bmad-output/ directory structure
7. Run quality-baseline
8. Update CI workflow

---

## 1. Tools to Install

### 1.1 Python Tools (via pip)

```bash
.venv/bin/pip install bandit[toml]
.venv/bin/pip install pip-audit
.venv/bin/pip install semgrep
.venv/bin/pip install deptry
.venv/bin/pip install vulture
.venv/bin/pip install pyright
```

### 1.2 Binary Tool (gitleaks)

```bash
# Linux
wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_linux_x64.tar.gz
tar -xvf gitleaks_8.18.4_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/

# Verify
gitleaks --version
```

---

## 2. Configuration Files to Create/Update

### 2.1 pyproject.toml - Add New Sections

**REMOVE this section:**
```toml
[tool.mypy]
# ... entire section to be removed
```

**ADD these sections:**
```toml
[tool.bandit]
exclude_dirs = ["tests", "tests/ha-manual", "tests/e2e", ".venv"]
skips = ["B101"]  # assert_used - HA uses asserts in config flow

[tool.pyright]
include = ["custom_components", "tests"]
exclude = ["**/tests/ha-manual"]
typeCheckingMode = "standard"
pythonVersion = "3.14"  # Match CI
reportMissingImports = "error"
reportMissingTypeStubs = "warning"
reportPrivateUsage = "none"
reportUnknownMemberType = "warning"

[tool.deptry]
exclude = ["tests", "tests/ha-manual", "tests/e2e"]
ignore = ["DEP003"]  # Transitive dependencies

[tool.vulture]
exclude = ["tests/*", "tests/ha-manual/*", "tests/e2e/*"]
min_confidence = 80
```

**UPDATE existing section:**
```toml
[tool.pylint.MASTER]
py-version = "3.14"  # Change from 3.11
```

### 2.2 .gitleaks.toml - CREATE

```toml
title = "Gitleaks Configuration"
extendDefault = true

[allowlist]
paths = [
    '''tests/''',
    '''tests/ha-manual/''',
    '''tests/e2e/''',
    '''\.venv/''',
    '''node_modules/''',
    '''_bmad-output/''',
]
```

### 2.3 .semgrep.yml - CREATE

```yaml
rules:
  - id: ha-unsafe-yaml-load
    languages: [python]
    message: Use yaml.safe_load() instead of yaml.load()
    severity: ERROR
    pattern: yaml.load(...)
    fix: yaml.safe_load(...)

  - id: ha-dangerous-eval
    languages: [python]
    message: Avoid eval() in HA custom components
    severity: ERROR
    pattern: eval(...)
```

### 2.4 .eslintrc.json - UPDATE (file exists)

Add extends for TypeScript rules:
```json
{
  "env": {
    "es6": true,
    "browser": true,
    "node": true
  },
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint"],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "parserOptions": {
    "ecmaVersion": 2022,
    "sourceType": "module"
  },
  "rules": {
    "no-console": "warn",
    "prefer-const": "error",
    "no-var": "error",
    "semi": ["error", "always"],
    "quotes": ["error", "single"]
  }
}
```

---

## 3. Makefile Targets - CREATE/UPDATE

### 3.1 New Targets to ADD

```makefile
# Security targets
.PHONY: security security-bandit security-audit security-gitleaks security-semgrep

security-bandit:
	@echo "Running Bandit security scan..."
	.venv/bin/bandit -r custom_components/ -f screen -ll

security-audit:
	@echo "Running pip-audit..."
	.venv/bin/python -m pip-audit --desc

security-gitleaks:
	@echo "Running Gitleaks secret detection..."
	@if command -v gitleaks >/dev/null 2>&1; then \
		gitleaks git --verbose --report-format=screen; \
	else \
		echo "ERROR: gitleaks not found. Install from https://github.com/gitleaks/gitleaks/releases"; \
		exit 1; \
	fi

security-semgrep:
	@echo "Running Semgrep scan..."
	.venv/bin/semgrep scan --config auto --error --strict custom_components/

security: security-bandit security-audit
	@echo "Security scan complete"

# Type checking - REPLACES mypy
.PHONY: typecheck

typecheck:
	pyright custom_components/ tests/

# Mutation testing shortcut
.PHONY: mutation

mutation:
	.venv/bin/mutmut run --until=100

# Quality gate - orchestrates ALL layers
.PHONY: quality-gate quality-baseline

quality-gate:
	@echo "=== Layer 1: Test Execution ==="
	$(MAKE) test
	@echo "=== Layer 2: Test Quality ==="
	python3 .claude/skills/quality-gate/scripts/mutation_analyzer.py . --gate
	@echo "=== Layer 3: Code Quality ==="
	$(MAKE) lint
	$(MAKE) typecheck
	.venv/bin/deptry . --ignore "DEP003"
	.venv/bin/vulture custom_components/ --min-confidence 80
	@echo "=== Layer 4: Security ==="
	$(MAKE) security-bandit
	.venv/bin/semgrep scan --config auto custom_components/
	@echo "=== Quality Gate PASSED ==="

quality-baseline:
	@mkdir -p _bmad-output/quality-gate
	@echo "Creating quality baseline..."
	$(MAKE) test > _bmad-output/quality-gate/pytest.txt 2>&1 || true
	$(MAKE) lint > _bmad-output/quality-gate/ruff.txt 2>&1 || true
	$(MAKE) typecheck > _bmad-output/quality-gate/pyright.txt 2>&1 || true
	$(MAKE) security-bandit > _bmad-output/quality-gate/bandit.txt 2>&1 || true
	.venv/bin/deptry . > _bmad-output/quality-gate/deptry.txt 2>&1 || true
	.venv/bin/vulture custom_components/ > _bmad-output/quality-gate/vulture.txt 2>&1 || true
	@echo "Baseline saved to _bmad-output/quality-gate/"
```

### 3.2 Existing Targets to UPDATE

**UPDATE .PHONY line:**
```makefile
.PHONY: help test test-cover test-verbose test-dashboard test-e2e test-e2e-headed test-e2e-debug \
        e2e e2e-headed e2e-debug e2e-soc e2e-soc-headed e2e-soc-debug \
        staging-up staging-down staging-reset \
        lint typecheck format check clean htmlcov \
        security security-bandit security-audit security-gitleaks security-semgrep \
        mutation quality-gate quality-baseline
```

**UPDATE help target:**
```makefile
help:
	@echo "Comandos disponibles:"
	@echo "  make test            - Ejecutar todos los tests Python"
	@echo "  make test-cover      - Ejecutar tests Python con reporte de cobertura"
	@echo "  make lint           - Ejecutar linting (ruff, pylint)"
	@echo "  make typecheck      - Ejecutar type checking (pyright)"
	@echo "  make format         - Formatear código con black e isort"
	@echo "  make check          - Ejecutar todos los checks (test, lint, typecheck)"
	@echo "  make mutation       - Ejecutar mutation testing (mutmut)"
	@echo "  make quality-gate   - Ejecutar quality gate completo (layers 1-4)"
	@echo "  make quality-baseline - Crear snapshot baseline de calidad"
	@echo "  make security       - Ejecutar security scans (bandit, pip-audit)"
	@echo "  make e2e            - Ejecutar tests E2E (requiere HA en localhost:8123)"
	@echo "  make clean          - Limpiar archivos generados"
```

**UPDATE check target:**
```makefile
check: test lint typecheck
```

**DEPRECATE mypy target (keep for compatibility but warn):**
```makefile
mypy:
	@echo "WARNING: mypy is deprecated. Use 'make typecheck' for pyright."
	pyright custom_components/ tests/
```

### 3.3 Clean Target - ADD

Add to existing clean target:
```makefile
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	# ... existing lines ...
	rm -rf _bmad-output
```

---

## 4. Files to Update Beyond Makefile

### 4.1 Documentation Files

**File: `.github/copilot-instructions.md`**
- Search for "mypy" references, replace with "pyright"
- Update type checking instructions

**File: `docs/development-guide.md`**
- Update any mypy references to pyright
- Add new quality-gate and security targets

### 4.2 VSCode Settings

**File: `.vscode/settings.json` (create if doesn't exist)**
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.ruffEnabled": true,
  "python.analysis.typeCheckingMode": "standard",
  "python.linting.mypyEnabled": false,
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

### 4.3 Package.json - Add Scripts (if not present)

```json
{
  "scripts": {
    "typecheck": "tsc --noEmit",
    "lint:ts": "eslint tests/e2e/**/*.ts",
    "lint:ts:fix": "eslint tests/e2e/**/*.ts --fix"
  }
}
```

---

## 5. Quality Gate Layers - EXPLICIT Commands

| Layer | Purpose | Commands (MUST ALL PASS) |
|-------|---------|--------------------------|
| **L1: Test Execution** | Unit tests pass | `make test` |
| **L2: Test Quality** | Mutation score OK | `python3 .claude/skills/quality-gate/scripts/mutation_analyzer.py . --gate` |
| **L3: Code Quality** | Lint + Type + Dead code | `make lint`, `make typecheck`, `deptry .`, `vulture custom_components/` |
| **L4: Security** | No vulnerabilities | `make security-bandit`, `semgrep scan --config auto` |

**Gate fails if ANY layer fails.** No partial passes.

---

## 6. AC Status Tracking

| AC | Status | Notes |
|----|--------|-------|
| AC-0.1: bandit | READY | Config defined, Makefile target defined |
| AC-0.2: pip-audit | READY | Chosen over safety, Makefile target defined |
| AC-0.3: gitleaks | READY | Binary install documented, Makefile target defined |
| AC-0.4: semgrep | READY | Config defined, Makefile target defined |
| AC-0.5: pyright | READY | Replaces mypy, config in pyproject.toml |
| AC-0.6: quality-gate | READY | All 4 layers explicitly defined |
| AC-0.7: mutation shortcut | READY | Target: `mutmut run --until=100` |
| AC-0.8: typecheck | READY | Replaces mypy in `check` target |
| AC-0.9: existing targets | VERIFY | Must test after changes: test, lint, format, e2e, check |
| AC-0.10: CI workflow | READY | Update python-tests.yml or create quality-gate.yml |
| AC-0.11: baseline snapshot | READY | `make quality-baseline` saves to _bmad-output/quality-gate/ |
| AC-0.12: deptry | READY | Config in pyproject.toml |
| AC-0.13: vulture | READY | Config in pyproject.toml |
| AC-0.14: TS tooling | PARTIAL | .eslintrc.json exists, update required |
| AC-0.15: _bmad-output/ gitignore | **DONE** | Already in .gitignore line 103 |
| AC-0.16: antipattern_checker | READY | Run `.claude/skills/quality-gate/scripts/antipattern_checker.py` |

---

## 7. CI/CD Integration

### 7.1 Update .github/workflows/python-tests.yml

**Add to existing job:**
```yaml
- name: Type checking
  run: pyright custom_components/ tests/

- name: Security scan
  run: |
    pip install bandit semgrep
    bandit -r custom_components/
    semgrep scan --config auto custom_components/

- name: Import consistency
  run: |
    pip install deptry
    deptry . --ignore "DEP003"
```

### 7.2 OR Create .github/workflows/quality-gate.yml

Separate workflow for full quality gate on PRs:
```yaml
name: Quality Gate

on:
  pull_request:
    branches: [main]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - run: pip install -r requirements_dev.txt
      - run: pip install bandit semgrep deptry vulture pyright
      - name: Run quality gate
        run: make quality-gate
```

---

## 8. Implementation Checklist (ORDER MATTERS)

- [ ] 1. Install Python tools (bandit, pip-audit, semgrep, deptry, vulture, pyright)
- [ ] 2. Install gitleaks binary
- [ ] 3. Update pyproject.toml (remove mypy, add bandit/pyright/deptry/vulture, update pylint version)
- [ ] 4. Create .gitleaks.toml
- [ ] 5. Create .semgrep.yml
- [ ] 6. Update .eslintrc.json (add extends)
- [ ] 7. Update Makefile (.PHONY, help, new targets, updated check target)
- [ ] 8. Verify existing targets work (AC-0.9): `make test`, `make lint`, `make format`, `make e2e`
- [ ] 9. Create _bmad-output/quality-gate/ directory
- [ ] 10. Update .github/copilot-instructions.md (mypy → pyright)
- [ ] 11. Update docs/development-guide.md if needed
- [ ] 12. Create/update .vscode/settings.json
- [ ] 13. Run quality-baseline: `make quality-baseline`
- [ ] 14. Verify baseline saved to _bmad-output/quality-gate/
- [ ] 15. Run antipattern_checker.py and document findings
- [ ] 16. Update CI workflow (python-tests.yml or create quality-gate.yml)
- [ ] 17. Commit all changes

---

## 9. Sources

- [Bandit Documentation](https://github.com/pycqa/bandit)
- [pip-audit Documentation](https://github.com/pypa/pip-audit)
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [Semgrep Documentation](https://semgrep.dev/docs/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Deptry Documentation](https://github.com/fpgmaas/deptry)
- [Vulture Documentation](https://github.com/jendrikseipp/vulture)
- [GNU Make Manual](https://www.gnu.org/software/make/manual/html_node/Parallel.html)

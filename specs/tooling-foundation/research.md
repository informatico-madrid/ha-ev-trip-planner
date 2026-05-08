# Research: Tooling Foundation

## Goal
Install missing tools, fix broken tooling, add Makefile targets, establish baseline metrics.

---

## Executive Summary

**Feasibility**: High | **Risk**: Low | **Effort**: Medium (8-12 Story Points)

All tools are well-documented, actively maintained, and compatible with Home Assistant custom components. This research covers security tools (bandit, pip-audit, gitleaks, semgrep), type checker migration (mypy → pyright), quality gate orchestration, and CI/CD + TypeScript tooling.

---

## 1. Security Tools

### 1.1 Bandit - Python Code Security Linter

**Installation:**
```bash
pip install bandit[toml]
```

**Makefile Target:**
```makefile
security-bandit:
	@echo "Running Bandit security scan..."
	.venv/bin/bandit -r custom_components/ -f screen -ll
```

**Configuration (pyproject.toml):**
```toml
[tool.bandit]
exclude_dirs = ["tests", "tests/ha-manual", "tests/e2e", ".venv"]
skips = ["B101"]  # assert_used - HA uses asserts in config flow
```

**Required Exclusions for HA:**
- `tests/`, `tests/ha-manual/`, `tests/e2e/` - test fixtures contain sample code
- `.venv/` - virtual environment
- B101 (assert_used) - HA uses asserts in config flow validation, not security-critical

---

### 1.2 pip-audit - Dependency Vulnerability Scanner

**Choice:** pip-audit over safety.

**Rationale:**
- PyPA-backed (official Python Packaging Authority)
- No API key required
- Offline-capable with cached database
- OSV support (Google's Open Source Vulnerabilities database)

**Installation:**
```bash
pip install pip-audit
```

**Makefile Target:**
```makefile
security-audit:
	@echo "Running pip-audit..."
	.venv/bin/python -m pip-audit --desc
```

---

### 1.3 Gitleaks - Secret Detection

**Installation:**
```bash
# Linux (binary download)
wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_linux_x64.tar.gz
tar -xvf gitleaks_8.18.4_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/

# macOS
brew install gitleaks
```

**Makefile Target:**
```makefile
security-gitleaks:
	@echo "Running Gitleaks secret detection..."
	@if command -v gitleaks >/dev/null 2>&1; then \
		gitleaks git --verbose --report-format=screen; \
	else \
		echo "ERROR: gitleaks not found. Install with: brew install gitleaks (macOS) or download from https://github.com/gitleaks/gitleaks/releases"; \
		exit 1; \
	fi
```

**Configuration (.gitleaks.toml):**
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
]
```

---

### 1.4 Semgrep - Multi-language Static Analysis

**Installation:**
```bash
pip install semgrep
```

**Makefile Target:**
```makefile
security-semgrep:
	@echo "Running Semgrep scan..."
	.venv/bin/semgrep scan --config auto --error --strict custom_components/
```

**HA-Specific Rules (.semgrep.yml):**
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

---

## 2. Type Checker Migration (mypy → pyright)

### 2.1 Why pyright over mypy?

| Aspect | mypy | pyright |
|--------|------|---------|
| Performance | Slower on large codebases | Faster |
| Type narrowing | Less consistent | Follows PEP 484 spec |
| `Any` narrowing | Inconsistent | Never narrows `Any` |
| Python 3.12+ | May have false positives | Better support |

### 2.2 Installation

```bash
pip install pyright
```

### 2.3 Configuration (pyproject.toml)

Replace `[tool.mypy]` section with:

```toml
[tool.pyright]
include = ["custom_components", "tests"]
exclude = ["**/tests/ha-manual"]
typeCheckingMode = "standard"
pythonVersion = "3.12"
reportMissingImports = "error"
reportMissingTypeStubs = "warning"  # HA libs lack stubs
reportPrivateUsage = "none"  # HA uses private members
reportUnknownMemberType = "warning"
```

### 2.4 Makefile Changes

**Remove:**
```makefile
mypy:
	mypy custom_components/ tests/ --exclude tests/ha-manual --no-namespace-packages
```

**Add:**
```makefile
typecheck:
	pyright custom_components/ tests/
```

**Update check target:**
```makefile
# Old: check: test lint mypy
# New:
check: test lint typecheck
```

---

## 3. Quality Gate Orchestration

### 3.1 Sequential Layer Execution

Use `&&` operator for fail-fast execution - if any layer fails, subsequent layers don't run.

```makefile
quality-gate:
	@echo "=== Layer 1: Test Execution ==="
	pytest --cov=custom_components tests/ && \
	echo "=== Layer 2: Test Quality ===" && \
	python3 .claude/skills/quality-gate/scripts/mutation_analyzer.py . --gate && \
	echo "=== Layer 3: Code Quality ===" && \
	ruff check custom_components/ && \
	pyright custom_components/ && \
	echo "=== Layer 4: Security ===" && \
	bandit -r custom_components/ && \
	echo "=== Quality Gate PASSED ==="
```

### 3.2 Exit Codes

Each tool returns specific exit codes that Make propagates:

| Tool | 0=Success | 1=Errors Found |
|------|-----------|----------------|
| pytest | ✓ | Tests failed |
| pyright | ✓ | Type errors |
| ruff | ✓ | Lint errors |
| bandit | ✓ | Issues found |

### 3.3 Baseline Snapshot

**Purpose:** Capture initial state before improvements begin.

```makefile
BASELINE_DIR := _bmad-output/quality-gate

quality-baseline:
	@mkdir -p $(BASELINE_DIR)
	pytest --cov=custom_components > $(BASELINE_DIR)/pytest.txt 2>&1
	ruff check custom_components/ > $(BASELINE_DIR)/ruff.txt 2>&1
	pyright custom_components/ > $(BASELINE_DIR)/pyright.txt 2>&1
	bandit -r custom_components/ > $(BASELINE_DIR)/bandit.txt 2>&1
	@echo "Baseline saved to $(BASELINE_DIR)/"
```

---

## 4. Additional Quality Tools

### 4.1 deptry - Import Consistency

**Purpose:** Verify imports match dependencies (critical for post-Spec 3 validation).

**Installation:**
```bash
pip install deptry
```

**Makefile Target:**
```makefile
quality-deptry:
	deptry . --ignore "DEP003"  # DEP003 = transitive deps (acceptable)
```

**Error Codes:**
- DEP001: Missing dependency
- DEP002: Unused dependency
- DEP003: Transitive dependency

### 4.2 vulture - Dead Code Detection

**Purpose:** Detect unused code (complements Spec 1 dead-code-elimination).

**Installation:**
```bash
pip install vulture
```

**Makefile Target:**
```makefile
quality-vulture:
	vulture custom_components/ --min-confidence 80 --exclude "*/tests/*"
```

---

## 5. TypeScript Tooling (E2E Tests)

### 5.1 TypeScript Compiler (tsc)

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true
  },
  "include": ["tests/e2e/**/*.ts"],
  "exclude": ["node_modules/**", ".venv/**"]
}
```

**package.json script:**
```json
{
  "scripts": {
    "typecheck": "tsc --noEmit"
  }
}
```

**Makefile:**
```makefile
typecheck-ts:
	npm run typecheck
```

### 5.2 ESLint for TypeScript

**Installation:**
```bash
npm install --save-dev @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

**.eslintrc.js:**
```javascript
module.exports = {
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended'
  ]
};
```

### 5.3 Prettier

**.prettierrc.json:**
```json
{
  "semi": true,
  "trailingComma": "all",
  "singleQuote": true,
  "printWidth": 100
}
```

---

## 6. CI/CD Integration

### 6.1 GitHub Actions Quality Gate Workflow

**File:** `.github/workflows/quality-gate.yml`

```yaml
name: Quality Gate

on:
  pull_request:
    branches: [main]

jobs:
  test-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - run: pip install -r requirements_dev.txt
      - run: pytest --cov=custom_components --cov-report=xml

  mutation-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements_dev.txt
      - run: mutmut run --until=100
      - run: python3 .claude/skills/quality-gate/scripts/mutation_analyzer.py . --gate

  quality-gate:
    runs-on: ubuntu-latest
    needs: [test-python, mutation-test]
    if: always()
    steps:
      - name: Check all jobs passed
        run: |
          if [ "${{ needs.test-python.result }}" != "success" ] || \
             [ "${{ needs.mutation-test.result }}" != "success" ]; then
            echo "Quality gate failed"
            exit 1
          fi
```

### 6.2 Parallel Execution

Jobs without `needs:` run in parallel. Jobs with `needs:` wait for dependencies.

---

## 7. Implementation Order

1. Install Python tools (bandit, pip-audit, semgrep, deptry, vulture, pyright)
2. Create/update pyproject.toml configurations
3. Create Makefile targets (security-bandit, security-audit, security-gitleaks, security-semgrep, typecheck, quality-gate, quality-baseline)
4. Install gitleaks binary
5. Set up TypeScript tooling (tsconfig.json, .eslintrc.js, .prettierrc.json)
6. Update CI workflow
7. Run quality-baseline and save results
8. Update .gitignore for _bmad-output/

---

## 8. Sources

- [Bandit Documentation](https://github.com/pycqa/bandit)
- [pip-audit Documentation](https://github.com/pypa/pip-audit)
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [Semgrep Documentation](https://semgrep.dev/docs/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Deptry Documentation](https://github.com/fpgmaas/deptry)
- [Vulture Documentation](https://github.com/jendrikseipp/vulture)
- [GNU Make Manual](https://www.gnu.com/software/make/manual/html_node/Parallel.html)

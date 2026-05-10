.PHONY: help test test-cover test-verbose test-dashboard test-e2e test-e2e-headed test-e2e-debug e2e e2e-headed e2e-debug e2e-soc e2e-soc-headed e2e-soc-debug staging-up staging-down staging-reset lint mypy format check clean htmlcov layer3a layer1 layer1-ci layer2 layer3b layer3 layer4 quality-gate quality-gate-ci security-bandit security-audit security-gitleaks security-semgrep typecheck dead-code unused-deps import-check refurb mutation test-parallel test-random e2e-lint pre-commit-install pre-commit-run pre-commit-update quality-baseline

help:
	@echo "Available commands / Comandos disponibles:"
	@echo ""
	@echo "Testing / Pruebas:"
	@echo "  make test            - Run all Python tests / Ejecutar todos los tests Python"
	@echo "  make test-cover      - Run tests with coverage report / Tests con reporte de cobertura"
	@echo "  make test-verbose    - Run tests with verbose output / Tests con salida detallada"
	@echo "  make test-dashboard  - Run tests and open coverage dashboard / Tests y dashboard de cobertura"
	@echo "  make test-parallel   - Run tests in parallel mode / Tests en paralelo"
	@echo "  make test-random     - Run tests in random order / Tests en orden aleatorio"
	@echo "  make test-e2e        - Run E2E tests (HA on localhost:8123) / Tests E2E (HA en localhost:8123)"
	@echo "  make e2e             - Auto-setup HA and run E2E / Arrancar HA y ejecutar E2E"
	@echo "  make e2e-soc         - E2E dynamic SOC suite / Suite E2E dynamic SOC"
	@echo "  make e2e-lint        - Lint E2E test files / Lintear archivos E2E"
	@echo ""
	@echo "Quality Gate Layers (6-layer architecture):"
	@echo "  make layer3a         - Layer 3A: Smoke test (ruff, pyright, SOLID-TA, principles, anti-TA)"
	@echo "  make layer1          - Layer 1: Test execution (unit + E2E) / Capa 1: Ejecución de tests"
	@echo "  make layer1-ci       - Layer 1 CI: Unit + integration tests, no E2E (fast) / Capa 1 CI: Unit + integration (sin E2E, rápido)"
	@echo "  make layer2          - Layer 2: Test quality (mutation) / Capa 2: Calidad de tests (mutación)"
	@echo "  make layer3b         - Layer 3B: Deep quality (SOLID-TB + Anti-TB via BMAD) / Capa 3B: Calidad profunda"
	@echo "  make layer3          - Layer 3: Code quality (all tiers) / Capa 3: Calidad de código"
	@echo "  make layer4          - Layer 4: Security scanning (8 tools) / Capa 4: Escaneo de seguridad"
	@echo "  make quality-gate    - Full quality gate (with E2E) / Quality gate completo (con E2E)"
	@echo "  make quality-gate-ci - CI quality gate (without E2E) / Quality gate CI (sin E2E)"
	@echo ""
	@echo "Security / Seguridad:"
	@echo "  make security-bandit    - Run Bandit security linter / Linter de seguridad Bandit"
	@echo "  make security-audit     - Run pip-audit for vulnerabilities / pip-audit para vulnerabilidades"
	@echo "  make security-gitleaks  - Run gitleaks for secret detection / gitleaks para detectar secretos"
	@echo "  make security-semgrep   - Run Semgrep static analysis / Análisis estático Semgrep"
	@echo ""
	@echo "Code Quality / Calidad de Código:"
	@echo "  make typecheck       - Run pyright type checker / Ejecutar pyright type checker"
	@echo "  make mypy            - DEPRECATED: Use typecheck instead / OBSOLETO: Usar typecheck"
	@echo "  make lint            - Run linting (ruff, pylint) / Ejecutar linting (ruff, pylint)"
	@echo "  make format          - Format code with black and isort / Formatear código con black e isort"
	@echo "  make dead-code       - Find dead code with vulture / Encontrar código muerto con vulture"
	@echo "  make unused-deps     - Find unused dependencies with deptry / Dependencias no usadas"
	@echo "  make import-check    - Check import organization / Verificar organización de imports"
	@echo "  make refurb          - Python modernization suggestions / Sugerencias de modernización"
	@echo "  make mutation        - Run mutation testing / Ejecutar pruebas de mutación"
	@echo ""
	@echo "Pre-commit Hooks:"
	@echo "  make pre-commit-install - Install pre-commit hooks / Instalar hooks pre-commit"
	@echo "  make pre-commit-run     - Run pre-commit on all files / Ejecutar pre-commit"
	@echo "  make pre-commit-update  - Update pre-commit hooks / Actualizar hooks pre-commit"
	@echo ""
	@echo "Baselines & Utilities:"
	@echo "  make quality-baseline - Establish quality baseline / Establecer línea base de calidad"
	@echo "  make check            - Run all checks (test, lint, typecheck) / Ejecutar todos los checks"
	@echo "  make clean            - Clean generated files / Limpiar archivos generados"
	@echo "  make htmlcov          - Generate HTML coverage report / Generar reporte HTML de cobertura"
	@echo ""
	@echo "Staging Environment (Docker, localhost:8124):"
	@echo "  make staging-up      - Start staging HA / Arrancar HA staging"
	@echo "  make staging-down    - Stop staging HA / Detener HA staging"
	@echo "  make staging-reset   - Reset staging HA / Resetear HA staging"

test:
	PYTHONPATH=. .venv/bin/python -m pytest tests/unit tests/integration -v --tb=short

test-cover:
	PYTHONPATH=. .venv/bin/python -m pytest tests/unit tests/integration --cov=custom_components.ev_trip_planner --cov-report=term-missing --cov-report=html --cov-fail-under=100

test-verbose:
	python3 -m pytest tests/unit tests/integration -vv -s --tb=long

test-dashboard:
	python3 -m pytest tests/unit tests/integration --cov=custom_components.ev_trip_planner --cov-report=html --cov-fail-under=100
	@echo "Dashboard de cobertura generado en htmlcov/index.html"

test-e2e:
	@echo "Ejecutando tests E2E contra http://localhost:8123 ..."
	@echo "⚠️  E2E uses hass directly (no Docker). See docs/staging-vs-e2e-separation.md"
	npx playwright test tests/e2e/ --workers=1

test-e2e-debug:
	npx playwright test tests/e2e/ --workers=1 --debug

# e2e targets: auto-setup HA if needed, then run tests
e2e:
	./scripts/run-e2e.sh

# e2e-soc: dynamic SOC capping suite (requires HA with SOH sensor configured)
# Uses INDEPENDENT setup: separate HA config dir, separate auth state (user-soc.json), separate Playwright config
e2e-soc:
	./scripts/run-e2e-soc.sh

lint:
	ruff check .
	pylint custom_components/ tests/unit/ tests/integration/

mypy:
	@echo "⚠️  DEPRECATED: mypy target is deprecated. Use 'make typecheck' instead (runs pyright)."
	@echo "   mypy has been removed from the project in favor of pyright."
	@echo "   Running pyright for compatibility..."
	$(MAKE) typecheck

format:
	black .
	isort .

check: test lint typecheck

# ============================================================================
# Type Checking (pyright)
# ============================================================================
typecheck:
	@echo "Running pyright type checker..."
	.venv/bin/pyright custom_components/ tests/

# ============================================================================
# Quality Gate Layers (6-layer: L3A → L1 → L2 → L3B → L4)
# ============================================================================
# Layer 3A: Smoke Test (fast, deterministic AST-based checks)
# If this fails, stop immediately — don't run L1/L2/L3B/L4
layer3a:
	@echo "=== Layer 3A: Smoke Test ==="
	@echo "Running ruff check..."
	@ruff check custom_components/ && ruff format --check custom_components/ || echo "WARNING: ruff violations found"
	@echo "Running pyright type check..."
	@$(MAKE) typecheck
	@echo "Running SOLID Tier A (AST-based)..."
	@python3 .claude/skills/quality-gate/scripts/solid_metrics.py custom_components/ || echo "WARNING: SOLID Tier A violations"
	@echo "Running Principles (DRY/KISS/YAGNI/LoD/CoI)..."
	@python3 .claude/skills/quality-gate/scripts/principles_checker.py custom_components/ || echo "WARNING: Principles violations"
	@echo "Running Antipatterns Tier A (25 AST patterns)..."
	@python3 .claude/skills/quality-gate/scripts/antipattern_checker.py custom_components/ || echo "WARNING: Antipattern Tier A violations"
	@echo "=== Layer 3A Complete ==="

# Layer 1: Test execution (unit tests + E2E auto-discovery)
layer1:
	$(MAKE) test
	@echo "Running E2E suites..."
	@$(MAKE) $(filter-out e2e-headed e2e-debug e2e-soc-headed e2e-soc-debug,$(filter e2e-%,$(.PHONY))) 2>/dev/null || echo "No E2E suites found (e2e-% targets)"

# Layer 1 CI: Unit tests only (no E2E for CI speed)
layer1-ci:
	$(MAKE) test

# Layer 2: Test Quality (mutation, weak tests, diversity)
layer2:
	@echo "Running Layer 2: Test Quality (mutation, weak tests, diversity)..."
	@echo "  → Mutation gate..."
	@.venv/bin/python .claude/skills/quality-gate/scripts/mutation_analyzer.py . --gate
	@echo "  → Weak test detector..."
	@.venv/bin/python .claude/skills/quality-gate/scripts/weak_test_detector.py tests/ custom_components/
	@echo "  → Test diversity..."
	@.venv/bin/python .claude/skills/quality-gate/scripts/diversity_metric.py tests/
	@echo "=== Layer 2 Complete ==="

# Layer 3B: Deep Quality (BMAD Party Mode — SOLID Tier B + Antipatterns Tier B)
layer3b:
	@echo "Running Layer 3B: Deep Quality (BMAD Tier B consensus)..."
	@echo "  → Generating SOLID Tier B context..."
	@.venv/bin/python .claude/skills/quality-gate/scripts/llm_solid_judge.py custom_components/
	@echo "  → Generating Antipatterns Tier B context..."
	@.venv/bin/python .claude/skills/quality-gate/scripts/antipattern_judge.py custom_components/ tests/
	@echo "  → Run BMAD Party Mode for consensus validation"
	@echo "     (Requires BMAD integration — context JSON files generated)"
	@echo "=== Layer 3B Complete ==="

# Layer 3: Code Quality (SOLID Tier A + Principles + Antipatterns Tier A)
# Deprecated: Use layer3a + layer3b instead
layer3: layer3a

# Layer 4: Security & Defense (8 tools, 3 priority levels)
layer4:
	@echo "Running Layer 4: Security & Defense..."
	@echo "  → Unified security scanner (8 tools)..."
	@python3 .claude/skills/quality-gate/scripts/security_scanner.py . --severity-threshold high --verbose || echo "WARNING: Layer 4 security findings detected"
	@echo "=== Layer 4 Complete ==="

# Alternative: run individual security tools
layer4-incremental:
	$(MAKE) security-bandit security-audit security-gitleaks security-semgrep dead-code unused-deps

# Quality Gate: Full 6-layer (L3A → L1 → L2 → L3B → L4, with E2E)
quality-gate:
	@echo "=== Full Quality Gate (6-layer architecture) ==="
	@echo "Phase 1: L3A Smoke Test (fail-fast)"
	$(MAKE) layer3a
	@echo "Phase 2: L1 Test Execution"
	$(MAKE) layer1
	@echo "Phase 3: L2 Test Quality"
	$(MAKE) layer2
	@echo "Phase 4: L3B Deep Quality (BMAD)"
	$(MAKE) layer3b
	@echo "Phase 5: L4 Security & Defense"
	$(MAKE) layer4
	@echo "=== Quality Gate PASSED ==="

# Quality Gate CI: Fast (excludes E2E + L3B)
quality-gate-ci:
	@echo "=== CI Quality Gate (L3A → L1-CI → L2 → L4, no E2E, no BMAD) ==="
	$(MAKE) layer3a
	$(MAKE) layer1-ci
	$(MAKE) layer2
	$(MAKE) layer4
	@echo "=== CI Quality Gate PASSED ==="

# ============================================================================
# Security Targets
# ============================================================================
security-bandit:
	@echo "Running Bandit security linter..."
	.venv/bin/bandit -r custom_components/ -f screen -v

security-audit:
	@echo "Running pip-audit for dependency vulnerabilities..."
	.venv/bin/pip-audit --desc --ignore-vuln PYSEC-2023-243

security-gitleaks:
	@echo "Running gitleaks for secret detection..."
	gitleaks detect --source . --verbose --no-git

security-semgrep:
	@echo "Running Semgrep static analysis..."
	.venv/bin/semgrep --config auto --error --verbose custom_components/ tests/unit/ tests/integration/

# ============================================================================
# Dead Code and Unused Dependencies
# ============================================================================
dead-code:
	@echo "Running vulture dead code detector..."
	.venv/bin/vulture custom_components/ tests/unit/ tests/integration/ --min-confidence 80

unused-deps:
	@echo "Running deptry for unused dependencies..."
	.venv/bin/deptry custom_components/

import-check:
	@echo "Checking import organization and style..."
	.venv/bin/ruff check --select I custom_components/ tests/
	.venv/bin/lint-imports --config pyproject.toml

refurb:
	@echo "Running refurb for Python modernization suggestions..."
	.venv/bin/refurb custom_components/ tests/unit/ tests/integration/

mutation:
	@echo "Running mutation testing..."
	.venv/bin/mutmut run --until=100

mutation-gate:
	@echo "Running mutation gate (per-module thresholds)..."
	python3 .claude/skills/quality-gate/scripts/mutation_analyzer.py . --gate

# ============================================================================
# Test Variants
# ============================================================================
test-parallel:
	@echo "Running tests in parallel mode..."
	PYTHONPATH=. .venv/bin/python -m pytest tests/unit tests/integration -v --tb=short -n auto

test-random:
	@echo "Running tests in random order..."
	PYTHONPATH=. .venv/bin/python -m pytest tests/unit tests/integration -v --tb=short --random-order

# ============================================================================
# E2E Linting
# ============================================================================
e2e-lint:
	@echo "Linting E2E test files..."
	npx eslint tests/e2e/

# ============================================================================
# Pre-commit Hooks
# ============================================================================
pre-commit-install:
	@echo "Installing pre-commit hooks..."
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "pre-commit not found. Install with: pip install pre-commit"; \
		exit 1; \
	}
	pre-commit install

pre-commit-run:
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files

pre-commit-update:
	@echo "Updating pre-commit hooks..."
	pre-commit autoupdate

# ============================================================================
# Quality Baseline
# ============================================================================
quality-baseline:
	@echo "Establishing quality baseline..."
	bash scripts/quality-baseline.sh

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf .hypothesis

htmlcov:
	python3 -m pytest tests/unit tests/integration --cov=custom_components.ev_trip_planner --cov-report=html --cov-fail-under=100
	@echo "Reporte HTML generado en htmlcov/index.html"

# ============================================================================
# Staging Environment Targets (Docker, localhost:8124)
# ============================================================================
STAGING_MAKE_DIR := $(patsubst %/,%,$(dir $(abspath $(firstword $(MAKEFILE_LIST)))))

staging-up:
	@echo "Starting staging environment on localhost:8124 (Docker)..."
	@echo "⚠️  STAGING is separate from E2E (localhost:8123, hass direct)."
	@echo "   See docs/staging-vs-e2e-separation.md for separation rules."
	@if [ ! -d "$$HOME/staging-ha-config" ]; then \
		echo "Staging config not initialized. Running init..."; \
		bash "$(STAGING_MAKE_DIR)/scripts/staging-init.sh"; \
	fi
	cd "$(STAGING_MAKE_DIR)" && docker compose -f docker-compose.staging.yml up -d
	@echo "Waiting for HA to be ready..."
	@READY=0; \
	for i in $$(seq 1 30); do \
		STATUS=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8124/api/ 2>/dev/null || echo "000"); \
		if [ "$$STATUS" = "200" ] || [ "$$STATUS" = "401" ]; then \
			echo "  ✅ HA ready (HTTP $$STATUS)"; \
			READY=1; \
			break; \
		fi; \
		echo "  Attempt $$i: status=$$STATUS (waiting 3s...)"; \
		sleep 3; \
	done; \
	if [ "$$READY" = "0" ]; then \
		echo "  ❌ HA failed to become ready after 30 attempts"; \
		exit 1; \
	fi
	@echo ""
	@echo "Staging ready at http://localhost:8124"
	@echo "Logs: docker logs -f ha-staging"
	@echo "Stop: make staging-down"

staging-down:
	@echo "Stopping staging container..."
	cd "$(STAGING_MAKE_DIR)" && docker compose -f docker-compose.staging.yml down

staging-reset:
	@echo "Resetting staging environment..."
	bash scripts/staging-reset.sh
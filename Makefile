.PHONY: help test test-cover test-verbose test-dashboard test-e2e test-e2e-headed test-e2e-debug e2e e2e-headed e2e-debug e2e-soc e2e-soc-headed e2e-soc-debug staging-up staging-down staging-reset lint mypy format check clean htmlcov layer1 layer1-ci layer2 layer3 layer4 quality-gate quality-gate-ci security-bandit security-audit security-gitleaks security-semgrep typecheck dead-code unused-deps import-check refurb test-parallel test-random e2e-lint pre-commit-install pre-commit-run pre-commit-update quality-baseline

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
	@echo "  make test-e2e-headed - Run E2E with visible browser / E2E con navegador visible"
	@echo "  make test-e2e-debug  - Run E2E in debug mode (Playwright inspector) / E2E en modo debug"
	@echo "  make e2e             - Auto-setup HA and run E2E / Arrancar HA y ejecutar E2E"
	@echo "  make e2e-debug       - Same as e2e but debug mode / Igual que e2e pero en modo debug"
	@echo "  make e2e-soc         - E2E dynamic SOC suite / Suite E2E dynamic SOC"
	@echo "  make e2e-lint        - Lint E2E test files / Lintear archivos E2E"
	@echo ""
	@echo "Quality Gate Layers:"
	@echo "  make layer1          - Layer 1: Test execution (unit + E2E) / Capa 1: Ejecución de tests"
	@echo "  make layer1-ci       - Layer 1 CI: Unit tests only (fast) / Capa 1 CI: Solo unit tests (rápido)"
	@echo "  make layer2          - Layer 2: Test quality (mutation) / Capa 2: Calidad de tests (mutación)"
	@echo "  make layer3          - Layer 3: Code quality (SOLID, DRY) / Capa 3: Calidad de código (SOLID, DRY)"
	@echo "  make layer4          - Layer 4: Security scanning / Capa 4: Escaneo de seguridad"
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
	PYTHONPATH=. .venv/bin/python -m pytest tests -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/

test-cover:
	PYTHONPATH=. .venv/bin/python -m pytest tests --cov=custom_components.ev_trip_planner --cov-report=term-missing --cov-report=html --cov-fail-under=100 --ignore=tests/ha-manual/ --ignore=tests/e2e/

test-verbose:
	python3 -m pytest tests -vv -s --tb=long --ignore=tests/ha-manual/ --ignore=tests/e2e/

test-dashboard:
	python3 -m pytest tests --cov=custom_components.ev_trip_planner --cov-report=html --cov-fail-under=100 --ignore=tests/ha-manual/ --ignore=tests/e2e/
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

e2e-headed:
	./scripts/run-e2e.sh --headed

e2e-debug:
	./scripts/run-e2e.sh --debug

# e2e-soc: dynamic SOC capping suite (requires HA with SOH sensor configured)
# Uses INDEPENDENT setup: separate HA config dir, separate auth state (user-soc.json), separate Playwright config
e2e-soc:
	./scripts/run-e2e-soc.sh

e2e-soc-headed:
	./scripts/run-e2e-soc.sh --headed

e2e-soc-debug:
	./scripts/run-e2e-soc.sh --debug

lint:
	ruff check .
	pylint custom_components/ tests/

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
# Quality Gate Layers
# ============================================================================
# Layer 1: Test execution (unit tests + E2E auto-discovery)
layer1:
	$(MAKE) test
	@echo "Running E2E suites..."
	@$(MAKE) $(filter-out e2e-headed e2e-debug e2e-soc-headed e2e-soc-debug,$(filter e2e-%,$(.PHONY))) 2>/dev/null || echo "No E2E suites found (e2e-% targets)"

# Layer 1 CI: Unit tests only (no E2E for CI speed)
layer1-ci:
	$(MAKE) test

# Layer 2: Test Quality (mutation testing)
layer2:
	@echo "Running Layer 2: Test Quality (mutation testing)..."
	@echo "TODO: Implement mutation testing with mutmut or Stryker"

# Layer 3: Code Quality (SOLID, DRY, antipatterns)
layer3:
	@echo "Running Layer 3: Code Quality analysis..."
	@echo "TODO: Implement code quality analysis"

# Layer 4: Security scanning
layer4:
	$(MAKE) security-bandit security-audit security-gitleaks security-semgrep

# Quality Gate: Full (includes E2E)
quality-gate:
	@echo "Running full quality gate (with E2E)..."
	$(MAKE) layer1 layer2 layer3 layer4

# Quality Gate CI: Fast (excludes E2E)
quality-gate-ci:
	@echo "Running CI quality gate (without E2E)..."
	$(MAKE) layer1-ci layer2 layer3 layer4

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
	.venv/bin/semgrep --config auto --error --verbose custom_components/ tests/

# ============================================================================
# Dead Code and Unused Dependencies
# ============================================================================
dead-code:
	@echo "Running vulture dead code detector..."
	.venv/bin/vulture custom_components/ tests/ --min-confidence 80

unused-deps:
	@echo "Running deptry for unused dependencies..."
	.venv/bin/deptry custom_components/

import-check:
	@echo "Checking import organization and style..."
	ruff check . --select I

refurb:
	@echo "Running refurb for Python modernization suggestions..."
	.venv/bin/refurb custom_components/ tests/

# ============================================================================
# Test Variants
# ============================================================================
test-parallel:
	@echo "Running tests in parallel mode..."
	PYTHONPATH=. .venv/bin/python -m pytest tests -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/ -n auto

test-random:
	@echo "Running tests in random order..."
	PYTHONPATH=. .venv/bin/python -m pytest tests -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/ --random-order

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
	$(MAKE) typecheck
	$(MAKE) dead-code
	$(MAKE) unused-deps
	@echo "Quality baseline established. Review reports above."

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
	python3 -m pytest tests --cov=custom_components.ev_trip_planner --cov-report=html --cov-fail-under=100
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
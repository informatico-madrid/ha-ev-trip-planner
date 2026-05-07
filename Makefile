.PHONY: help test test-cover test-verbose test-dashboard test-e2e test-e2e-headed test-e2e-debug e2e e2e-headed e2e-debug staging-up staging-down staging-reset lint mypy format check clean htmlcov

help:
	@echo "Comandos disponibles:"
	@echo "  make test            - Ejecutar todos los tests Python"
	@echo "  make test-cover      - Ejecutar tests Python con reporte de cobertura"
	@echo "  make test-verbose    - Ejecutar tests Python con salida detallada"
	@echo "  make test-dashboard  - Ejecutar tests y abrir dashboard de cobertura"
	@echo "  make test-e2e        - Ejecutar tests E2E (requiere HA en localhost:8123)"
	@echo "  make test-e2e-headed - Ejecutar tests E2E con navegador visible"
	@echo "  make test-e2e-debug  - Ejecutar tests E2E en modo debug (inspector Playwright)"
	@echo "  make e2e             - Arrancar HA si es necesario y ejecutar E2E (automático)"
	@echo "  make e2e-debug       - Igual que e2e pero en modo debug"
	@echo "  make e2e-soc         - Tests E2E dynamic SOC (suite separada)"
	@echo "  make staging-up          - Arrancar HA staging (Docker, localhost:8124)"
	@echo "  make staging-down        - Detener HA staging"
	@echo "  make staging-reset       - Resetear HA staging"
	@echo "  make lint            - Ejecutar linting (ruff, pylint)"
	@echo "  make mypy            - Ejecutar type checking"
	@echo "  make format          - Formatear código con black e isort"
	@echo "  make check           - Ejecutar todos los checks (test, lint, mypy)"
	@echo "  make clean           - Limpiar archivos generados"
	@echo "  make htmlcov         - Generar reporte HTML de cobertura"

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
	mypy custom_components/ tests/ --exclude tests/ha-manual --no-namespace-packages

format:
	black .
	isort .

check: test lint mypy

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -delete 2>/dev/null || true
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
	@if [ ! -d "$$(eval echo ~/staging-ha-config)" ]; then \
		echo "Staging config not initialized. Running init..."; \
		bash "$(STAGING_MAKE_DIR)/scripts/staging-init.sh"; \
	fi
	cd "$(STAGING_MAKE_DIR)" && docker compose -f docker-compose.staging.yml up -d
	@echo "Waiting for HA to be ready..."
	@for i in $$(seq 1 30); do \
		STATUS=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8124/api/ 2>/dev/null || echo "000"); \
		if [ "$$STATUS" = "200" ] || [ "$$STATUS" = "401" ]; then \
			echo "  ✅ HA ready (HTTP $$STATUS)"; \
			break; \
		fi; \
		echo "  Attempt $$i: status=$$STATUS (waiting 3s...)"; \
		sleep 3; \
	done
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
.PHONY: help test test-cover test-verbose test-dashboard test-e2e lint mypy format check clean htmlcov

help:
	@echo "Comandos disponibles:"
	@echo "  make test            - Ejecutar todos los tests Python"
	@echo "  make test-cover      - Ejecutar tests Python con reporte de cobertura"
	@echo "  make test-verbose    - Ejecutar tests Python con salida detallada"
	@echo "  make test-dashboard  - Ejecutar tests y abrir dashboard de cobertura"
	@echo "  make lint            - Ejecutar linting (ruff, pylint)"
	@echo "  make mypy            - Ejecutar type checking"
	@echo "  make format          - Formatear código con black e isort"
	@echo "  make check           - Ejecutar todos los checks (test, lint, mypy)"
	@echo "  make clean           - Limpiar archivos generados"
	@echo "  make htmlcov         - Generar reporte HTML de cobertura"

test:
	PYTHONPATH=. .venv/bin/python -m pytest tests -v --tb=short --ignore=tests/ha-manual/

test-cover:
	PYTHONPATH=. .venv/bin/python -m pytest tests --cov=custom_components.ev_trip_planner --cov-report=term-missing --cov-report=html --cov-fail-under=80 --ignore=tests/ha-manual/

test-verbose:
	python3 -m pytest tests -vv -s --tb=long

test-dashboard:
	python3 -m pytest tests --cov=custom_components.ev_trip_planner --cov-report=html --cov-fail-under=80
	@echo "Dashboard de cobertura generado en htmlcov/index.html"

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
	python3 -m pytest tests --cov=custom_components.ev_trip_planner --cov-report=html --cov-fail-under=80
	@echo "Reporte HTML generado en htmlcov/index.html"

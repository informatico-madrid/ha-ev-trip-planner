#!/bin/bash

# run_playwright_test.sh - Project Script for E2E Testing
#
# Ejecuta tests de Playwright de forma segura y devuelve un reporte estructurado.
#
# USO:
#   ./scripts/run_playwright_test.sh [test_file] [test_name]
#
# EJEMPLOS:
#   ./scripts/run_playwright_test.sh                # Ejecuta todos los tests
#   ./scripts/run_playwright_test.sh trips.spec.ts  # Ejecuta solo trips.spec.ts
#   ./scripts/run_playwright_test.sh test-create-trip.spec.ts  # Ejecuta un archivo específico
#
# SALIDA:
#   - Archivo playwright-results.json con reporte estructurado
#   - Salida JSON al stdout con resumen de resultados

set -e

# Directorio raíz del proyecto
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Archivo de reporte
REPORT_FILE="playwright-results.json"

# Ejecutar tests de Playwright
# El reporte JSON se genera automáticamente con la configuración de playwright.config.ts

if [[ -n "$1" ]]; then
  # Si se proporciona un test file o nombre de test
  if [[ -n "$2" ]]; then
    # Ejecutar test específico
    echo "🧪 Ejecutando test: $1 - $2"
    npx playwright test "$1" --grep "$2" --reporter=json --output "$REPORT_FILE"
  else
    # Ejecutar solo el archivo de test
    echo "🧪 Ejecutando archivo: $1"
    npx playwright test "$1" --reporter=json --output "$REPORT_FILE"
  fi
else
  # Ejecutar todos los tests
  echo "🧪 Ejecutando todos los tests..."
  npx playwright test --reporter=json --output "$REPORT_FILE"
fi

echo "✅ Tests completados. Reporte: $REPORT_FILE"

# Extraer y mostrar resumen
node scripts/extract_report.js

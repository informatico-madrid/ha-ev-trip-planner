# Implementation Plan: Navegación Manual con Navegador para Panel Nativo

**Branch**: `018-e2e-playwright-testing` | **Date**: 2026-03-21 | **Spec**: [spec.md](../spec.md)
**Input**: Feature specification from `/specs/018-e2e-playwright-testing/spec.md`

## Summary

Crear dos tareas para navegar manualmente con el navegador (Playwright browser automation) a Home Assistant, crear un vehículo siguiendo el config flow, y verificar que el panel de control del vehículo es accesible. Si el panel no es accesible, verificar logs de error, corregir el problema y repetir el proceso hasta lograr el panel accesible.

## Technical Context

**Language/Version**: JavaScript con Playwright
**Primary Dependencies**: Playwright Test, Axios (opcional para API de HA)
**Storage**: N/A (sin persistencia de datos)
**Testing**: N/A (es navegación manual, no test automatizado)
**Target Platform**: Linux/any OS con Node.js y Playwright
**Project Type**: Browser Automation Script
**Performance Goals**: N/A (no es un benchmark)
**Constraints**: Debe funcionar en cualquier entorno con HA accesible
**Scale/Scope**: 2 tareas principales: crear vehículo y verificar panel

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance Review

- [x] **Code Style**: No código Python (es JavaScript/Playwright)
- [x] **Testing**: No se requiere testing (es navegación manual)
- [x] **Documentation**: Se documenta en spec.md y plan.md
- [x] **Conventional Commits**: Se usará formato estándar en commits

**Status**: PASS - No violations detected

## Available Tools for Verification

*Skills and MCPs installed and available for task verification*

| Tool | Type | Status | Purpose |
|------|------|--------|---------|
| homeassistant-ops | skill | available | Operar Home Assistant via API |
| homeassistant-ops | skill | available | Control dispositivos y automatizaciones |
| e2e-testing-patterns | skill | available | Patrones de testing E2E con Playwright |
| python-testing-patterns | skill | available | Patrones de testing con pytest |

## Project Structure

### Documentation (this feature)

```text
specs/018-e2e-playwright-testing/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (resolve NEEDS CLARIFICATION)
├── data-model.md        # Phase 1 output (data entities)
├── quickstart.md        # Phase 1 output (setup guide)
├── contracts/           # Phase 1 output (interface contracts)
├── checklists/          # Specification quality checklists
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
scripts/
└── browser-navigation.js    # Script de navegación con navegador

tests/
└── e2e/
    └── native-panel.spec.js    # Playwright test file (existing)
```

## State Verification Plan

### ⚠️ IMPORTANT: Only 3 Verification Types (CLOSED set)

| Verification Type | When to Use | Example Command (not a new type!) |
|------------------|-------------|-----------------------------------|
| `[VERIFY:TEST]` | Unit/integration tests (pytest) | `pytest tests/ -v --cov` |
| `[VERIFY:API]` | REST API verification (use homeassistant-ops skill) | Use skill to query HA API (no hardcoded curl) |
| `[VERIFY:BROWSER]` | Playwright UI automation | use mcp playwright |

**RULES:**
- ✅ ONLY these 3 types are valid in tasks
- ✅ Details of HOW to verify (services, logs, dashboard, etc.) are decided per-task in the task description
- ❌ DO NOT add more verification types like `[VERIFY:SERVICES]`, `[VERIFY:LOGS]`, `[VERIFY:LOVELACE]`
- ❌ The "Example Command" column shows HOW to use each type - it's NOT a new verification type

### Existence Check

- [ ] Verificar que el panel aparece en el sidebar de Home Assistant
- [ ] Verificar que el panel tiene el nombre correcto del vehículo
- [ ] Verificar que la URL del panel es accesible

### Effect Check

- [ ] Navegar al panel desde el sidebar
- [ ] Verificar que el panel carga sin errores
- [ ] Verificar que muestra información del vehículo
- [ ] Verificar que no hay errores en logs de HA

## Complexity Tracking

> **No complexity violations detected** - This is a straightforward browser automation implementation with standard Playwright patterns.

# Entornos: Staging vs E2E — Guía de Separación

## RECUENTO RÁPIDO (para Agentes IA)

> **Staging = Web REAL, Docker, navegador real.** Aquí el agente NAVEGA y VERIFICA.
> **E2E = Tests deterministas, `hass` directo, containers efímeros.** Aquí solo se EJECUTAN tests.
>
> **SIEMPRE lees `CLAUDE.md` sección "ENVIRONMENT SEPARATION" antes de tocar algo.**

## PROBLEMA FRECUENTE: Agentes Confunden los Entornos

Los agentes IA tienden a:
1. **Usar Docker para E2E** — E2E usa `hass` directo, NUNCA Docker
2. **Crear tests en staging** — Staging NO tiene tests, es para navegación de agentes
3. **Ejecutar `npx playwright test` en staging** — Staging se navega con Playwright MCP, NO con CLI
4. **Conectar E2E al puerto de staging** — E2E usa 8123, staging usa 8124

Si un agente tiene dudas: **lee CLAUDE.md sección "ENVIRONMENT SEPARATION" primero.**

## REGLA ABSOLUTA

> **STAGING NUNCA TIENE TESTS.**  
> **STAGING NUNCA TIENE spec files.**  
> **STAGING NUNCA TIENE playwright config.**  
> **STAGING NUNCA TIENE auth.setup.ts.**  
>
> Si ves `tests/staging/`, `playwright.staging.config.ts`, `verify-environment.spec.ts`, o `test-staging` en el Makefile:  
> **ESTÁ EQUIVOCADO. BORRAR ESO.**
>
> Staging es un entorno de navegación con Playwright MCP, NO de testing.

## Tabla de Referencia

| Propiedad | E2E (Existente) | Staging (Nuevo) |
|-----------|-----------------|-----------------|
| **Propósito** | Verificación determinista de features | Navegación interactiva con agente (Playwright MCP) |
| **Motor** | `hass` directo (Python venv, SIN Docker) | Docker Compose (persistente) |
| **Puerto** | `localhost:8123` | `localhost:8124` |
| **Config** | `/tmp/ha-e2e-config/` (borrado cada ejecución) | `~/staging-ha-config/` (volumen persistente) |
| **Datos** | Mínimos (`input_boolean`, `input_number`) | Realistas (vehicles, trips, automations, sensors) |
| **Tests** | `tests/e2e/` (Playwright feature tests) | **NINGUNO** |
| **Agentes IA** | NO — solo tests automatizados | SÍ — agente navega y verifica |
| **Persistencia** | No (siempre empieza limpio) | Sí (datos sobreviven restarts) |
| **Comando principal** | `make e2e` | `make staging-up` |

## Separación Técnica

### Puertos distintos
- **8123** = E2E (`hass` directo)
- **8124** = Staging (Docker)

### Métodos de arranque distintos
- **E2E**: `scripts/run-e2e.sh` → `hass -c /tmp/ha-e2e-config/`
- **Staging**: `docker compose -f docker-compose.staging.yml up -d`

### Directorios de configuración distintos
- **E2E**: `/tmp/ha-e2e-config/` (se borra y recrea cada ejecución)
- **Staging**: `~/staging-ha-config/` (volumen Docker persistente)

### Playwright: MCP vs CLI

| Aspecto | Agente (MCP Playwright) | Tests E2E (CLI npx) |
|---------|------------------------|---------------------|
| **Motor** | `mcp__playwright` tool en Claude Code | `npx playwright test` |
| **Uso** | Navegación interactiva en staging (localhost:8124) | Tests deterministas en E2E (localhost:8123) |
| **Config** | No necesita config — conecta a la URL directamente | Necesita `playwright.config.ts` |
| **Interactividad** | El agente ve la UI, hace clic, escribe, toma screenshots | Ejecuta y termina, resultados en reporte |
| **Cuándo usar** | El agente necesita verificar que algo funciona en vivo | Se necesita test automatizado reproducible |

**El agente NUNCA debe ejecutar `npx playwright test` para explorar staging.** Usa las herramientas MCP de Playwright para navegar.

## Qué NO existe en Staging

```
❌ tests/staging/                 — NO EXISTE
❌ playwright.staging.config.ts   — NO EXISTE
❌ auth.setup.ts (staging)        — NO EXISTE
❌ verify-environment.spec.ts     — NO EXISTE
❌ make test-staging              — NO EXISTE
```

## Comandos Make

| Acción | E2E | Staging |
|--------|-----|---------|
| Arrancar HA | `make e2e` (auto-start) | `make staging-up` |
| Detener | Se mata con run-e2e.sh | `make staging-down` |
| Reset | `make e2e` (siempre limpio) | `make staging-reset` |
| Tests | `make e2e` (tests deterministas) | **NADA** — el agente navega con MCP |
| Logs | Ver /tmp/logs/ | `docker logs -f ha-staging` |

## Reglas para Agentes de IA

1. **NUNCA** usar `docker compose` para E2E
2. **NUNCA** usar `tests/e2e/` para navegación de agentes
3. **NUNCA** mezclar puertos 8123 y 8124
4. **NUNCA** mezclar directorios de configuración
5. **NUNCA** confundir los propósitos de cada entorno
6. **NUNCA** crear archivos de testing en staging
7. **NUNCA** asumir que staging necesita auth.setup.ts o playwright config

Si un agente encuentra referencias a Docker en el flujo E2E, son residuos de documentación desactualizada y deben ignorarse.

## docker-compose.yml (Residuo)

El archivo `docker-compose.yml` en la raíz del proyecto es un **residuo de pruebas anteriores**.
- NO se usa para E2E
- NO se usa para Staging
- Ver `docker-compose.staging.yml` para el entorno de staging real

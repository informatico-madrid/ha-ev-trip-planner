# 📚 Documentación de Testing E2E

## Archivos Disponibles

| Archivo | Descripción |
|---------|-------------|
| [E2E-TESTING.md](E2E-TESTING.md) | Guía completa de testing E2E con Playwright, arquitectura de tests y workflow |
| [PATTERNS.md](PATTERNS.md) | Patrones de selectores Web-First, anti-patrones y referencias rápidas |
| [DEBUGGING.md](DEBUGGING.md) | Guía de debugging, herramientas y escenarios comunes |

## Quick Links

| Recurso | Ubicación |
|---------|-----------|
| **Agent** | `.claude/agents/ha-e2e-test-architect.md` |
| **Skill** | `~/.agents/skills/ha-e2e-testing/` |
| **Scripts** | `~/.agents/skills/ha-e2e-testing/scripts/` |
| **Memorias** | `.claude/agent-memory-local/ha-e2e-test-architect/` |

## Comandos Rápidos

```bash
# Setup inicial
npx playwright test auth.setup.ts --reporter=list

# Ejecutar tests
bash ~/.agents/skills/ha-e2e-testing/scripts/run_playwright_test.sh tests/e2e/panel.spec.ts

# Ver reporte
bash ~/.agents/skills/ha-e2e-testing/scripts/extract_report.js

# Debug
npx playwright show-trace playwright/trace.zip
```

## 🎯 Patrones Clave

| Patrón | Descripción | Ejemplo |
|--------|-------------|---------|
| **storageState** | Autenticación persistente | `storageState: 'playwright/.auth/user.json'` |
| **globalSetup** | Login + Config Flow automático | `globalSetup: 'tests/global.setup.ts'` |
| **getByRole** | Selectores semánticos | `getByRole('button', { name: /Save/i })` |
| **expect().toBeVisible** | Auto-waiting | `await expect(locator).toBeVisible()` |
| **{baseDir}** | Rutas portables | `{baseDir}/scripts/inspect_dom.js` |

## 📖 Guía de Lectura

1. **Novedades en E2E Testing**: [E2E-TESTING.md](E2E-TESTING.md)
2. **Patrones de Selectores**: [PATTERNS.md](PATTERNS.md)
3. **Debugging y Troubleshooting**: [DEBUGGING.md](DEBUGGING.md)

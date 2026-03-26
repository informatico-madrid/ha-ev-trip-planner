---
name: scripts_location
description: Ubicación correcta de los scripts de la skill ha-e2e-testing
type: reference
---

# Scripts de la Skill ha-e2e-testing - Ubicación CORRECTA

## ❌ ERROR CORREGIDO

Los scripts de la skill `ha-e2e-testing` **NO** están en el proyecto root (`/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/scripts/`)

## ✅ UBICACIÓN REAL

Los scripts están en la carpeta de la skill:

```bash
~/.claude/skills/ha-e2e-testing/scripts/
```

## Lista completa de scripts disponibles

| Script | Ubicación | Uso |
|--------|-----------|-----|
| `check_session.js` | `~/.claude/skills/ha-e2e-testing/scripts/check_session.js` | Valida autenticación antes de tests |
| `create_auth_setup.js` | `~/.claude/skills/ha-e2e-testing/scripts/create_auth_setup.js` | Genera auth.setup.ts con Config Flow |
| `extract_report.js` | `~/.claude/skills/ha-e2e-testing/scripts/extract_report.js` | Resumen estructurado de tests |
| `get_ha_url.js` | `~/.claude/skills/ha-e2e-testing/scripts/get_ha_url.js` | Obtiene URL de HA desde server-info.json |
| `inspect_dom.js` | `~/.claude/skills/ha-e2e-testing/scripts/inspect_dom.js` | Inspecciona DOM real cuando selector falla |
| `run_playwright_test.sh` | `~/.claude/skills/ha-e2e-testing/scripts/run_playwright_test.sh` | Ejecuta tests con reporte JSON |
| `reload_integration.sh` | `~/.claude/skills/ha-e2e-testing/scripts/reload_integration.sh` | Hot-reload sin reiniciar HA |
| `validate_selector.js` | `~/.claude/skills/ha-e2e-testing/scripts/validate_selector.js` | Valida selectores Web-First |

## ¿Por qué mi búsqueda falló?

**Mi error:** Busqué en `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/scripts/` en lugar de `~/.claude/skills/ha-e2e-testing/scripts/`

**Verificación correcta:**
```bash
# ✅ CORRECTO - Scripts de la skill
ls ~/.claude/skills/ha-e2e-testing/scripts/

# ❌ INCORRECTO - Scripts del proyecto (no existen)
ls /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/scripts/
```

## Lección Aprendida

Los scripts de las skills están en `~/.claude/skills/<skill-name>/scripts/`, no en el proyecto root.

Cuando busques scripts de una skill, usa:
```bash
~/.claude/skills/<skill-name>/scripts/
```

## Uso de los Scripts

Para usar los scripts, puedes copiarlos al proyecto o ejecutarlos directamente:

```bash
# Opción 1: Ejecutar directamente desde la skill
node ~/.claude/skills/ha-e2e-testing/scripts/get_ha_url.js
node ~/.claude/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271

# Opción 2: Copiarlos al proyecto (recomendado para acceso rápido)
cp ~/.claude/skills/ha-e2e-testing/scripts/*.js scripts/
cp ~/.claude/skills/ha-e2e-testing/scripts/*.sh scripts/
```

## Scripts Útiles para Debugging

1. **Cuando un selector falla:**
   ```bash
   node ~/.claude/skills/ha-e2e-testing/scripts/inspect_dom.js http://127.0.0.1:8271/config/integrations
   ```

2. **Para validar autenticación:**
   ```bash
   node ~/.claude/skills/ha-e2e-testing/scripts/check_session.js
   ```

3. **Para obtener URL de HA:**
   ```bash
   node ~/.claude/skills/ha-e2e-testing/scripts/get_ha_url.js
   ```

4. **Para ejecutar tests con reporte:**
   ```bash
   bash ~/.claude/skills/ha-e2e-testing/scripts/run_playwright_test.sh tests/e2e/auth.setup.ts
   ```

5. **Para ver resumen de tests:**
   ```bash
   node ~/.claude/skills/ha-e2e-testing/scripts/extract_report.js
   ```

6. **Para validar selectores:**
   ```bash
   node ~/.claude/skills/ha-e2e-testing/scripts/validate_selector.js "getByRole('button', { name: /Save/i })"
   ```

7. **Para generar auth.setup.ts:**
   ```bash
   node ~/.claude/skills/ha-e2e-testing/scripts/create_auth_setup.js "Mi Tesla" "battery_capacity_kwh=75"
   ```

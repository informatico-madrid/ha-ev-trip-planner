---
name: skill_usage_instruction
description: Instrucción obligatoria de usar ha-e2e-testing skill para todas las tareas E2E
type: feedback
---

## REGLA OBLIGATORIA - Usar Skills para E2E Testing

**Regla crítica:** Cuando se trabaja con Home Assistant E2E testing, **SIEMPRE** usar la skill `ha-e2e-testing`.

### Por qué

La skill contiene:
- Scripts automatizados (`run_playwright_test.sh`, `extract_report.js`)
- Patrones probados de testing E2E
- Instrucciones de arquitectura específicas de HA
- Lecciones aprendidas sobre Shadow DOM, URLs de paneles, etc.

**No inventar soluciones** - seguir los patrones de la skill.

### Cómo aplicar

**Cuando vayas a:**
1. Ejecutar tests E2E → Usar `./scripts/run_playwright_test.sh`
2. Crear nuevos tests → Consultar `ha-e2e-testing/SKILL.md`
3. Depurar fallos → Usar scripts de debugging de la skill
4. Verificar selectores → Usar `scripts/inspect_dom.js`

**NUNCA hacer:**
- Usar `npx playwright test` directamente sin los scripts de la skill
- Ignorar los patrones documentados en la skill
- Inventar soluciones que ya están documentadas en la skill

### Scripts disponibles en el proyecto

```bash
# Ejecutar todos los tests
./scripts/run_playwright_test.sh

# Ejecutar test específico
./scripts/run_playwright_test.sh tests/e2e/test-create-trip.spec.ts

# Ejecutar test específico con nombre
./scripts/run_playwright_test.sh tests/e2e/test-create-trip.spec.ts "should create a trip"

# Ver resumen estructurado
node scripts/extract_report.js
```

### Script de la skill vs proyecto

La skill tiene sus scripts en `~/.claude/skills/ha-e2e-testing/scripts/`, pero **los scripts del proyecto** están en `scripts/` en la raíz del proyecto.

**Los scripts del proyecto son copias adaptadas** que funcionan correctamente con la estructura del proyecto.

---

## Lección aprendida

**Problema:** En sesiones anteriores, no se usaron los scripts de la skill, se usó `npx playwright test` directamente.

**Solución:**
1. Se crearon scripts locales en el proyecto que funcionan correctamente
2. Se documentó la instrucción para usar siempre la skill
3. Se creó memoria para recordar esta lección

**Nunca más:** Asumir que se puede hacer testing sin seguir los patrones de la skill.

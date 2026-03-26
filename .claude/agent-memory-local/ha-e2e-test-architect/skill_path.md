---
name: skill_path
description: Ruta correcta del SKILL.md (ha-e2e-testing, no ha-e2e--testing)
type: reference
---

# 🚨 CRÍTICO: Ruta Correcta del SKILL.md

**✅ CORRECTA:** `~/.claude/skills/ha-e2e-testing/SKILL.md`

**❌ INCORRECTA:** `~/.claude/skills/ha-e2e--testing/SKILL.md` (doble guion)

## Corrección Aplicada (2026-03-26)

El prompt del agente ha-e2e-test-architect fue actualizado para usar la ruta correcta.

**Antes (INCORRECTO):**
```markdown
~/.claude/skills/ha-e2e--testing/SKILL.md
```

**Después (CORRECTO):**
```markdown
~/.claude/skills/ha-e2e-testing/SKILL.md
```

## Por qué esto importa

El doble guion `--` en la ruta original causaba que el archivo no se encontrara. La ruta correcta usa un solo guion `ha-e2e-testing`.

Esto es **FUNDAMENTAL** porque:
1. El SKILL.md contiene las reglas arquitectónicas obligatorias
2. Sin acceso correcto al SKILL.md, no se pueden implementar tests válidos
3. Error tipográfico bloquea todo el workflow de E2E testing

## Verificación

```bash
ls -la ~/.claude/skills/ | grep -E "ha-e2e"
# Output esperado:
# drwxrwxr-x  4 malka malka  4096 mar 26 18:44 ha-e2e-testing
```

## Cómo aplicar

En futuras sesiones:
1. **SIEMPRE** usar `ha-e2e-testing` (simple guión)
2. Verificar con `ls ~/.claude/skills/` antes de referenciar
3. Usar autocompletado del shell para evitar errores tipográficos

## Reglas Arquitectónicas del SKILL.md

El archivo contiene:
- Trace Viewer vs Screenshots (no dependencia de screenshots)
- Requisitos de Instalación (Config Flow obligatorio)
- Manejo del Shadow DOM (Lit Elements, getByRole)
- Entorno de Red y Timeouts (auto-waiting, cero waitForTimeout)
- Snippets oficiales de referencia
- Herramientas disponibles y workflow

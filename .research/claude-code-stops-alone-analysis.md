# Research: Claude Code Se Detiene Solo — Análisis de Causas y Configuraciones

**Fecha:** 2026-05-17
**Pregunta:** ¿Por qué Claude Code a veces se detiene solo mientras trabaja? ¿Hay algún setting nuevo?
**Categoría:** Troubleshooting / Configuración de Claude Code

---

## Resumen Ejecutivo

Claude Code puede detenerse solo por varias razones, algunas relacionadas con settings y otras con comportamiento del agente. El setting `disableBypassPermissionsMode` ya está documentado, pero hay otros mecanismos que pueden causar detuvo espontáneo.

---

## Causas Identificadas

### 1. Stop Hooks (Hooks de Detención)

Claude Code tiene ganchos que pueden ejecutar cuando el agente considera detenerse. Esto es un mecanismo NATIVO de Claude Code, **no un bug**.

**Comportamiento:**
- El hook `Stop` se invoca cuando el agente cree que completó su tarea
- Puede ser configurado para **aprobar** o **bloquear** la detención
- Un hook mal configurado puede causar que el agente se detenga prematuramente

**Estructura del hook:**
```json
{
  "Stop": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Verify task completion: tests run, build succeeded. Return 'approve' to stop or 'block' with reason."
        }
      ]
    }
  ]
}
```

**Decisión:**
```json
{
  "decision": "approve|block",
  "reason": "Explanation",
  "systemMessage": "Additional context"
}
```

---

### 2. Agente Cree que Completó la Tarea

El modelo puede considerar que terminó aunque el usuario quiera continuar. Causas comunes:

- **Resultado vago/difuso** — El agente da una respuesta superficial
- **Herramienta no usada** — No ejecutó las herramientas necesarias
- **Contexto insuficiente** — No tiene suficiente info para continuar

---

### 3. Permisos y Modo Bypass

El setting `disableBypassPermissionsMode` en `"disable"` significa que NO se puede saltar los permisos. Pero esto no causa detuvo espontáneo.

**Settings de permisos:**
```json
{
  "permissions": {
    "disableBypassPermissionsMode": "disable",
    "ask": ["Bash"],
    "deny": ["WebSearch", "WebFetch"]
  }
}
```

---

### 4. Errores de API / Conexión

De la documentación de hooks (MCP integration):

> "Handling connection failures gracefully is essential for robust MCP integrations. When an MCP server becomes unavailable..."

Si hay un error de conexión temporal, Claude Code puede detenerse.

---

### 5. Cache Control TTL Ordering Fix

Del CHANGELOG de Claude Code:

> "Fixed an intermittent API 400 error related to cache control TTL ordering that could occur when a parallel request completed during request setup"

Este era un bug conocido que causaba errores intermitentes.

---

## Recomendaciones para Diagnosticar

### Paso 1: Verificar si hay Stop Hooks activos

Revisar en `~/.claude/settings.json` si hay configuración `Stop` en hooks.

### Paso 2: Ver logs de Claude Code

Ejecutar con `--verbose` para ver más información:
```bash
claude --verbose
```

### Paso 3: Verificar versión

Asegurarse de tener la última versión:
```bash
claude --version
claude --updater-check
```

### Paso 4: Revisar el CHANGELOG oficial

Buscar en [GitHub CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md) si hay issues relacionados.

---

## Configuración Recomendada para Evitar Detenerse Solo

Si el problema es que el agente se detiene prematuramente, considera agregar un Stop hook que bloquee la detención hasta que se cumplan criterios:

```json
// En ~/.claude/settings.json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Review the conversation. If the user's request is not fully complete, return 'block' with reason. Only return 'approve' if ALL requested tasks are done."
          }
        ]
      }
    ]
  }
}
```

---

## Referencias

- [Anthropic Claude Code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/claude-code/CHANGELOG.md)
- [Hook Development SKILL](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/hook-development/SKILL.md)
- [Settings — Permissions and Sandbox](https://context7.com/anthropics/claude-code/llms.txt)
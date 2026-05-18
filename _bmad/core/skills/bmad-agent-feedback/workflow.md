# Workflow: Agent Feedback Hook

> El maestro es CLAUDE.md — este archivo solo tiene plantilla de formato.

## Hook: PRE-TASK

1. Leer `.harness/agent-feedback/sessions/*.md` (últimos 5 si existen)
2. Leer `.harness/agent-feedback/patterns.md`
3. Sintetizar insights en 2-3 líneas

## Hook: POST-TASK

1. Crear `.harness/agent-feedback/sessions/YYYY-MM-DD_HH-MM.md`
2. Llenar según [plantilla README.md](.harness/agent-feedback/README.md)
3. Actualizar patterns.md si hay patrón nuevo

## Formato de Sesión

```markdown
# Feedback Session: YYYY-MM-DD_HH-MM

## Agente: [code|ask|architect|etc]
## Tarea: [descripción]
## Duración: [estimada]

### Lo que funcionó bien
-

### Qué causó confusión o errores
-

### Información que faltaba
-

### Constraints o reglas que no funcionaron
-

### Mejoras propuestas
-

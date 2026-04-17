# Plan de Migración a BMad Method — ha-ev-trip-planner

**Fecha**: 2026-04-16
**Estado**: En progreso

## Objetivo

Migrar toda la documentación existente (Smart Ralph + Speckit + código sin documentar) al método BMad, generando documentación estructurada y contexto optimizado para LLMs.

## Estado Actual del Proyecto

- **Versión**: v0.5.1 (manifest.json)
- **Milestones completados**: M0-M4 + SOLID Refactor
- **Tests**: 793+ Python + 10 E2E Playwright
- **Specs existentes**: 30+ specs en `specs/` (Smart Ralph/Speckit)
- **Docs existentes**: 14 archivos en `docs/`
- **Instalación**: Home Assistant Container (NO Supervisor)

## Pasos de Migración

### ✅ Paso 1: Generar Project Context (`bmad-generate-project-context`)
- **Estado**: Completado
- **Salida**: `_bmad-output/project-context.md` (402 líneas)
- **Contenido**: 13 reglas críticas, stack tecnológico, arquitectura, testing, workflow, mapa de documentación

### 🔄 Paso 2: Documentar Proyecto Brownfield (`bmad-document-project`)
- **Estado**: Pendiente de ejecución en sesión nueva
- **Modo**: `initial_scan` (primera vez)
- **Salida esperada**: Documentación estructurada en `_bmad-output/planning-artifacts/`
- **Nota**: Requiere sesión de contexto fresco para ejecutarse correctamente

### 📋 Paso 3: Integración y Consolidación
- Revisar documentación generada vs. existente
- Crear índice que conecte ambas metodologías
- Validar que no haya conflictos

### 📋 Paso 4: Crear Índice BMad
- Generar índice de toda la documentación BMad
- Referenciar specs existentes de Smart Ralph
- Establecer prioridad: implementación > documentación

## Principios Clave

1. **La implementación es la fuente de verdad** — la documentación puede estar desactualizada
2. **Usar fechas para resolver contradicciones** — lo más reciente tiene más peso
3. **No reemplazar, complementar** — Smart Ralph/Speckit coexisten con BMad
4. **Verificar contra el código** — siempre confirmar claims contra el codebase real

## Configuración BMad

- **project_knowledge**: `{project-root}/docs`
- **planning_artifacts**: `{project-root}/_bmad-output/planning-artifacts`
- **implementation_artifacts**: `{project-root}/_bmad-output/implementation-artifacts`
- **output_folder**: `{project-root}/_bmad-output`
- **communication_language**: Spanish
- **document_output_language**: English

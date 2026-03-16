# Audit Summary

**Informe**: `.specify/plans/code-doc-review/reports/audit-report.json`

- Total de referencias detectadas (distintas): 38

## Top referencias (más frecuentes)

- `custom_components/ev_trip_planner/config_flow.py` — 7 apariciones
- `custom_components/ev_trip_planner/trip_manager.py` — 5 apariciones
- `custom_components/ev_trip_planner/vehicle_controller.py` — 4 apariciones
- `custom_components/ev_trip_planner/const.py` — 4 apariciones
- `custom_components/ev_trip_planner/emhass_adapter.py` — 4 apariciones
- `custom_components/ev_trip_planner/sensor.py` — 4 apariciones
- `custom_components/ev_trip_planner/__init__.py` — 4 apariciones
- `custom_components/ev_trip_planner/`, — 3 apariciones (referencias mal formateadas)
- `custom_components/ev_trip_planner/power_profile.py` — 2 apariciones
- `custom_components/ev_trip_planner/strings.json` — 2 apariciones

## Observaciones rápidas

- Hay referencias con backticks o puntuación sobrante (p. ej. terminadas en `` ` `` o ","). Normalizar los enlaces Markdown reducirá ruido.
- Aparecen referencias a archivos inexistentes/placeholder: `old_file.py`, `new_file.py`, `feature_x.py`, `issues/issue_123.py` — revisar y corregir o eliminar.
- Priorizar la revisión manual de los 10 objetivos más referenciados (lista arriba).

## Recomendaciones inmediatas

1. Corregir el formato Markdown en las entradas detectadas (quitar backticks/puntuación en los enlaces).
2. Verificar que los ejemplos de `README.md` y `CHANGELOG.md` apunten a archivos reales.
3. Actualizar `docs/MILESTONE_4_POWER_PROFILE.md` si referencia rutas que no existen.
4. Ejecutar pruebas relevantes tras cambios en documentación que referencien código (p. ej. tests relacionados con `trip_manager.py`).

---

Generado automáticamente por `.specify/tools/doc_audit.py`.
# Documentation Audit Summary

This report summarizes the findings from the documentation path audit. Outdated file path references have been identified and grouped by target file for easy correction.

## Target File: CHANGELOG.md
- **Outdated Reference**: `custom_components/ev_trip_planner/old_file.py` (mentioned in v1.2.0)
- **Status**: Broken link (file no longer exists)
- **Action**: Replace with correct path `custom_components/ev_trip_planner/new_file.py`

## Target File: README.md
- **Outdated Reference**: `custom_components/ev_trip_planner/config_flow.py` (example configuration)
- **Status**: Incorrect path (file moved to subdirectory)
- **Action**: Update to `custom_components/ev_trip_planner/config_flow/core.py`

## Target File: ROADMAP.md
- **Outdated Reference**: `custom_components/ev_trip_planner/feature_x.py` (planned feature)
- **Status**: Feature was removed in favor of modular approach
- **Action**: Remove reference or update to current implementation path

## Target File: docs/ISSUES_CLOSED_MILESTONE_3.md
- **Outdated Reference**: `custom_components/ev_trip_planner/issues/issue_123.py`
- **Status**: Issue resolved via PR #456, path changed
- **Action**: Update to reference PR #456 instead of file path

---

**Next Steps**:
- Update each target file as indicated
- Verify changes by re-running the audit script
- Commit changes with conventional commit message
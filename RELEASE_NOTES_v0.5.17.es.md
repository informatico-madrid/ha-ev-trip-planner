# Release Notes v0.5.17 — Datetime Fix & Race Condition Resolution

## Resumen

Esta versión corrige un bug crítico de timezone en los cálculos de datetime del TripManager, resuelve condiciones de carrera en el coordinator, y mejora la infraestructura de tests E2E para sensores EMHASS.

## Cambios Destacados

### Fixed
- **Bug datetime naive/aware**: Corregido `datetime.now()` a `datetime.now(timezone.utc)` en [`trip_manager.py`](custom_components/ev_trip_planner/trip_manager.py:1470-1471) para evitar errores `TypeError` en comparaciones de timezone.
- **Race condition coordinator**: Resuelta condición de carrera en el coordinator que podía causar estados inconsistentes durante actualizaciones concurrentes.
- **Cálculo SOC en eliminación de sensores**: Corregido el cálculo de SOC al eliminar sensores huérfanos.
- **Mutación in-place**: Reemplazada mutación in-place con dict expansion en `async_publish_all_deferrable_loads` y `async_cleanup_vehicle_indices`.

### Added
- **Tests regression datetime**: Nuevo archivo [`tests/test_trip_manager_datetime_tz.py`](tests/test_trip_manager_datetime_tz.py) con tests de regresión para datetime naive/aware.
- **Refactor `_parse_trip_datetime`**: Método centralizado para parsing de datetime en TripManager con type hints para compliance SOLID.
- **Tests E2E EMHASS dinámicos**: Tests E2E con descubrimiento dinámico de entity IDs en lugar de hardcoded values.
- **100% coverage**: Cobertura del 100% en las líneas críticas del datetime handling.

### Changed
- **Test infrastructure**: Mejoras en tests E2E con fechas dinámicas usando `getFutureIs` en lugar de fechas hardcoded.
- **Chore files cleanup**: Eliminación de archivos obsoletos de presentaciones (Saga, Freya) y skills no utilizados.

## Detalles Técnicos

### Archivos Modificados
- `custom_components/ev_trip_planner/trip_manager.py` - Datetime handling y refactoring
- `custom_components/ev_trip_planner/coordinator.py` - Race condition fixes
- `custom_components/ev_trip_planner/emhass_adapter.py` - Mutación in-place fix
- `custom_components/ev_trip_planner/__init__.py` - Cleanup imports
- `tests/test_trip_manager_datetime_tz.py` - Nuevo archivo con tests de regresión
- `tests/e2e/emhass-sensor-updates.spec.ts` - Tests E2E dinámicos
- `_bmad/` - Eliminación de archivos obsoletos de agentes

### Archivos Eliminados
- `_bmad/cis/agents/artifact-analyzer.md`
- `_bmad/cis/agents/opportunity-reviewer.md`
- `_bmad/cis/agents/skeptic-reviewer.md`
- `_bmad/cis/agents/web-researcher.md`
- `_bmad/core/agents/distillate-compressor.md`
- `_bmad/core/agents/round-trip-reconstructor.md`
- `_bmad/bmb/agents/tech-writer-sidecar/documentation-standards.md`
- `docs/e2e-date-diagnosis-final.md`

## Notas de Migración

- No hay cambios breaking conocidos
- Los usuarios existentes pueden actualizar sin acciones adicionales
- Se recomienda reiniciar Home Assistant tras actualizar para asegurar estado consistente del coordinator

## Referencias

- Commit: `df4f68d Fix sensor deletion calculating soc & fix: datetime bug, coordinator race condition, test infrastructure (#34)`
- Specifications: `specs/e2e-ux-tests-fix/`

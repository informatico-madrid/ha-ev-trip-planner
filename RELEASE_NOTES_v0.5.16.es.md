# Release Notes v0.5.16 — Panel Fixes & EMHASS Cleanup

## Resumen

Esta versión corrige problemas críticos del panel que causaban pantalla en blanco al cambiar pestañas, improve la publicación de datos EMHASS tras reinicios de Home Assistant, y añade limpieza automática de sensores huérfanos durante la eliminación de integraciones.

## Cambios Destacados

### Fixed
- **Panel en blanco**: Añadido `disconnectedCallback()` faltante para prevenir pantalla en blanco al cambiar entre pestañas del panel Lovelace.
- **Publicación EMHASS tras restart**: Asegurado que `publish_deferrable_loads` se llama tras el setup del adaptador EMHASS para mantener datos actualizados tras reinicios.
- **Perfil de potencia trip 2**: Corregido el cálculo de watts del segundo viaje que devolvía valores incorrectos.
- **Safety margin percent**: Aplicado correctamente el margen de seguridad desde la configuración del vehículo a los cálculos de energía.
- **Ventanas de carga secuenciales**: Corregida la lógica de ventanas de carga para múltiples viajes sequential.
- **Limpieza de caché EMHASS**: Limpiados datos EMHASS en caché al eliminar viajes para prevenir estado stale.
- **Coincidencia vehicle_id/entry_id**: Corregido el manejo de la relación entre vehicle_id y entry_id en la limpieza de sensores.

### Added
- **Normalización centralizada de vehicle_id**: Mejorada la centralización del normalizado de vehicle_id y actualizado TripManager para usar YamlTripStorage.
- **Tests de integración para cleanup**: Nuevos tests para verificar el comportamiento correcto durante la eliminación de integraciones y trips.
- **Tests de persistencia post-reinicio**: Tests para garantizar que los datos persisten correctamente tras reinicios de HA.
- **Reglas E2E para Shadow DOM**: Documentación de reglas para selectores E2E en el panel con Shadow DOM.

## Detalles Técnicos

### Archivos Modificados
- `custom_components/ev_trip_planner/__init__.py` - Setup y cleanup del adaptador EMHASS
- `custom_components/ev_trip_planner/coordinator.py` - Refresh del coordinator
- `custom_components/ev_trip_planner/emhass_adapter.py` - Caché por viaje y cleanup
- `custom_components/ev_trip_planner/frontend/panel.js` - Lifecycle del panel
- `custom_components/ev_trip_planner/sensor.py` - Sensores adicionales
- `custom_components/ev_trip_planner/services.py` - APIs de servicios
- `custom_components/ev_trip_planner/trip_manager.py` - Gestión de trips
- `custom_components/ev_trip_planner/utils.py` - Utilidades de normalización

### Tests Añadidos
- `tests/test_integration_uninstall.py` - Tests de desinstalación
- `tests/test_post_restart_persistence.py` - Persistencia post-reinicio
- `tests/test_emhass_adapter.py` - Tests del adaptador EMHASS
- `tests/test_trip_manager_core.py` - Tests core del TripManager
- `tests/e2e/zzz-integration-deletion-cleanup.spec.ts` - Tests E2E de cleanup

## Notas de Migración

- No hay cambios breaking conocidos
- Los usuarios existentes pueden actualizar sin acciones adicionales
- Se recomienda limpar sensores EMHASS huérfanos tras actualizar si existen

## Referencias

- Commit: `7532e42 Fix panel in blank (#32)`
- Especificaciones relacionadas: `specs/e2e-trip-crud/`, `plans/bmad-migration-plan-phase3.md`

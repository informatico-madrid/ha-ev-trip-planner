# Plan: Integration with ev-trip-planner-integration-fixes

**Epic**: specs/_epics/emhass-deferrable-integration/epic.md

## Goal

Como sistema, necesito integrar los fixes de user stories US-6, US-7, US-8, US-9, US-10 del epic anterior.

## User Stories to Integrate

From `specs/ev-trip-planner-integration-fixes/requirements.md` (Extended Scope):

**US-6**: Display p_deferrable schedule on trip cards (see Spec 5 above)

**US-7**: EMHASS JSON Format Transformation - Display sensor IDs in panel for EMHASS config

**US-8**: Automation template for charge control (see Spec 6 above)

**US-9**: Improved charging window calculation - Calculate windows between trips

**US-10**: SOC-Based Trip Planning - Integrate SOC sensor, warn if external charging needed

## Acceptance Criteria

1. **Given** el usuario elimina un vehiculo, **when** se confirma la eliminacion, **then** se eliminan todos los sensores, el adaptador EMHASS y los datos asociados

2. **Given** el usuario aniade un vehiculo, **when** se completa la configuracion, **then** se crean todos los sensores necesarios incluyendo `EmhassDeferrableLoadSensor`

3. **Given** el dashboard se carga, **when** hay vehiculos configurados, **then** los datos se sincronizan correctamente desde el TripManager

4. **Given** un viaje cambia de estado, **when** el panel se actualiza, **then** el sensor correspondiente muestra el estado correcto

5. **Given** hay un error de carga, **when** se detecta, **then** se muestra una notificacion adecuada

## Integration Points

- `TripManager` → `EMHASSAdapter` initialization
- `TripManager.set_emhass_adapter()` called during setup
- Sensor creation/deletion synced with vehicle CRUD
- Dashboard data refresh on trip state changes

**Cascade delete**: When vehicle removed, must delete:
- All trip sensors
- All trip data from storage
- EMHASS adapter indices
- Any persistent state (hora_regreso, soc_en_regreso)

**Dependencies**: All previous specs (1-6)

## Size
Medium - integration work across components

## TODO

- [ ] Integrate Spec 1-6 implementations
- [ ] Ensure cascade delete works correctly
- [ ] Test sensor creation on vehicle add
- [ ] Test dashboard data synchronization
- [ ] Test trip state change updates
- [ ] End-to-end integration tests

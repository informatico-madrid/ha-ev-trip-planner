# Plan: EMHASS Sensor Enhancement

**Epic**: specs/_epics/emhass-deferrable-integration/epic.md

## Goal

Como sistema, necesito que `sensor.emhass_perfil_diferible_{vehicle_id}` tenga el formato correcto con indices `p_deferrable{n}` estables y se actualice automaticamente.

## Acceptance Criteria

1. **Given** el usuario tiene 3 viajes activos, **when** se genera el perfil, **then** el sensor tiene `p_deferrable0`, `p_deferrable1`, `p_deferrable2` con valores correctos

2. **Given** un viaje se elimina, **when** se regenera el perfil, **then** los indices se reasignan con soft delete (indices marcados "released" con timestamp, NO reutilizados inmediatamente)

3. **Given** el coche esta en casa y enchufado y el SOC cambia, **when** se recalcula, **then** el sensor se actualiza con el nuevo `power_profile_watts`

4. **Given** el `deferrables_schedule` se genera, **when** se mira una hora especifica, **then** se ve el valor de `p_deferrable{n}` para esa hora

5. **Given** EMHASS devuelve un plan MPC, **when** el sensor se actualiza, **then** la automatizacion puede leer `p_deferrable{n}` por hora

## Interface Contracts

**Sensor attributes**:
```yaml
sensor.emhass_perfil_diferible_{vehicle_id}:
  state: "ready" | "active" | "error"
  attributes:
    power_profile_watts: [0.0, 0.0, 3600.0, ...]  # 168 values
    deferrables_schedule:
      - date: "2026-03-29T14:00:00+01:00"
        p_deferrable0: "0.0"
        p_deferrable1: "3600.0"
      ...
    trips_count: 2
    vehicle_id: "coche1"
    last_update: "2026-03-29T14:00:00+01:00"
    emhass_status: "ok"
```

**Index Stability (Soft Delete)**:
- Released indices stored in `_released_indices` dict with timestamp
- Default cooldown: 24 hours before reuse
- Only indices past cooldown can be reassigned

**Trigger recalculation on**:
- Trip added → `async_publish_new_trip_to_emhass()`
- Trip modified → `async_update_deferrable_load()`
- Trip deleted → mark index as "released" (NOT reuse immediately)
- SOC changed AND car home AND plugged → `async_generate_power_profile()`

**Dependencies**: Spec 3: SOC Milestone Algorithm

## Size
Medium - sensor enhancement and integration

## TODO

- [ ] Add `last_update` and `emhass_status` attributes to sensor
- [ ] Implement soft delete for indices (don't reuse immediately)
- [ ] Add released indices cooldown mechanism
- [ ] Enhance `EmhassDeferrableLoadSensor.async_update()`
- [ ] Add unit tests for index stability

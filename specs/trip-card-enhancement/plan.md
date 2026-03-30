# Plan: Trip Card Enhancement

**Epic**: specs/_epics/emhass-deferrable-integration/epic.md

## Goal

Como usuario, necesito ver en la tarjeta del viaje cual es su indice `p_deferrable{n}` y el horario de carga asignado.

## Acceptance Criteria

1. **Given** el usuario crea un viaje, **when** la tarjeta se muestra, **then** aparece el indice de carga diferible (ej: "Carga diferible: p_deferrable0")

2. **Given** el viaje tiene ventana de carga asignada, **when** se muestra la tarjeta, **then** aparece la hora de inicio y fin de la ventana (ej: "Ventana: 18:00 - 22:00")

3. **Given** el viaje tiene deficit propagado, **when** se muestra la tarjeta, **then** se indica el SOC objetivo (ej: "SOC objetivo: 60%")

4. **Given** el usuario edita el viaje, **when** se guarda, **then** la tarjeta se actualiza con el nuevo indice y ventana

5. **Given** el EMHASS no esta configurado, **when** se muestra la tarjeta, **then** no se muestra informacion de carga diferible

## Interface Contracts

**Trip card additional attributes**:
```yaml
trip_card:
  p_deferrable_index: 0
  charging_window:
    start: "18:00"
    end: "22:00"
  soc_target: 60
  kwh_for_trip: 15.0
  deficit_from_previous: 5.0
```

**Data access for p_deferrable_index**:
- Option 1: Via `EmhassDeferrableLoadSensor` data
- Option 2: Via `emhass_adapter.get_assigned_index(trip_id)` method
- Recommendation: Use EMHASSAdapter method for index resolution

**Dependencies**: Spec 4: EMHASS Sensor Enhancement

## Size
Small - UI display logic

## TODO

- [ ] Add p_deferrable_index to TripSensor._attr_extra_state_attributes
- [ ] Add charging_window display to trip card
- [ ] Add soc_target display
- [ ] Add deficit_from_previous display
- [ ] Handle EMHASS not configured case
- [ ] Add unit tests for UI display logic

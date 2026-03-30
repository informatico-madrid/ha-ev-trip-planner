# Plan: Automation Template

**Epic**: specs/_epics/emhass-deferrable-integration/epic.md

## Goal

Como usuario, necesito una automatizacion YAML que controle la carga fisica del vehiculo segun el plan MPC de EMHASS.

## Acceptance Criteria

1. **Given** EMHASS devuelve un plan con `sensor.emhass_plan_{vehicle}_mpc_congelado`, **when** la automatizacion se ejecuta, **then** para cada hora lee el valor de `p_deferrable{n}` correspondiente

2. **Given** `p_deferrable{n}` es > 100W para la hora actual, **when** el coche esta en casa y enchufado, **then** la automatizacion inicia la carga

3. **Given** `p_deferrable{n}` es 0W para la hora actual, **when** la carga esta activa, **then** la automatizacion detiene la carga

4. **Given** el coche no esta en casa o no esta enchufado, **when** EMHASS programa carga, **then** se envia notificacion al usuario

5. **Given** el usuario activa modo manual, **when** la automatizacion se ejecuta, **then** NO interfiere con el control manual

## Sensor Naming Clarification

Two sensor patterns exist in the system:
1. `sensor.emhass_plan_{vehicle}_mpc_congelado` - per-vehicle MPC frozen plan (used in docs/borrador)
2. `sensor.emhass_deferrable{index}_schedule` - per-index schedule (used in schedule_monitor.py)

Implementation must support both patterns or provide mapping between them.

## Interface Contracts

**Automation structure**:
```yaml
alias: "EV Trip Planner - Control Carga {vehicle_id}"
triggers:
  - minutes: "5"
    trigger: time_pattern
  - minutes: "35"
    trigger: time_pattern
conditions:
  - condition: template
    value_template: "{{ states('sensor.emhass_plan_{vehicle}_mpc_congelado') not in ['unavailable', 'unknown'] }}"
  - condition: state
    entity_id: input_boolean.carga_{vehicle}_modo_manual
    state: "off"
actions:
  - variables:
      potencia_planificada: "{{ read p_deferrable{n} for current hour }}"
      coche_en_casa: "{{ is_state(home_sensor, 'on') }}"
      coche_enchufado: "{{ is_state(plugged_sensor, 'on') }}"
  - choose:
      - conditions: [...charging start conditions...]
        sequence: [start charging]
      - conditions: [...charging stop conditions...]
        sequence: [stop charging]
```

**Requirements from EMHASS docs**:
- Lee de `sensor.emhass_plan_{vehicle}_mpc_congelado` attribute `plan_deferrable{n}_horario_mpc`
- Formato: `[{"date": "2026-03-29T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]`
- `potencia_planificada > 100` = EMHASS quiere cargar
- `potencia_planificada == 0` = EMHASS NO quiere cargar

**Dependencies**: Spec 4: EMHASS Sensor Enhancement

## Size
Medium - automation template with edge cases

## TODO

- [ ] Create YAML automation template based on docs/borrador/cargasAplazables.yaml
- [ ] Support both sensor naming patterns
- [ ] Implement charge start/stop logic
- [ ] Handle manual mode override
- [ ] Add notification for missed charging opportunities
- [ ] Document required HA entities (home_sensor, plugged_sensor, soc_sensor, etc.)

# EMHASS Sensor Naming Patterns

This document describes the two sensor naming patterns used in the EMHASS integration.

## Pattern 1: Per-Vehicle MPC Frozen Plan (Primary)

**Sensor**: `sensor.emhass_plan_{vehicle}_mpc_congelado`

**Attributes**:
- `plan_deferrable0_horario_mpc` - Array of hourly p_deferrable0 values
- `plan_deferrable1_horario_mpc` - Array of hourly p_deferrable1 values (if multiple deferrables)
- Format: `[{"date": "2026-03-29T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]`

**Usage in automation**:
```yaml
variables:
  p_deferrable0: "{{ state_attr('sensor.emhass_plan_' ~ vehicle_id ~ '_mpc_congelado', 'plan_deferrable0_horario_mpc')[hora_actual] | int(0) }}"
```

## Pattern 2: Per-Index Schedule

**Sensor**: `sensor.emhass_deferrable{index}_schedule`

**Attributes**:
- `horario_mpc` - Array of hourly values for that deferrable index
- `potencia_programada` - Current scheduled power

**Usage**:
```yaml
variables:
  p_deferrable0: "{{ state_attr('sensor.emhass_deferrable0_schedule', 'horario_mpc')[hora_actual] | int(0) }}"
```

## Mapping Between Patterns

| Pattern 1 Attribute | Pattern 2 Attribute |
|--------------------|---------------------|
| `plan_deferrable{n}_horario_mpc` | `horario_mpc` (index {n}) |
| Per-vehicle sensor | Per-index sensor |

## Choosing a Pattern

- **Pattern 1** is used by the EMHASS MPC optimizer directly (frozen plan per vehicle)
- **Pattern 2** is used by the schedule_monitor.py component for per-deferrable tracking
- Both patterns provide equivalent data, just organized differently

## Example Entity IDs

```yaml
# Pattern 1 examples
sensor.emhass_plan_ovms_chispitas_mpc_congelado
sensor.emhass_plan_coche_morgan_mpc_congelado

# Pattern 2 examples
sensor.emhass_deferrable0_schedule
sensor.emhass_deferrable1_schedule
```
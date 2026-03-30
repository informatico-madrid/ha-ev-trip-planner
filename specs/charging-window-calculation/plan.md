# Plan: Charging Window Calculation

**Epic**: specs/_epics/emhass-deferrable-integration/epic.md

## Goal

Como sistema, necesito calcular la ventana de carga disponible como el tiempo desde que el coche regresa a casa hasta que inicia el siguiente viaje.

## Acceptance Criteria

1. **Given** el coche esta en casa desde las 18:00 y el siguiente viaje es a las 22:00, **then** la ventana de carga es de 4 horas

2. **Given** el viaje anterior aun no ha regresado (esperando 6h), **then** la ventana NO comienza hasta que el coche regrese

3. **Given** el coche regresa a casa y el SOC cambia, **when** se recalcula la ventana, **then** el perfil de carga se actualiza inmediatamente

4. **Given** hay multiple viajes en el mismo dia, **when** se calcula la ventana, **then** cada viaje tiene su propia ventana desde que termina el anterior

5. **Given** el coche esta en casa pero NO hay viajes pendientes, **when** se genera el perfil, **then** todas las horas son 0 (sin carga)

## Interface Contracts

**Function signature**:
```python
async def calcular_ventana_carga(
    trip: Dict[str, Any],
    soc_actual: float,
    hora_regreso: datetime,
    charging_power_kw: float
) -> Dict[str, Any]:
    """
    Returns:
        {
            "ventana_horas": float,
            "kwh_necesarios": float,
            "horas_carga_necesarias": float,
            "inicio_ventana": datetime,
            "fin_ventana": datetime,
            "es_suficiente": bool
        }
    """
```

**Dependencies**: Spec 1: SOC Integration Baseline

## Size
Medium - window calculation logic with multiple edge cases

## TODO

- [ ] Implement `calcular_ventana_carga()` function
- [ ] Read `hora_regreso` from persistent state (set by Spec 1)
- [ ] Handle multi-trip window chaining
- [ ] Handle edge case when no trips pending
- [ ] Add unit tests

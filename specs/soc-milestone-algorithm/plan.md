# Plan: SOC Milestone Algorithm

**Epic**: specs/_epics/emhass-deferrable-integration/epic.md

## Goal

Como sistema, necesito propagar el deficit de carga entre viajes consecutivos para que cada viaje tenga su SOC objetivo calculado correctamente.

## Acceptance Criteria

1. **Given** un viaje de manana a las 12:00 que necesita 30% SOC y un viaje de noche a las 22:00 que necesita 80% SOC, **when** se calcula el perfil, **then**:
   - Entre viajes hay 4 horas de ventana, cargando 10% SOC/hora = +40% SOC
   - Viaje manana: necesita 30% + buffer 10% = 40% target
   - Viaje noche: 20% (llegada) + 40% (carga) = 60% pero necesita 80% → deficit 20%
   - El deficit de 20% se SUMA al viaje de manana: target manana = 40% + 20% = **60%**

2. **Given** el deficit se ha propagado, **when** se publica el perfil, **then** el viaje de manana tiene mas kWh necesarios que el viaje nocturno

3. **Given** el coche carga mas rapido que 10% SOC/hora, **when** se recalcula, **then** se usa la velocidad de carga real del usuario

4. **Given** no hay viajes previos que causen deficit, **when** se calcula, **then** solo se usa el buffer standard (ej: 10% sobre energia del viaje)

## Algorithm Details

```
Para cada viaje en orden cronologico:
    1. Calcular SOC objetivo base (energia_viaje + buffer)
    2. Calcular SOC al inicio del viaje (desde llegada anterior)
    3. Si SOC_inicio + capacidad_carga_en_ventana < SOC_objetivo:
           deficit = SOC_objetivo - (SOC_inicio + capacidad_carga_en_ventana)
           SOC_objetivo_del_siguiente_viaje += deficit
    4. Almacenar kwh_necesarios = (SOC_objetivo - SOC_inicio) * capacidad_bateria / 100
```

## Interface Contracts

**Function signature**:
```python
async def calcular_hitos_soc(
    trips: List[Dict[str, Any]],
    soc_inicial: float,
    charging_power_kw: float,
    battery_capacity_kwh: float
) -> List[Dict[str, Any]]:
    """
    Returns list of trips with updated kwh requirements:
    [{
        "trip_id": str,
        "soc_objetivo": float,
        "kwh_necesarios": float,
        "deficit_acumulado": float,
        "ventana_carga": {"inicio": datetime, "fin": datetime}
    }, ...]
    """
```

**Data source**: `battery_capacity_kwh` from `vehicle_config` (config entry data), fallback 50.0 kWh

**Dependencies**: Spec 2: Charging Window Calculation

## Size
Medium - algorithm implementation with testing

## TODO

- [ ] Implement `calcular_hitos_soc()` function
- [ ] Pass `battery_capacity_kwh` from config
- [ ] Implement deficit propagation algorithm
- [ ] Handle charging rate: `charging_power_kw / battery_capacity_kwh * 100` = % SOC/hour
- [ ] Add unit tests

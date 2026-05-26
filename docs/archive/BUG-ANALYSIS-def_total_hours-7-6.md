# Análisis del Bug: def_total_hours [7, 6] en Staging

## Resumen Ejecutivo

**Bug:** `def_total_hours` muestra `[7, 6]` en staging en lugar de `[2, 2]` esperados.

**Causa Raíz:** `EMHASSAdapter` no lee `battery_capacity_kwh` de `ConfigEntry`, usa default 50.0 kWh en lugar de 28.0 kWh del vehículo configurado.

## Datos del Bug

### Valores Observados en Staging
```
BUG-DEBUG: _precompute_and_process_trips battery_capacity_kwh=50.00 soc_current=50.00 charging_power_kw=None
BUG-DEBUG: _populate_per_trip_cache_entry DONE trip_id=rec_5_xeqnmt def_total_hours=7.00
BUG-DEBUG: _populate_per_trip_cache_entry DONE trip_id=rec_1_fy4pfk def_total_hours=6.00
```

### Valores Correctos (esperados)
```
def_total_hours: [2, 2]
- Trip 1: 5.4 kWh / 3.4 kW = 1.59h → ceil = 2h
- Trip 2: 5.4 kWh / 3.4 kW = 1.59h → ceil = 2h
```

## Causa Raíz

### Problema 1: battery_capacity_kwh no se lee de ConfigEntry

```python
# EMHASSAdapter.__init__ (líneas 74-78)
self._load_publisher = LoadPublisher(
    hass=hass,
    vehicle_id=self.vehicle_id,
    config=LoadPublisherConfig(index_manager=self._index_manager),  # battery_capacity_kwh=50.0 DEFAULT!
)
```

**Debería ser:**
```python
self._load_publisher = LoadPublisher(
    hass=hass,
    vehicle_id=self.vehicle_id,
    config=LoadPublisherConfig(
        index_manager=self._index_manager,
        battery_capacity_kwh=self._entry.data.get("battery_capacity_kwh", 50.0),
        charging_power_kw=self._entry.data.get("charging_power_kw", 3.6),
    ),
)
```

### Problema 2: soc_current no se lee del sensor configurado

```python
# EMHASSAdapter._get_current_soc() retorna None si no hay presencia
```

**Log de staging:**
```
soc_current=50.00  # Default en lugar de 65.0 del sensor
```

## Tests que Fallan (Reproducen el Bug)

### Test 1: `test_adapter_must_read_battery_capacity_from_config_entry`
```
AssertionError: EMHASSAdapter MUST read battery_capacity_kwh=28.0 from ConfigEntry, 
but got 50.0. BUG: adapter uses LoadPublisherConfig default 50.0 
instead of entry.data['battery_capacity_kwh']=28.0
```

### Test 2: `test_adapter_must_read_soc_from_hass_sensor`
```
AssertionError: EMHASSAdapter MUST read SOC=65.0 from sensor.ev_battery_soc, 
but got None. BUG: adapter uses default SOC instead of configured sensor
```

### Test 3: `test_full_flow_uses_config_values_not_defaults`
```
AssertionError: With correct config (battery=28.0, SOC=65%), 
def_total_hours should be [2, 2], got [2, 1]. 
BUG: adapter is using default values instead of config entry values.
```

## Cómo el Bug Produce [7, 6]

### Con valores INCORRECTOS (staging):
```
battery_capacity_kwh = 50.0  # WRONG (default)
soc_current = 50.0          # WRONG (default)
charging_power_kw = None    # WRONG (not read)

SOC capping calculation:
- current_energy = 50% × 50.0 kWh = 25.0 kWh
- soc_cap = 93.68% × 50.0 kWh = 46.84 kWh
- capped_energy = 46.84 - 25.0 = 21.84 kWh
- capped_hours = 21.84 / 3.4 = 6.42h → ceil = 7h  ← BUG!
```

### Con valores CORRECTOS (config):
```
battery_capacity_kwh = 28.0  # CORRECT
soc_current = 65.0          # CORRECT
charging_power_kw = 3.4     # CORRECT

SOC capping calculation:
- current_energy = 65% × 28.0 kWh = 18.2 kWh
- soc_cap = 85.99% × 28.0 kWh = 24.08 kWh
- capped_energy = 24.08 - 18.2 = 5.88 kWh
- capped_hours = 5.88 / 3.4 = 1.73h → ceil = 2h  ← CORRECT!
```

## Fix Necesario

### En `EMHASSAdapter.__init__()`:

```python
def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
    # ... existing code ...
    
    # Read battery_capacity_kwh from ConfigEntry
    battery_capacity_kwh = 50.0  # default
    charging_power_kw = 3.6     # default
    if entry:
        entry_data = dict(getattr(entry, "options", {}) or {})
        entry_data.update(dict(getattr(entry, "data", {}) or {})
        battery_capacity_kwh = float(entry_data.get("battery_capacity_kwh", 50.0))
        charging_power_kw = float(entry_data.get("charging_power_kw", 3.6))
    
    self._load_publisher = LoadPublisher(
        hass=hass,
        vehicle_id=self.vehicle_id,
        config=LoadPublisherConfig(
            index_manager=self._index_manager,
            battery_capacity_kwh=battery_capacity_kwh,
            charging_power_kw=charging_power_kw,
        ),
    )
```

## Archivos Modificados

- `tests/integration/test_multi_trip_staging_scenario.py`: Tests que fallan reproduciendo el bug

## Estado

- [x] Bug identificado
- [x] Causa raíz encontrada (EMHASSAdapter no lee ConfigEntry)
- [x] Tests que fallan creados
- [ ] Fix implementado (pendiente)
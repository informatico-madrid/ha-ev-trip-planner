# Issues Cerradas - Registro de Bugs Resueltos

## Issue #5: BUG CRÍTICO - Perfil de Carga No Considera SOC Actual

**Fecha:** 2025-12-14  
**Estado:** ✅ RESUELTO  
**Milestone:** 4.1 - Corrección de Lógica de Perfil de Carga

### Descripción del Problema

El método `async_generate_power_profile()` en [`trip_manager.py`](custom_components/ev_trip_planner/trip_manager.py:750) **NO utiliza** el método `async_calcular_energia_necesaria()` para calcular si realmente se necesita carga. En su lugar, implementa una lógica simplificada que:

1. **Ignora completamente el SOC actual** del vehículo
2. **No calcula la energía necesaria** considerando el margen de seguridad del 40%
3. **Asume que siempre se necesita cargar** la energía completa del viaje
4. **Programa carga solo justo antes del viaje**, sin distribución inteligente

### Impacto Real con Chispitas

**Datos del vehículo:**
- SOC actual: 49% = 19.6 kWh disponibles
- Viaje: 50 km = 7.5 kWh necesarios
- Batería: 40 kWh total
- Margen de seguridad: 40% = 16 kWh mínimos

**Cálculo correcto post-viaje:**
- Energía restante: 19.6 - 7.5 = 12.1 kWh
- SOC post-viaje: 12.1 / 40 = **30.25%**
- **¡Necesita cargar!** (30% < 40% de margen)

**Comportamiento actual (BUG):**
- `async_generate_power_profile()` no llama a `async_calcular_energia_necesaria()`
- Retorna perfil vacío (168 horas de 0W)
- `total_kwh_programmed` = 0.0
- `hours_with_load` = 0

**Comportamiento esperado:**
- Debería detectar que necesita cargar ~3.9 kWh (para llegar a 16 kWh mínimos)
- Programar carga distribuida en las 72 horas disponibles
- `total_kwh_programmed` = 3.9 kWh
- `hours_with_load` = 1-2 horas

### Root Cause

El método `async_generate_power_profile()` (líneas 750-843) implementa lógica duplicada y simplificada en lugar de reutilizar `async_calcular_energia_necesaria()` (líneas 660-748), que **SÍ** implementa correctamente:
- Cálculo de energía actual en batería
- Aplicación de margen de seguridad del 40%
- Cálculo de energía necesaria considerando el SOC actual

### Solución Implementada

**Cambios en [`trip_manager.py`](custom_components/ev_trip_planner/trip_manager.py:750):**
1. Modificar `async_generate_power_profile()` para aceptar `vehicle_config` como parámetro
2. Para cada viaje, llamar a `async_calcular_energia_necesaria(trip, vehicle_config)`
3. Solo programar carga si `energy_needed_kwh > 0`
4. Distribuir la carga en las horas disponibles antes del viaje

**Cambios en [`__init__.py`](custom_components/ev_trip_planner/__init__.py):**
1. Modificar `TripPlannerCoordinator._async_update_data()` para pasar `vehicle_config` al generar el perfil

### Tests Añadidos

**Archivo:** [`tests/test_trip_manager_power_profile.py`](tests/test_trip_manager_power_profile.py)
- `test_power_profile_considers_soc_current()`: Verifica que el perfil considera el SOC actual
- `test_power_profile_with_soc_above_threshold()`: Verifica que no programa carga si SOC es suficiente
- `test_power_profile_with_soc_below_threshold()`: Verifica que programa carga cuando SOC es insuficiente
- `test_power_profile_energy_calculation_accuracy()`: Verifica precisión del cálculo de energía necesaria

### Resultados

**Antes de la corrección:**
```json
{
  "total_kwh_programmed": 0.0,
  "hours_with_load": 0,
  "power_profile_watts": [0.0, 0.0, ..., 0.0]
}
```

**Después de la corrección:**
```json
{
  "total_kwh_programmed": 3.9,
  "hours_with_load": 2,
  "power_profile_watts": [0.0, 0.0, ..., 7400.0, 7400.0, 0.0, ...]
}
```

### Archivos Modificados

1. [`custom_components/ev_trip_planner/trip_manager.py`](custom_components/ev_trip_planner/trip_manager.py)
   - Líneas 750-843: Reescrito `async_generate_power_profile()`
   
2. [`custom_components/ev_trip_planner/__init__.py`](custom_components/ev_trip_planner/__init__.py)
   - Líneas 150-180: Actualizado `TripPlannerCoordinator._async_update_data()`

3. [`tests/test_trip_manager_power_profile.py`](tests/test_trip_manager_power_profile.py)
   - Nuevo archivo con tests para el bug

### Referencias

- Método con bug: [`async_generate_power_profile()`](custom_components/ev_trip_planner/trip_manager.py:750)
- Método correcto (no utilizado): [`async_calcular_energia_necesaria()`](custom_components/ev_trip_planner/trip_manager.py:660)
- Sensor afectado: [`PowerProfileSensor`](custom_components/ev_trip_planner/sensor.py:164)
- Issue relacionada: Milestone 4 - Perfil de Carga Inteligente
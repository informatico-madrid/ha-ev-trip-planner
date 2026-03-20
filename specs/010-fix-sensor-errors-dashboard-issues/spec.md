# Fix Sensor Errors, Dashboard Issues, and Test Quality

**Feature ID**: 010-fix-sensor-errors-dashboard-issues  
**Status**: Draft  
**Created**: 2026-03-20  
**Component**: EV Trip Planner Integration  
**Priority**: Critical

---

## Problem Summary

Al ejecutar EV Trip Planner en Home Assistant Container, se producen los siguientes errores críticos en los logs:

1. **P001 - VehicleController.get_charging_power() no existe**: Error cada 30 segundos
2. **P002 - Sensores con device_class incorrecto**: Warning sobre incompatibilidad
3. **P003 - NextTripSensor falla al crearse**: Error de valor no numérico
4. **P004 - Dashboard no se importa**: Storage API no disponible en Container

---

## User Stories

### P001: VehicleController.get_charging_power() error
**Como** usuario que configura un nuevo vehículo  
**Quiero** que los sensores funcionen sin errores en el log  
**Para** ver el estado del vehículo y viajes programados

### P002: Sensores con device_class incorrecto
**Como** usuario que usa los sensores  
**Quiero** que los sensores tengan la configuración correcta  
**Para** evitar warnings en los logs de Home Assistant

### P003: NextTripSensor falla
**Como** usuario sin viajes programados  
**Quiero** que el sensor next_trip se cree sin errores  
**Para** poder usar el dashboard incluso sin viajes

### P004: Dashboard Container
**Como** usuario de HA Container  
**Quiero** que el dashboard se importe o genere instrucciones claras  
**Para** poder usar el dashboard en mi instalación

---

## Functional Requirements

### FR-001: Fix VehicleController.get_charging_power() error
**Descripción**: El sensor hours_needed_today debe poder obtener la potencia de carga
**Criterios de aceptación**:
- No aparece error "VehicleController has no attribute 'get_charging_power'" en logs
- El sensor hours_needed_today se actualiza correctamente cada 30 segundos (intervalo estándar de HA)
- Valor retornado en kW (kilowatts)

### FR-002: Fix sensor device_class configuration
**Descripción**: Cada sensor debe tener el device_class apropiado
**Criterios de aceptación**:
- Sensores de energía (kWh) tienen device_class ENERGY
- Sensores de tiempo tienen device_class DURATION o None
- Sensores de texto tienen device_class None
- No aparecen warnings de incompatibilidad en logs

### FR-003: Fix NextTripSensor creation error
**Descripción**: El sensor next_trip debe crearse sin errores cuando no hay viajes
**Criterios de aceptación**:
- El sensor se crea sin errores aunque no haya viajes programados
- No aparece "ValueError: non-numeric value" en logs

### FR-004: Fix dashboard import in HA Container
**Descripción**: El dashboard debe importarse o generar instrucciones claras en Container
**Criterios de aceptación**:
- Si no se puede importar, se genera archivo YAML en config directory
- El usuario recibe notificación con: (1) ruta del archivo generado, (2) pasos para importar manualmente en Lovelace UI
- No aparecen errores confusos en logs - solo información útil
- **Robustez**: Maneja nombre de dashboard ya existente (agrega sufijo -2-, -3-, etc.)
- **Tests**: Cobertura completa para todos los casos de fallo

---

## Success Criteria

1. **Sensores funcionales**: Los sensores se crean sin errores para nuevos vehículos
2. **Dashboard único**: El dashboard se crea con nombre único sin colisiones
3. **Tests de calidad**: Tests que cubran todos los casos de uso críticos

---

## Assumptions

1. Home Assistant Container no tiene Supervisor ni Storage API
2. Los sensores heredan device_class de la clase base incorrectamente
3. VehicleController no necesita método get_charging_power - debe estar en TripManager
4. Los tests actuales no cubren los paths de error y fallback

---

## Key Entities

| Entidad | Descripción |
|---------|-------------|
| TripManager | Gestor central de viajes |
| TripPlannerSensor | Sensores del componente |
| LovelaceDashboard | Dashboard de Lovelace |
| ConfigEntry | Entrada de configuración HA |

---

## Technical Notes

### Root Cause Analysis

**P001: VehicleController.get_charging_power() no existe**
- Location: `sensor.py:90`
- Código: `self.trip_manager.vehicle_controller.get_charging_power()`
- El método NO existe en VehicleController
- Existe `_get_charging_power()` en TripManager (privado)

**P002: Sensores con device_class incorrecto**
- Location: `sensor.py:58-60` (clase base)
- TripPlannerSensor define device_class=energy para TODOS los sensores derivados
- Sensores como NextTripSensor devuelven strings, no son energía

**P003: NextTripSensor falla**
- Location: `sensor.py:103`
- Devuelve "N/A" cuando no hay viaje
- device_class=energy no permite valores no numéricos

**P004: Dashboard no se importa**
- Location: `__init__.py:632`
- HA Container no tiene `lovelace.save` service
- HA Container no tiene Storage API
- Código intenta ambos métodos pero ambos fallan

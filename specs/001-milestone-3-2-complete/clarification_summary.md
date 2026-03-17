# Resumen de Clarificaciones - Milestone 3.2

**Fecha**: 2026-03-17  
**Estado**: Clarificaciones completadas

---

## Hallazgos Críticos

### 🔴 Hallazgo 1: Milestone 3.1 NO está terminado

**Problema**: Las mejoras UX de Milestone 3.1 (textos, descripciones, labels) **NO están implementadas**.

**Impacto**: **ALTO** - Sin esto, la configuración será confusa para usuarios.

**Acción Requerida**: Implementar Milestone 3.1 **ANTES** de Milestone 3.2.

---

### 🔴 Hallazgo 2: Documentación incorrecta sobre EMHASS

**Problema**: La documentación asume que EMHASS publica sensores que **NO EXISTEN**:
- `sensor.emhass_planning_horizon` - **NO EXISTE**
- `sensor.emhass_deferrable_load_config_{index}` - **NO EXISTE** (solo se crea dinámicamente)

**Impacto**: **CRÍTICO** - El código basado en esto fallará.

**Acción Requerida**: Corregir documentación y arquitectura.

---

### 🔴 Hallazgo 3: Snippet YAML manual es problemático

**Problema**: La documentación sugiere mostrar snippet YAML para copiar manualmente a EMHASS.

**Problemas**:
1. No es automático
2. Propenso a errores
3. Requiere reinicio de EMHASS
4. No escala (50 cargas = YAML enorme)

**Acción Requerida**: Usar API/Service de EMHASS o input_text helpers en HA.

---

## Respuestas de Clarificación

### P1: Nombres de Entidades
**Respuesta**: Opción A - `{nombre_vehiculo}_{tipo_sensor}`
- Ejemplo: `sensor.mi_coche_presencia_status`
- Legible y descubrible en UI

### P2: Detección de Presencia
**Respuesta**: Opción A - Configurar durante setup inicial
- El config_flow actual **NO tiene** pasos para presencia
- Debe agregarse paso 5: "Presence Detection"

### P3: Servicio de Notificaciones
**Respuesta**: Opción A - Configurable por vehículo
- Permite diferentes estrategias por vehículo

### P4: Snippet EMHASS
**Respuesta**: Opción A o C - Evitar YAML manual
- Usar API/Service de EMHASS o input_text helpers
- **NO** mostrar YAML manual para copiar

### P5: Estrategia de Control
**Respuesta**: Opción A - Inmutable durante setup
- Seleccionada una vez, no cambia después

### P6: MAX_DEFERRABLE_LOADS
**Respuesta**: Opción A - Validar contra EMHASS real
- Leer configuración de EMHASS y validar
- Si EMHASS tiene max=50, aceptar max=50

### P7: Planning Horizon
**Respuesta**: Opción B - Solo input manual
- **NO hay sensor** `emhass_planning_horizon`
- La documentación asume sensor que no existe
- Usar solo input manual del usuario

### P8: Milestone 3.1
**Respuesta**: **NO está terminado**
- Mejoras UX no implementadas
- Debe implementarse antes de Milestone 3.2

---

## Corregir la Documentación

### Eliminar Referencias Incorrectas

1. **Eliminar**: `CONF_PLANNING_SENSOR` - No hay sensor que leer
2. **Eliminar**: Referencias a `sensor.emhass_planning_horizon` - No existe
3. **Corregir**: Snippet YAML manual → API/Service o input_text

### Actualizar Arquitectura

**Flujo Correcto**:
1. Usuario configura vehículo → config_flow
2. Sistema calcula viajes → trip_manager
3. Sistema publica cargas diferibles → emhass_adapter (vía API/Service)
4. EMHASS optimiza → schedule generado
5. Sistema monitorea schedule → schedule_monitor
6. Sistema activa carga → vehicle_controller (switch/service)

---

## Plan de Implementación Actualizado

### Fase 0: Milestone 3.1 (PRIORIDAD)
**Duración**: 1-2 días

- [ ] 3.1.1 Añadir descriptions en config_flow.py
- [ ] 3.1.2 Corregir "External EMHASS" → "Notifications Only"
- [ ] 3.1.3 Clarificar checkbox de planning horizon
- [ ] 3.1.4 Corregir planning sensor entity

### Fase 1: Config Flow (Milestone 3.2)
**Duración**: 1-2 días

- [ ] 3.2.1 Agregar paso 4: "EMHASS Configuration"
- [ ] 3.2.2 Agregar paso 5: "Presence Detection"
- [ ] 3.2.3 Validar max_deferrable_loads contra EMHASS
- [ ] 3.2.4 Usar solo input manual para planning horizon

### Fase 2: EMHASS Adapter (Milestone 3.2)
**Duración**: 2-3 días

- [ ] 3.2.5 Implementar publicación vía API/Service (NO YAML manual)
- [ ] 3.2.6 Crear entidades de sensor dinámicamente
- [ ] 3.2.7 Validar contra capacidad real de EMHASS

### Fase 3: Sensor.py (Milestone 3.2)
**Duración**: 2-3 días

- [ ] 3.2.8 Crear `sensor.{vehicle}_presence_status`
- [ ] 3.2.9 Crear `sensor.{vehicle}_charging_readiness`
- [ ] 3.2.10 Crear `sensor.{vehicle}_active_trips_count`

### Fase 4: Trip Manager (Milestone 3.2)
**Duración**: 2-3 días

- [ ] 3.2.11 Implementar `async_expand_trips()`
- [ ] 3.2.12 Usar planning horizon manual (no sensor)
- [ ] 3.2.13 Expandir viajes recurrentes para próximos días

### Fase 5: Tests (Milestone 3.2)
**Duración**: 3-4 días

- [ ] 3.2.14 Tests para config_flow
- [ ] 3.2.15 Tests para emhass_adapter
- [ ] 3.2.16 Tests para vehicle_controller
- [ ] 3.2.17 Tests para presence_monitor

---

## Total Estimado

| Fase | Duración |
|------|----------|
| 0: Milestone 3.1 | 1-2 días |
| 1: Config Flow | 1-2 días |
| 2: EMHASS Adapter | 2-3 días |
| 3: Sensor.py | 2-3 días |
| 4: Trip Manager | 2-3 días |
| 5: Tests | 3-4 días |
| **TOTAL** | **11-17 días** |

---

## Recomendaciones

1. **Implementar Milestone 3.1 primero** - Mejoras UX son críticas
2. **Corregir documentación** - Eliminar referencias a sensores que no existen
3. **Usar API/Service** - NO YAML manual para EMHASS
4. **Validar contra EMHASS real** - No asumir capacidades
5. **Tests desde el inicio** - No dejar para el final

---

**Documento generado por análisis de código y documentación**  
**Fecha**: 2026-03-17

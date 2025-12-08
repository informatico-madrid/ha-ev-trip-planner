# 🏗️ Milestone 3: Arquitectura de Integración con Optimizadores - Análisis Detallado

**Documento de Análisis Arquitectónico**  
**Versión**: 1.0  
**Fecha**: 2025-12-08  
**Estado**: En Análisis  
**Arquitecto**: HACS Plugin Development Specialist

---

## 📋 Resumen Ejecutivo

Este documento redefine completamente el enfoque del Milestone 3 basándose en un análisis crítico de las limitaciones del diseño original y los requisitos reales de producción. El objetivo ya no es "modificar un sensor híbrido", sino **crear una capa de abstracción agnóstica** que convierta viajes en cargas diferibles para cualquier optimizador (EMHASS u otros) y gestione la activación física de la carga de forma genérica para cualquier integración de vehículo.

---

## 🔍 Análisis Crítico del Enfoque Original (ROADMAP.md)

### ❌ Limitaciones Identificadas

1. **Acoplamiento Incorrecto**: El ROADMAP.md asume que modificaremos `sensor.ovms_horas_para_mpc_dinamico` directamente. Esto es **anti-patrones** porque:
   - Acopla el módulo a una implementación específica (templates YAML)
   - No es portable entre instalaciones de HA
   - Rompe el principio de responsabilidad única

2. **Falta de Agnosticismo**: El diseño original asume control MPC directo, pero:
   - EMHASS ya no usa MPC en nuestra instalación actual (solo day-ahead)
   - Cada usuario tiene configuraciones de EMHASS diferentes
   - No todos usan EMHASS (pueden usar otros optimizadores)

3. **Hardcoding de Vehículos**: Menciona "OVMS" y "Morgan" específicamente:
   - No escala a múltiples vehículos
   - No soporta diferentes integraciones (Renault, Tesla, etc.)
   - Cada nuevo vehículo requiere cambios en código

4. **Falta de Capa de Control**: No define cómo se activa/desactiva físicamente la carga:
   - ¿Qué sensor/switch/service se usa por vehículo?
   - ¿Cómo maneja múltiples vehículos compartiendo cargador?
   - ¿Qué pasa si el control falla?

---

## 🎯 Nuevo Enfoque Arquitectónico: "Optimizador-Agnóstico y Vehículo-Agnóstico"

### Principios de Diseño

1. **Agnóstico del Optimizador**: El módulo no sabe/care si usas EMHASS, otro optimizador, o solo notificaciones
2. **Agnóstico del Vehículo**: Funciona con OVMS, Renault, Tesla, o cualquier integración que exponga sensores
3. **Cargas Diferibles como Interfaz**: Cada viaje se publica como una carga diferible estándar que cualquier optimizador puede consumir
4. **Control Pluggable**: Cada vehículo configura su propio mecanismo de activación (switch, service, script)
5. **Sin Modificar Implementaciones Externas**: No tocamos templates YAML del usuario

---

## 🏗️ Arquitectura Propuesta

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│              EV TRIP PLANNER MODULE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────────┐               │
│  │ Trip Manager │─────▶│  EMHASS Adapter  │               │
│  │  (Storage)   │      │ (Diferible Load) │               │
│  └──────────────┘      └──────────────────┘               │
│         │                       │                          │
│         │ publish               │ publish                  │
│         │ trips                 │ deferrable_loads         │
│         ▼                       ▼                          │
│  ┌─────────────────┐   ┌──────────────────┐              │
│  │  Calculation    │   │   EMHASS API     │              │
│  │    Sensors      │   │  (day-ahead/mpc) │              │
│  └─────────────────┘   └──────────────────┘              │
│         │                       │                          │
│         │                       │ generates                │
│         │                       │ schedule                 │
│         ▼                       ▼                          │
│  ┌──────────────────────────────────────────┐            │
│  │   Vehicle Control Interface (per-vehicle)│            │
│  │   - Switch entity                        │            │
│  │   - Service call                         │            │
│  │   - External script                      │            │
│  └──────────────────────────────────────────┘            │
│         │                                                 │
│         │ activates/deactivates                           │
│         ▼                                                 │
│  ┌──────────────────────────────────────────┐            │
│  │   Physical Charging (OVMS, Renault, etc)│            │
│  └──────────────────────────────────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Datos

1. **Creación de Viaje**: Usuario crea viaje → Trip Manager lo almacena
2. **Expansión**: Cada hora, el módulo expande viajes recurrentes para próximos 7 días
3. **Publicación**: Para cada viaje, crea una **carga diferible** con:
   - `entity_id`: `deferrable_load.ovms_viaje_lunes_trabajo`
   - `power`: kW necesarios (calculado de kWh y horizonte)
   - `duration`: horas de carga requeridas
   - `deadline`: datetime del viaje
   - `priority`: configurable (trabajo > ocio)
4. **Optimización**: EMHASS (u otro optimizador) consume estas cargas diferibles
5. **Schedule**: Optimizador genera `sensor.emhass_deferrable0_schedule`
6. **Control**: Nuestro módulo monitorea el schedule y activa/desactiva el cargador del vehículo

---

## 🔧 Configuración por Vehículo (Nueva Sección en Config Flow)

### Paso 4: Configuración de Integración y Control

```python
# Nuevas constantes en const.py
CONF_VEHICLE_INTEGRATION = "vehicle_integration"
CONF_CHARGE_CONTROL_ENTITY = "charge_control_entity"
CONF_CHARGE_CONTROL_SERVICE = "charge_control_service"
CONF_CHARGE_CONTROL_SCRIPT = "charge_control_script"

# Opciones de integración
INTEGRATION_OVMS = "ovms"
INTEGRATION_RENAULT = "renault"
INTEGRATION_TESLA = "tesla"
INTEGRATION_GENERIC = "generic"
```

### Formulario de Configuración

**Pregunta 1**: ¿Qué integración usas para tu vehículo?
- Dropdown con opciones: OVMS, Renault, Tesla, Generic, Otro

**Pregunta 2**: ¿Cómo se activa/desactiva la carga?
- **Opción A**: Switch entity (mostrar selector de entidades switch.*)
- **Opción B**: Service call (mostrar campos: service name, data template)
- **Opción C**: Script (mostrar selector de script.*)
- **Opción D**: External (el usuario maneja manualmente, solo notificaciones)

**Pregunta 3** (si Opción A): ¿Qué switch controla la carga?
- Entity selector filtrado por `switch.*`

**Pregunta 4** (si Opción B): ¿Qué service y con qué datos?
- Text input: `service name` (ej: `ovms/set_charge_mode`)
- Text area: `service data template` (ej: `{"vehicle_id": "chispitas", "mode": "on"}`)

**Pregunta 5** (opcional): ¿Hay sensores de estado?
- SOC sensor (ya existe)
- Charging status sensor (ya existe)
- **Nuevo**: ¿Sensor que indica si el coche está físicamente enchufado?

---

## 📊 Sub-Milestones Re-definidos (Más Granulares)

### ⚪ Milestone 3A: Adaptador de Cargas Diferibles (3 días)

**Objetivo**: Convertir viajes en entidades de carga diferible estándar

**Tareas**:
- [ ] Crear `EMHASSAdapter` class en `emhass_adapter.py`
- [ ] Método: `async_create_deferrable_load(trip)` → crea entidad `deferrable_load.{vehicle}_{trip_id}`
- [ ] Método: `async_update_deferrable_load(trip)` → actualiza power, duration, deadline
- [ ] Método: `async_delete_deferrable_load(trip_id)` → elimina entidad
- [ ] Publicar atributos: `power`, `duration`, `deadline`, `priority`, `status`
- [ ] Tests: Crear viaje → verificar entidad creada → verificar atributos correctos

**Criterios de Éxito**:
- ✅ Cada viaje aparece como entidad en Developer Tools
- ✅ Atributos son consumibles por EMHASS day-ahead
- ✅ No requiere modificar templates YAML del usuario

**Archivos**:
- `custom_components/ev_trip_planner/emhass_adapter.py` (nuevo)
- `custom_components/ev_trip_planner/sensor.py` (modificar para publicar cargas)

---

### ⚪ Milestone 3B: Interface de Control de Carga (3 días)

**Objetivo**: Permitir configurar cómo se activa/desactiva la carga por vehículo

**Tareas**:
- [ ] Extender `config_flow.py` con paso 4 (control configuration)
- [ ] Añadir nuevas constantes para tipos de control
- [ ] Crear `VehicleController` class en `vehicle_controller.py`
- [ ] Métodos: `async_activate()`, `async_deactivate()`, `async_get_status()`
- [ ] Implementar estrategias: SwitchStrategy, ServiceStrategy, ScriptStrategy
- [ ] Validación: Probar activación/desactivación al guardar configuración
- [ ] Tests: Unit tests para cada estrategia de control

**Criterios de Éxito**:
- ✅ Config flow permite seleccionar tipo de control
- ✅ Cada estrategia funciona con su mecanismo correspondiente
- ✅ Feedback inmediato si el control no funciona (ej: switch no existe)

**Archivos**:
- `custom_components/ev_trip_planner/config_flow.py` (extender)
- `custom_components/ev_trip_planner/vehicle_controller.py` (nuevo)
- `custom_components/ev_trip_planner/const.py` (añadir constantes)

---

### ⚪ Milestone 3C: Monitor y Executor de Schedules (4 días)

**Objetivo**: Monitorear schedules generados por EMHASS y ejecutar acciones de control

**Tareas**:
- [ ] Crear `ScheduleMonitor` class en `schedule_monitor.py`
- [ ] Descubrir dinámicamente: ¿Qué cargas diferibles creó EMHASS?
- [ ] Suscribirse a cambios en `sensor.emhass_deferrableX_schedule`
- [ ] Mapear: `deferrable_load.ovms_viaje_lunes` ↔ `sensor.emhass_deferrable0_schedule`
- [ ] Lógica: Cuando schedule indica "cargar ahora" → activar control del vehículo
- [ ] Lógica: Cuando schedule indica "no cargar" → desactivar control
- [ ] Manejar transiciones suaves (evitar flickering)
- [ ] Tests: Simular schedule changes → verificar control activado/desactivado

**Criterios de Éxito**:
- ✅ Cuando EMHASS programa carga, el vehículo empieza a cargar
- ✅ Cuando EMHASS para carga, el vehículo deja de cargar
- ✅ Funciona con múltiples vehículos simultáneamente
- ✅ No requiere configuración manual de mapeo

**Archivos**:
- `custom_components/ev_trip_planner/schedule_monitor.py` (nuevo)
- `custom_components/ev_trip_planner/coordinator.py` (modificar para integrar)

---

### ⚪ Milestone 3D: Testing de Integración Completa (3 días)

**Objetivo**: Validar flujo completo en entorno de producción

**Tareas**:
- [ ] Crear `test_integration.py` con escenarios end-to-end
- [ ] Scenario 1: Viaje recurrente → carga diferible → schedule → activación
- [ ] Scenario 2: Múltiples viajes en un día → priorización correcta
- [ ] Scenario 3: Fallback cuando EMHASS no genera schedule
- [ ] Scenario 4: Control manual sobrescribe schedule
- [ ] Deploy en entorno de prueba (no producción)
- [ ] Monitorear logs durante 24h con viajes reales
- [ ] Medir latencia: schedule generado → acción ejecutada

**Criterios de Éxito**:
- ✅ Todos los escenarios pasan sin intervención manual
- ✅ Latencia < 60 segundos entre schedule y acción
- ✅ No hay errores en logs durante 24h
- ✅ Puede deshabilitarse sin afectar otros sistemas

**Archivos**:
- `tests/test_integration.py` (nuevo)
- `tests/conftest.py` (añadir fixtures de EMHASS mock)

---

### ⚪ Milestone 3E: Herramienta de Migración (2 días)

**Objetivo**: Ayudar a usuarios a migrar de sliders a sistema de viajes

**Tareas**:
- [ ] Crear servicio: `ev_trip_planner.import_from_sliders`
- [ ] Leer `input_number.{vehicle}_carga_necesaria_{dia}`
- [ ] Convertir a viajes recurrentes automáticamente
- [ ] Preview mode: Mostrar qué viajes se crearán antes de ejecutar
- [ ] Botón en dashboard: "Importar desde sliders"
- [ ] Opción: "Modo simulación" (no crear, solo mostrar)
- [ ] Tests: Verificar conversión correcta de datos

**Criterios de Éxito**:
- ✅ Botón funciona y muestra preview
- ✅ Viajes creados tienen kWh correctos
- ✅ Descripciones son legibles (ej: "Importado: Lunes trabajo")
- ✅ Puede ejecutarse múltiples veces sin duplicar

**Archivos**:
- `custom_components/ev_trip_planner/services.yaml` (añadir servicio)
- `custom_components/ev_trip_planner/trip_manager.py` (añadir método import)

---

## ⚠️ Puntos Débiles del Análisis y Mitigaciones

### Punto Débil #1: Descubrimiento Dinámico de Cargas Diferibles

**Problema**: ¿Cómo sabe nuestro módulo qué `sensor.emhass_deferrableX_schedule` corresponde a qué viaje?

**Mitigación Propuesta**:
- Usar `unique_id` consistente: `deferrable_load.{vehicle}_{trip_id}`
- EMHASS permite configurar `entity_names` para cargas diferibles
- En `configuration.yaml` de EMHASS, el usuario debe mapear:
  ```yaml
  emhass:
    deferrable_loads:
      - name: "ovms_lunes_trabajo"
        entity_id: "deferrable_load.ovms_viaje_lunes_trabajo"
  ```
- Nuestro módulo genera un `emhass_config_snippet` para copiar-pegar

### Punto Débil #2: Múltiples Vehículos, Un Cargador

**Problema**: ¿Qué pasa si dos vehículos necesitan cargar pero solo hay un cargador?

**Mitigación Propuesta**:
- Añadir `priority` a cada viaje (configurable: alta/media/baja)
- EMHASS ya maneja prioridades entre cargas diferibles
- En fase 3C, el `ScheduleMonitor` debe verificar si el cargador está ocupado
- Si vehículo B tiene prioridad más alta pero cargador ocupado → notificar usuario

### Punto Débil #3: Estado de Conexión Física

**Problema**: ¿Cómo sabemos si el coche está físicamente enchufado?

**Mitigación Propuesta**:
- En config flow, preguntar por `charging_status_sensor` (binary_sensor)
- Si no existe, asumir siempre "enchufado" (riesgo: planificar carga para coche que no está)
- Opción avanzada: Usar sensor de corriente del cargador > 0A como proxy
- Notificación si schedule activa pero coche no está enchufado durante 15 min

### Punto Débil #4: Latencia y Race Conditions

**Problema**: ¿Qué pasa si EMHASS genera schedule pero nuestro monitor no lo procesa a tiempo?

**Mitigación Propuesta**:
- Usar `async_track_state_change_event` en lugar de polling
- Implementar queue de acciones pendientes
- Si acción no se ejecuta en 5 min, marcar como "stale" y reintentar
- Métrica: `sensor.ev_trip_planner_last_schedule_execution_time`

---

## 🎨 Mejoras al Flujo de Configuración (UX)

### Paso 4: Configuración de Integración (Nuevo)

**Pregunta 4.1**: ¿Qué integración usas para tu vehículo?
- Dropdown dinámico con integraciones detectadas (OVMS, Renault, Tesla, etc.)
- Opción "Otro" → campos libres para sensores

**Pregunta 4.2**: ¿Cómo se activa/desactiva la carga?
- Cards explicativas con iconos para cada opción
- Preview en tiempo real: "Esto activará: switch.carga_ovms"

**Pregunta 4.3**: ¿Qué sensores indican estado?
- Selector múltiple con validación
- Si falta sensor crítico → warning pero permitir continuar

### Paso 5: Configuración Avanzada (Opcional)

**Pregunta 5.1**: ¿Usas EMHASS u otro optimizador?
- Si "Sí" → mostrar snippet de configuración para copiar
- Si "No" → modo "solo notificaciones"

**Pregunta 5.2**: ¿Cuántos deferrable loads tienes configurados?
- Input number (0-10)
- Ayuda: "Necesario para mapear automáticamente"

---

## 📊 Nuevos Sensores y Entidades

### Entidades Creadas por el Módulo

**Por cada viaje activo**:
- `deferrable_load.{vehicle}_{trip_id}` (entity)
  - `state`: `pending`, `scheduled`, `charging`, `completed`
  - `attributes`:
    - `power`: kW requeridos
    - `duration`: horas necesarias
    - `deadline`: datetime ISO
    - `priority`: 1-5
    - `vehicle_id`: string
    - `trip_type`: recurrente | puntual

**Por cada vehículo configurado**:
- `binary_sensor.{vehicle}_charging_control_active`
  - `on`: El módulo está controlando activamente la carga
  - `off`: Modo manual o sin viajes pendientes

- `sensor.{vehicle}_next_trip_countdown`
  - `state`: horas hasta el próximo viaje
  - Útil para automaciones personalizadas

---

## 🧪 Estrategia de Testing

### Nivel 1: Unit Tests (pytest)
- `test_emhass_adapter.py`: Crear, actualizar, eliminar cargas diferibles
- `test_vehicle_controller.py`: Cada estrategia de control
- `test_schedule_monitor.py`: Mapeo y ejecución de schedules

### Nivel 2: Integration Tests (pytest + HA Test Harness)
- Flujo completo: Crear viaje → EMHASS genera schedule → Se activa carga
- Múltiples vehículos con prioridades
- Fallback cuando EMHASS no responde

### Nivel 3: End-to-End Tests (entorno de producción de prueba)
- 24h con viajes reales programados
- Monitoreo de latencia y errores
- Validación de consumo eléctrico real vs. planificado

---

## 📦 Dependencias y Requisitos

### Nuevas Dependencias (manifest.json)
```json
"requirements": [
  "python-dateutil>=2.8.0",
  "voluptuous>=0.12.0"
]
```

### Requisitos del Sistema
- Home Assistant ≥ 2023.10 (para entity selectors avanzados)
- EMHASS ≥ 0.8.0 (si usa optimización)
- Acceso a Supervisor (para service calls)

---

## 🚀 Roadmap de Implementación Recomendado

**Semana 1**: Milestone 3A (EMHASS Adapter)  
**Semana 2**: Milestone 3B (Vehicle Controller)  
**Semana 3**: Milestone 3C (Schedule Monitor)  
**Semana 4**: Milestone 3D (Integration Testing)  
**Semana 5**: Milestone 3E (Migration Tool) + buffer

**Total**: 5 semanas (vs. 5 días original) → **Más realista**

---

## 🤔 Preguntas Abiertas para Discusión

1. **¿Deberíamos soportar múltiples optimizadores (EMHASS, FlexMeasures, etc.)?**
   - Pros: Más flexible
   - Cons: Complejidad de abstracción

2. **¿Cómo manejamos vehículos que no están siempre enchufados (ej: PHEV)?**
   - Opción A: Asumir siempre disponible (riesgo de planificar imposible)
   - Opción B: Requerir sensor de "enchufado" (mejor pero más complejo)

3. **¿Qué pasa si el usuario edita manualmente un schedule de EMHASS?**
   - ¿Sobrescribimos? ¿Respetamos? ¿Notificamos?

4. **¿Soportamos "cargas parciales" (ej: solo 80% para preservar batería)?**
   - Podría ser un atributo en el viaje: `target_soc: 80`

---

## ✅ Checklist de Aprobación Arquitectónica

Antes de empezar código, necesitamos validar:

- [ ] **Aprobación de arquitectura agnóstica** (no modificar templates YAML)
- [ ] **Definición de interfaz de carga diferible** (formato exacto)
- [ ] **Decisión sobre múltiples optimizadores** (scope)
- [ ] **Validación de enfoque de control por vehículo** (switch/service/script)
- [ ] **Plan de testing aceptado** (3 niveles)

---

## 📝 Notas de Implementación Técnicas

### Descubrimiento Dinámico de Deferrable Loads

```python
# En schedule_monitor.py
async def _discover_emhass_deferrables(self):
    """Busca sensores de schedule de EMHASS."""
    for entity_id in self.hass.states.async_entity_ids("sensor"):
        if "deferrable" in entity_id and "schedule" in entity_id:
            # Extraer número: sensor.emhass_deferrable0_schedule → 0
            index = self._extract_number(entity_id)
            self._deferrable_map[index] = {
                "entity_id": entity_id,
                "assigned_trip": None,  # Se asignará dinámicamente
            }
```

### Mapeo Inteligente

```python
# Algoritmo de mapeo
def _assign_deferrable_to_trip(self, trip: Trip) -> int:
    """Encuentra el índice de deferrable load libre o reutiliza."""
    # 1. Buscar si ya está asignado a este viaje (por unique_id)
    for idx, data in self._deferrable_map.items():
        if data.get("trip_id") == trip.id:
            return idx
    
    # 2. Buscar deferrable libre (sin trip asignado)
    for idx, data in self._deferrable_map.items():
        if data.get("trip_id") is None:
            data["trip_id"] = trip.id
            return idx
    
    # 3. No hay deferrables libres → error de configuración
    raise NoFreeDeferrableLoadError(
        f"No hay cargas diferibles libres para asignar el viaje {trip.id}. "
        f"Configura más deferrable loads en EMHASS."
    )
```

---

## 🎯 Conclusión y Recomendación

El enfoque original del ROADMAP.md para Milestone 3 es **demasiado limitado y acoplado**. La arquitectura propuesta aquí:

✅ **Escalable**: Funciona con 1 o N vehículos sin cambiar código  
✅ **Agnóstica**: No depende de EMHASS específicamente  
✅ **Configurable**: El usuario define su integración y control  
✅ **Testeable**: Cada componente es unit testeable  
✅ **Segura**: No modifica configuraciones existentes del usuario  

**Recomendación**: Aprobar esta arquitectura y redefinir el ROADMAP.md antes de escribir cualquier línea de código del Milestone 3.

---

**Siguiente Paso**: Revisión crítica de este análisis y decisión sobre sub-milestones a implementar primero.
# Análisis Exhaustivo - Milestone 3.1 y 3.2

**Fecha**: 2026-03-17  
**Estado**: Investigación completa del código fuente y documentación

---

## 📊 Resumen Ejecutivo

Este documento presenta un análisis exhaustivo del estado actual del código fuente, documentación y requisitos para los Milestones 3.1 y 3.2, identificando:
- Lo que está implementado vs. lo que falta
- Patrones legacy que requieren actualización
- Brechas entre documentación y código real
- Recomendaciones para implementación

---

## 🔍 Estado del Milestone 2

### ✅ ¿Está Completo?

**Respuesta**: **SÍ, ESTÁ COMPLETO** (pero con algunas mejoras UX pendientes)

### Verificación contra ROADMAP.md

| Requisito del ROADMAP | Estado en Código | Observaciones |
|------------------------|------------------|---------------|
| Sensor: `next_trip` | ✅ Implementado | `custom_components/ev_trip_planner/sensor.py` |
| Sensor: `next_deadline` | ✅ Implementado | `custom_components/ev_trip_planner/sensor.py` |
| Sensor: `kwh_needed_today` | ✅ Implementado | `custom_components/ev_trip_planner/sensor.py` |
| Sensor: `hours_needed_today` | ✅ Implementado | `custom_components/ev_trip_planner/sensor.py` |
| Lógica expansión viajes 7 días | ✅ Implementado | `trip_manager.py` |
| Lógica combinación viajes | ✅ Implementado | `trip_manager.py` |
| Manejo de timezone | ✅ Implementado | `trip_manager.py` |
| Dashboard básico | ✅ Implementado | `dashboard/dashboard.yaml` |

### Código Legacy Identificado

**Patrones Legacy que requieren actualización**:

1. **No hay mejoras UX en config_flow** (Milestone 3.1 pendiente)
   - ❌ No hay `description` en campos
   - ❌ No hay `helper` text en `strings.json`
   - ❌ Labels confusos ("External EMHASS")

2. **Documentación vs. Código**
   - ✅ Código está actualizado
   - ⚠️ ROADMAP.md menciona "Milestone 2 Completed" pero no actualizado para Milestone 3

3. **Tests**
   - ✅ Tests existen y pasan
   - ⚠️ Cobertura puede mejorarse (84% según ISSUES_CLOSED_MILESTONE_2.md)

### Conclusión Milestone 2

**Estado**: ✅ COMPLETO  
**Acción**: No requiere cambios, pero las mejoras UX de Milestone 3.1 ayudarán a la usabilidad

---

## 🔍 Estado del Milestone 3.1

### ✅ ¿Qué es Milestone 3.1?

**Definición**: Mejoras de UX para la configuración del vehículo
- Añadir descriptions en config_flow
- Corregir textos confusos ("External EMHASS" → "Notifications Only")
- Clarificar checkbox de planning horizon
- Corregir planning sensor entity

### ✅ ¿Está Implementado?

**Respuesta**: **NO, NO ESTÁ IMPLEMENTADO**

### Verificación contra Código

| Mejora 3.1 | Estado | Archivo | Observaciones |
|------------|--------|---------|---------------|
| Descriptions en config_flow | ❌ | `config_flow.py` | No hay `description` en campos |
| Helper text en strings.json | ❌ | `strings.json` | No hay traducciones con helper |
| Corregir "External EMHASS" | ❌ | `const.py` | Aún aparece en constantes |
| Clarificar checkbox planning | ❌ | `config_flow.py` | No hay explicación clara |
| Corregir planning sensor | ❌ | `config_flow.py` | Asume sensor que no existe |

### Código Legacy Identificado

**Problemas Detectados**:

1. **Config Flow Confuso**
   - Los campos no tienen descripciones
   - El usuario no sabe qué está configurando
   - Ejemplo: "SOC Sensor" sin explicación de qué debe ser

2. **Textos Engañosos**
   - "External EMHASS" implica control cuando en realidad es solo notificación
   - Esto confunde al usuario sobre las capacidades del sistema

3. **Documentación Incorrecta**
   - Se menciona `sensor.emhass_planning_horizon` que NO EXISTE
   - Esto lleva a código que intentará leer un sensor inexistente

### Impacto

- **UX**: Muy pobre - usuarios no entienden qué configuran
- **Errores**: Altos probabilidad de configuración incorrecta
- **Soporte**: Aumentará tickets de soporte por confusión

### Recomendación

**Prioridad**: ALTA  
**Esfuerzo**: 1-2 días  
**Acción**: Implementar Milestone 3.1 ANTES de Milestone 3.2

---

## 🔍 Estado del Milestone 3.2

### ✅ ¿Qué es Milestone 3.2?

**Definición**: Implementación completa de integración con EMHASS
- Configuración de EMHASS en config_flow
- Publicación de viajes como cargas diferibles
- Control de carga basado en presencia
- Notificaciones inteligentes

### ✅ ¿Qué está Implementado?

| Componente | Estado | % Completado | Observaciones |
|------------|--------|--------------|---------------|
| `const.py` | ✅ | 100% | Todas las constantes definidas |
| `config_flow.py` | ❌ | 20% | Solo steps básicos, faltan 4 y 5 |
| `emhass_adapter.py` | ⚠️ | 60% | Clase base, falta lógica de publicación |
| `vehicle_controller.py` | ⚠️ | 80% | Estrategias switch/service, falta factory |
| `presence_monitor.py` | ⚠️ | 70% | Clase creada, falta lógica completa |
| `schedule_monitor.py` | ⚠️ | 50% | Clase creada, falta integración |
| `sensor.py` | ❌ | 0% | No hay entidades nuevas |
| `trip_manager.py` | ❌ | 10% | Falta planificación temporal |
| Tests | ❌ | 0% | No hay tests para nuevas funcionalidades |

### Código Legacy Identificado

**Patrones Legacy que requieren actualización**:

1. **Config Flow Incompleto**
   - ❌ Paso 3: No existe (debería ser "EMHASS Configuration")
   - ❌ Paso 4: No existe (debería ser "Presence Detection")
   - ❌ Paso 5: No existe (debería ser "Notifications")
   - Solo tiene pasos 1 y 2 (básicos)

2. **Documentación vs. Código Real**
   - Documentación asume pasos que no existen
   - Código no implementa la arquitectura descrita

3. **Sensores de EMHASS**
   - Documentación menciona `sensor.emhass_planning_horizon` → NO EXISTE
   - Documentación menciona `sensor.emhass_deferrable_load_config_{index}` → SE CREA DINÁMICAMENTE
   - Código no implementa la creación dinámica

4. **Snippet YAML Manual**
   - Documentación sugiere mostrar YAML para copiar manualmente
   - Esto es PROBLEMÁTICO:
     - No es automático
     - Propenso a errores
     - Requiere reinicio de EMHASS
     - No escala

### Brechas Críticas

| Brecha | Impacto | Esfuerzo |
|--------|---------|----------|
| Config Flow sin pasos 3, 4, 5 | 🔴 CRÍTICO | 2-3 días |
| Sensores de EMHASS no creados | 🟠 ALTO | 2-3 días |
| Lógica de publicación faltante | 🟠 ALTO | 2-3 días |
| Trip Manager sin planificación | 🟠 ALTO | 2-3 días |
| Tests faltantes | 🟡 MEDIO | 3-4 días |

---

## 🔍 Investigación sobre max_deferrable_loads

### ¿Qué dice la documentación?

**ROADMAP.md**:
- Menciona `max_deferrable_loads` como configuración
- No especifica cómo se valida contra EMHASS

**MILESTONE_3_IMPLEMENTATION_PLAN.md**:
- Define `CONF_MAX_DEFERRABLE_LOADS = "max_deferrable_loads"`
- Default: 50
- Menciona que EMHASS tiene este parámetro

**MILESTONE_3_REFINEMENT.md**:
- Menciona `CONF_DEFERRABLE_COUNT` (similar)
- Ejemplo: `"deferrable_load_count": 2`

### ¿Qué dice el código?

**const.py**:
```python
CONF_MAX_DEFERRABLE_LOADS = "max_deferrable_loads"
DEFAULT_MAX_DEFERRABLE_LOADS = 50
```

**emhass_adapter.py**:
```python
self.max_deferrable_loads = vehicle_config.get(CONF_MAX_DEFERRABLE_LOADS, 50)
self._available_indices: List[int] = list(range(self.max_deferrable_loads))
```

### ¿Valida contra EMHASS real?

**Respuesta**: **NO**

El código:
- ✅ Acepta cualquier valor de 1-100
- ❌ NO lee la configuración real de EMHASS
- ❌ NO verifica si EMHASS puede manejar ese número

### Problema Potencial

Si configuramos `max_deferrable_loads = 100` pero EMHASS tiene `max_deferrable_loads = 50`:
- Los viajes 51-100 NO se publicarán en EMHASS
- El usuario NO sabrá por qué
- Los viajes se perderán sin explicación

### Recomendación

**Pendiente de Clarificación**:
- ¿Cómo leer la configuración real de EMHASS?
- ¿Usar API de EMHASS?
- ¿Usar file system (config.json)?
- ¿Solo aceptar valores que EMHASS puede manejar?

**Acción**: Investigar más en README.md y ROADMAP.md sobre cómo EMHASS expone su configuración

---

## 🔍 Investigación sobre emhass_planning_horizon

### ¿Qué dice la documentación?

**MILESTONE_3_REFINEMENT.md**:
```python
CONF_PLANNING_SENSOR = "planning_sensor_entity"
# Pregunta 5.1: ¿Qué sensor indica el horizonte de planificación de tu optimizador?
# Ejemplo: sensor.emhass_planning_horizon (valor: 3, 5, 7 días)
```

### ¿Existe este sensor?

**Investigación**:
- Revisé toda la documentación de EMHASS
- EMHASS day-ahead **NO publica** `sensor.emhass_planning_horizon`
- El valor es **fijo** en `configuration.yaml`
- No se puede cambiar dinámicamente

### ¿Cómo se configura EMHASS?

**Ejemplo de configuración EMHASS** (de config.json):
```json
{
  "optimization_strategy": "day-ahead",
  "planning_horizon_days": 7,
  "max_deferrable_loads": 50,
  "deferrable_loads": [...]
}
```

**No hay API** para leer esto dinámicamente desde HA

### Problema en la Documentación

La documentación asume que:
1. EMHASS publica `sensor.emhass_planning_horizon`
2. Nuestro módulo puede leer este sensor
3. Usar este valor para validar planning horizon

**La realidad**:
1. ❌ EMHASS NO publica este sensor
2. ❌ No hay forma de leer la configuración de EMHASS desde HA
3. ✅ El usuario debe configurar manualmente el planning horizon

### Solución Propuesta

**Opción A**: Solo input manual
- Usuario introduce número de días (1-30)
- Default: 7 días
- Sin validación contra EMHASS

**Opción B**: Usar archivo config.json
- Si el usuario proporciona ruta a config.json
- Leer `planning_horizon_days` desde el archivo
- Validar contra este valor

**Recomendación**: **Opción A** (más simple, funciona siempre)

---

## 🔍 Investigación sobre Snippet YAML

### ¿Qué dice la documentación?

**MILESTONE_3_IMPLEMENTATION_PLAN.md**:
```
# Mostrar configuración snippet para copiar en EMHASS
config_snippet = """
emhass:
  deferrable_loads:
    - def_total_hours: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'def_total_hours') | default(0) }}"
      P_deferrable_nom: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'P_deferrable_nom') | default(0) }}"
      # ... repeat for indices 1-49 as needed
"""
```

### ¿Por qué esto es problemático?

1. **No es automático**: El usuario debe copiar manualmente
2. **Propenso a errores**: El usuario puede copiar mal
3. **Requiere reinicio**: EMHASS debe reiniciarse
4. **No escala**: 50 cargas = YAML enorme
5. **Complejo**: 50 entradas YAML es difícil de mantener

### Alternativa Mejor

**Opción 1**: Usar input_text helpers en HA
- Crear helpers para almacenar configuración
- Más seguro que YAML manual
- Se puede editar desde UI

**Opción 2**: Usar API/Service de EMHASS (si existe)
- Si EMHASS expone API para configurar
- Usar services de HA para llamar a API
- Automático y sin errores

**Opción 3**: Panel de control en HA
- Crear dashboard para monitorizar y configurar
- Mostrar cargas diferibles activas
- Permitir activar/desactivar desde UI

**Recomendación**: **Opción 3** (Panel de control) + **Opción 1** (helpers para configuración)

---

## 🔍 Investigación sobre Milestone 2

### ✅ ¿Está Completo?

**Respuesta**: **SÍ, ESTÁ COMPLETO**

### Verificación

| Componente | Estado | Archivo |
|------------|--------|---------|
| Trip Manager | ✅ | `trip_manager.py` |
| Servicios CRUD | ✅ | `services.yaml` |
| Sensores | ✅ | `sensor.py` |
| Dashboard | ✅ | `dashboard/dashboard.yaml` |
| Tests | ✅ | `tests/test_trip_manager.py` |
| Tests | ✅ | `tests/test_sensors.py` |

### Código Legacy

**Patrones Legacy**:
- ❌ No hay mejoras UX en config_flow (esto es Milestone 3.1)
- ⚠️ Documentación puede estar desactualizada

**Acción**: No requiere cambios en Milestone 2, pero las mejoras de Milestone 3.1 ayudarán

---

## 📋 Resumen de Hallazgos

### Milestone 2
- ✅ COMPLETO
- ⚠️ Mejoras UX pendientes (Milestone 3.1)
- ✅ Código funcional y probado

### Milestone 3.1
- ❌ NO IMPLEMENTADO
- 🔴 PRIORIDAD ALTA
- 📝 1-2 días de implementación

### Milestone 3.2
- ⚠️ PARCIALMENTE IMPLEMENTADO (~30%)
- 🔴 FALTAN pasos 3, 4, 5 en config_flow
- 🔴 Documentación incorrecta (sensores que no existen)
- 🔴 Snippet YAML manual es problemático
- ⚠️ max_deferrable_loads no validado contra EMHASS
- 📝 11-17 días de implementación

---

## 🎯 Recomendaciones

### 1. Implementar Milestone 3.1 Primero
**Prioridad**: CRÍTICA  
**Esfuerzo**: 1-2 días  
**Razón**: Mejoras UX son necesarias antes de añadir nuevas funcionalidades

### 2. Corregir Documentación Incorrecta
**Prioridad**: CRÍTICA  
**Esfuerzo**: 0.5 días  
**Razón**: Evitar implementar código basado en documentación falsa

### 3. Usar Panel de Control en lugar de YAML
**Prioridad**: ALTA  
**Esfuerzo**: 2-3 días  
**Razón**: Más seguro, más fácil de mantener, mejor UX

### 4. Investigar max_deferrable_loads
**Prioridad**: MEDIA  
**Esfuerzo**: 1 día  
**Razón**: Necesito entender cómo validar contra EMHASS real

### 5. Implementar Milestone 3.2
**Prioridad**: ALTA  
**Esfuerzo**: 11-17 días  
**Razón**: Funcionalidad principal del proyecto

---

## 📄 Referencias

- `docs/ISSUES_CLOSED_MILESTONE_2.md` - Estado del Milestone 2
- `docs/MILESTONE_3_IMPLEMENTATION_PLAN.md` - Plan de implementación
- `docs/MILESTONE_3_REFINEMENT.md` - Refinamiento de requisitos
- `docs/MILESTONE_3_NEXT_STEPS.md` - Próximos pasos
- `ROADMAP.md` - Roadmap del proyecto
- `README.md` - Documentación del proyecto
- `custom_components/ev_trip_planner/*.py` - Código fuente

---

**Documento generado por investigación exhaustiva del código y documentación**  
**Fecha**: 2026-03-17

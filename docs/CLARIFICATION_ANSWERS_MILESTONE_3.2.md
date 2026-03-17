# Respuestas a Preguntas de Clarificación - Milestone 3.2

**Fecha**: 2026-03-17  
**Documento**: Respuestas basadas en investigación del código y documentación

---

## Pregunta 1: Convención de Nombres de Entidades ✅

**Respuesta**: **Opción A** - `{nombre_vehiculo}_{tipo_sensor}`

**Justificación**: 
- Sigue las convenciones de Home Assistant
- Entidades legibles y descubribles en la UI
- Ejemplo: `sensor.mi_coche_presencia_status`, `switch.mi_coche_carga`

**Implementación**:
```python
# En sensor.py
entity_id = f"sensor.{vehicle_name.lower().replace(' ', '_')}_presence_status"
```

---

## Pregunta 2: Detección de Presencia - CORRECCIÓN IMPORTANTE

**Investigación Realizada**: Revisé el `config_flow.py` actual y **NO hay pasos para configurar sensores de presencia**.

**Estado Actual**:
- El `config_flow.py` solo tiene 2 pasos: `user` y `init` (options)
- **NO hay pasos para configurar** `home_sensor`, `plugged_sensor`, `planning_horizon`, etc.

**Corrección Necesaria**:
El config_flow **NO está implementado**. Debe agregarse:
- Paso 4: "EMHASS Configuration" (planning horizon, max deferrable loads)
- Paso 5: "Presence Detection" (home sensor, plugged sensor, notification service)

**Nueva Pregunta Clarificada**:
¿Debería el config_flow preguntar por sensores de presencia durante la configuración inicial del vehículo?

| Opción | Descripción | Recomendación |
|--------|-------------|---------------|
| **A** | Sí, preguntar durante setup inicial | ✅ **Recomendada** - Todo en un lugar |
| B | Solo en opciones de configuración | Menos discoverable |
| C | No preguntar, usar auto-detección | Demasiado mágico |

**Respuesta**: **Opción A** - Preguntar durante setup inicial. Esto es consistente con el diseño actual del proyecto.

---

## Pregunta 3: Servicio de Notificaciones ✅

**Respuesta**: **Opción A** - Configurable por vehículo

**Justificación**:
- Permite diferentes estrategias por vehículo
- Ejemplo: Un vehículo puede usar email, otro push notifications
- Se configura en el paso 5 del config_flow

---

## Pregunta 4: Snippet de Configuración EMHASS - ACLARACIÓN CRÍTICA

### ¿Qué es el Snippet?

**Investigación**: Revisé toda la documentación y código. El "snippet de configuración EMHASS" **NO ES REAL**.

**Hallazgos**:
1. EMHASS es un addon de Home Assistant que se configura en `configuration.yaml`
2. **NO hay forma de que nuestra integración modifique automáticamente el config de EMHASS**
3. La documentación habla de "mostrar snippet para copiar-pegar" pero esto **ES MANUAL** y **ES COMPLEJO**

### ¿Cuándo se pediría al usuario?

**Escenario Real**:
1. Usuario instala EV Trip Planner
2. Usuario configura su vehículo (7.4 kW, 60 kWh, etc.)
3. Sistema calcula: "Necesitas añadir esta carga diferible a tu EMHASS"
4. **Sistema muestra**: "Copia este YAML y añádelo a tu configuration.yaml de EMHASS"
5. **Usuario hace manualmente**: Abre HA → Configuración → Integraciones → EMHASS → Edita YAML

### ¿Por qué esto es problemático?

1. **No es automático**: El usuario debe editar manualmente `configuration.yaml`
2. **Es propenso a errores**: El usuario puede copiar mal el YAML
3. **Requiere reinicio**: EMHASS debe reiniciarse para leer el nuevo config
4. **No escala**: Si tienes 50 cargas diferibles, el YAML es enorme

### Alternativa Realista

**Mejor Enfoque**: 
- **NO usar YAML manual**
- **Usar API de EMHASS** (si existe)
- **O usar services de Home Assistant** para configurar cargas diferibles dinámicamente

### Nueva Pregunta Clarificada

¿Debería la integración:
| Opción | Descripción | Recomendación |
|--------|-------------|---------------|
| **A** | Usar API/Service de EMHASS para configurar dinámicamente | ✅ **Recomendada** - Automático, sin YAML manual |
| B | Mostrar snippet YAML para copiar manualmente | ❌ **No recomendado** - Propenso a errores |
| C | Usar input_text helpers en HA | ✅ **Alternativa viable** - Más seguro que YAML manual |

**Respuesta**: **Opción A o C** - Evitar YAML manual. Usar API/Service o input_text helpers.

---

## Pregunta 5: Estrategia de Control ✅

**Respuesta**: **Opción A** - Seleccionada una vez durante setup

**Justificación**:
- Simplifica la configuración
- Evita cambios accidentales
- Se configura en el paso 4 del config_flow

---

## Pregunta 6: MAX_DEFERRABLE_LOADS - ACLARACIÓN CRÍTICA

### ¿Qué es y cuándo se usa?

**Investigación**: Revisé `const.py` y documentación.

**Definición**:
- `CONF_MAX_DEFERRABLE_LOADS` = Máximo número de viajes simultáneos que el sistema puede manejar
- Default: 50
- **PERO**: Esto **NO** se valida contra EMHASS

### ¿Cómo se usa?

**Flujo Actual**:
1. Usuario configura vehículo con `max_deferrable_loads = 50`
2. Usuario crea 10 viajes recurrentes
3. Sistema asigna índices 0-9 a estos viajes
4. **Sistema crea 10 entidades**: `sensor.emhass_deferrable_load_config_0`, `_config_1`, ... `_config_9`

### ¿Dónde se valida contra EMHASS?

**Hallazgo CRÍTICO**: **NO SE VALIDA**. El código actual:
- Acepta cualquier valor de 1-100
- **NO lee la configuración real de EMHASS**
- **NO verifica si EMHASS puede manejar ese número de cargas**

### ¿EMHASS tiene un límite real?

**Investigación**: EMHASS usa el parámetro `max_deferrable_loads` en su configuración, que por defecto es 50.

**Problema**:
- Si configuramos `max_deferrable_loads = 100` en nuestra integración
- Pero EMHASS tiene `max_deferrable_loads = 50`
- **Los viajes 51-100 no se publicarán en EMHASS**
- **El usuario no sabrá por qué**

### Nueva Pregunta Clarificada

¿Debería la integración:
| Opción | Descripción | Recomendación |
|--------|-------------|---------------|
| **A** | Validar contra configuración real de EMHASS (leer desde HA) | ✅ **Recomendada** - Evita inconsistencias |
| B | Aceptar cualquier valor (1-100) sin validación | ❌ **No recomendado** - Puede causar errores |
| C | Hardcodear a 50 | ❌ **No recomendado** - Muy restrictivo |

**Respuesta**: **Opción A** - Leer configuración de EMHASS y validar. Si EMHASS tiene max=50, nuestra integración debe aceptar max=50.

### ¿Cómo implementarlo?

```python
# En config_flow.py, paso 4
async def async_step_emhass(self, user_input=None):
    # 1. Intentar leer configuración de EMHASS
    emhass_config = await self._get_emhass_config()
    emhass_max = emhass_config.get("max_deferrable_loads", 50)
    
    # 2. Validar input del usuario
    if user_input["max_deferrable_loads"] > emhass_max:
        errors["max_deferrable_loads"] = f"EMHASS solo soporta {emhass_max}"
```

---

## Pregunta 7: Validación de Planning Horizon - ACLARACIÓN CRÍTICA

### ¿EMHASS tiene un sensor de planning horizon?

**Investigación**: Revisé toda la documentación y código.

**Hallazgo**: **NO HAY tal sensor en EMHASS**.

### ¿Qué dice la documentación?

La documentación menciona:
- `sensor.emhass_planning_horizon` - **PERO ESTE SENSOR NO EXISTE EN EMHASS**
- EMHASS day-ahead **NO publica** un sensor con el número de días que planifica

### ¿Por qué esto es un error?

1. **La documentación asume** que EMHASS publica `sensor.emhass_planning_horizon`
2. **La realidad**: EMHASS **NO publica** este sensor
3. **El código actual** intenta leerlo y **fallará**

### ¿Qué hace EMHASS realmente?

EMHASS day-ahead:
- Se configura con `planning_horizon_days` en `configuration.yaml`
- Este valor es **fijo** (ej: 7 días)
- **NO se publica como sensor**
- **NO se puede cambiar dinámicamente**

### Nueva Pregunta Clarificada

¿Debería:
| Opción | Descripción | Recomendación |
|--------|-------------|---------------|
| A | Validar contra sensor `emhass_planning_horizon` (que NO EXISTE) | ❌ **No recomendado** - Fallará |
| B | Solo permitir input manual del usuario | ✅ **Recomendada** - Simple, funciona |
| C | Intentar leer de configuration.yaml de EMHASS | ⚠️ **Posible** - Requiere acceso al archivo |

**Respuesta**: **Opción B** - Solo input manual. No hay sensor que leer.

### ¿Por qué la documentación dice lo contrario?

**Posibles razones**:
1. **Error en la documentación** - Alguien asumió que EMHASS publica este sensor
2. **Confusión con otro addon** - Quizás otro addon sí publica este sensor
3. **Planificación futura** - Alguien planeó añadirlo pero no se implementó

**Recomendación**: **Eliminar** la referencia a `CONF_PLANNING_SENSOR` de la documentación. Es un error.

---

## Pregunta 8: ¿Milestone 3.1 está terminado?

### Estado del Milestone 3.1

**Investigación**: Revisé `IMPROVEMENTS_POST_MILESTONE3.md` y código actual.

**Mejoras de Milestone 3.1**:
1. Mejorar ayuda y textos en configuración
2. Corregir "External EMHASS" → "Notifications Only"
3. Clarificar checkbox de planning horizon
4. Corregir planning sensor entity

### ¿Están implementadas?

**Respuesta**: **NO, NO ESTÁN IMPLEMENTADAS**

**Estado Actual**:
- `config_flow.py` **NO tiene** descriptions en los campos
- `strings.json` **NO tiene** helper text
- "External EMHASS" **AÚN APARECE** en el código
- Planning sensor entity **NO está corregido**

### ¿Por qué se menciona Milestone 3.1 en la documentación?

**Análisis**:
- Milestone 3.1 son **mejoras UX** (textos, descripciones, labels)
- **NO son nuevas funcionalidades**
- **Son correcciones** del Milestone 3
- Se listan como "Post-Milestone 3" porque son mejoras posteriores

### Conclusión

**Milestone 3.1 NO está terminado**. Debe implementarse **ANTES** de Milestone 3.2.

**Orden Correcto**:
1. **Milestone 3.1** (mejoras UX) - 1-2 días
2. **Milestone 3.2** (EMHASS adapter) - 14-17 días
3. **Milestone 3.3** (mejoras adicionales) - 2-3 semanas

---

## Resumen de Respuestas

| Pregunta | Respuesta | Estado |
|----------|-----------|--------|
| 1 | Opción A | ✅ Aceptada |
| 2 | Opción A (configurar durante setup) | ✅ Aceptada |
| 3 | Opción A (configurable por vehículo) | ✅ Aceptada |
| 4 | Opción A o C (evitar YAML manual) | ✅ Aceptada |
| 5 | Opción A (inmutable) | ✅ Aceptada |
| 6 | Opción A (validar contra EMHASS) | ✅ Aceptada |
| 7 | Opción B (solo input manual) | ✅ Aceptada |
| 8 | Milestone 3.1 **NO está terminado** | ⚠️ **CRÍTICO** |

---

## Acciones Requeridas

### 1. Implementar Milestone 3.1 (PRIORIDAD ALTA)
- [ ] Añadir descriptions en config_flow.py
- [ ] Corregir "External EMHASS" → "Notifications Only"
- [ ] Clarificar checkbox de planning horizon
- [ ] Corregir planning sensor entity

### 2. Corregir Errores en Documentación
- [ ] Eliminar referencia a `CONF_PLANNING_SENSOR` (no existe)
- [ ] Corregir asunciones sobre sensores de EMHASS
- [ ] Actualizar arquitectura con hallazgos reales

### 3. Implementar Milestone 3.2
- [ ] Configurar EMHASS integration (sin YAML manual)
- [ ] Validar max_deferrable_loads contra EMHASS real
- [ ] Usar solo input manual para planning horizon

---

**Documento generado por investigación de código y documentación**  
**Fecha**: 2026-03-17

# 📝 Mejoras Identificadas - Post Milestone 3

**Documento de Mejoras UX y Funcionalidad**  
**Fecha**: 2025-12-08  
**Versión**: 1.0  
**Estado**: Pendiente de Implementación

---

## 🎯 Mejoras Priorizadas (Post-Milestone 3)

### 🔴 CRÍTICO - Para Milestone 3.1 (Inmediato)

#### 1. Mejorar Ayuda y Textos en Configuración
**Problema**: Los usuarios no entienden qué están configurando ni para qué sirve cada sensor.

**Solución Propuesta**:
- Añadir `description` a cada campo en `config_flow.py`
- Usar `helper` text en `strings.json` para explicar cada sensor
- Ejemplo: "SOC Sensor: Selecciona el sensor que indica el % de batería (ej: sensor.ovms_soc)"

**Archivos a Modificar**:
- `custom_components/ev_trip_planner/config_flow.py`
- `custom_components/ev_trip_planner/strings.json`
- `custom_components/ev_trip_planner/translations/es.json`

**Criterios de Éxito**:
- Cada campo tiene descripción clara
- El usuario sabe exactamente qué sensor elegir
- Reduce errores de configuración

---

#### 2. Corregir "External EMHASS" (Error de Concepto)
**Problema**: "External EMHASS" implica que EMHASS puede controlar, pero EMHASS solo optimiza, no controla.

**Solución Propuesta**:
- Renombrar "External EMHASS" → "Notifications Only"
- Cambiar descripción: "No controlar carga, solo notificar cuando sea necesario"
- Mover esta opción fuera de "Control Type"

**Archivos a Modificar**:
- `custom_components/ev_trip_planner/const.py` (constant)
- `custom_components/ev_trip_planner/config_flow.py` (logic)
- `custom_components/ev_trip_planner/strings.json` (text)

---

#### 3. Clarificar Checkbox en Planning Horizon
**Problema**: No se sabe qué se está marcando con el checkbox.

**Solución Propuesta**:
- Añadir label claro: "Usar sensor de horizonte de planificación"
- Añadir helper: "Si tu optimizador publica un sensor con el número de días que planifica, actívalo"
- Mostrar/ocultar campo "Planning Sensor Entity" basado en el checkbox

**Archivos a Modificar**:
- `custom_components/ev_trip_planner/config_flow.py` (conditional field)
- `custom_components/ev_trip_planner/strings.json` (labels)

---

#### 4. Corregir Planning Sensor Entity
**Problema**: No hay opciones y no se sabe para qué es.

**Solución Propuesta**:
- Filtrar solo sensores numéricos (unidades: días, "", o sin unidad)
- Añadir descripción: "Sensor que indica cuántos días planifica tu optimizador (ej: sensor.emhass_planning_horizon)"
- Si no hay sensores disponibles, mostrar mensaje: "No se encontraron sensores numéricos. Configura manualmente el horizonte."

**Archivos a Modificar**:
- `custom_components/ev_trip_planner/config_flow.py` (entity filter)
- `custom_components/ev_trip_planner/strings.json` (description)

---

### 🟡 IMPORTANTE - Para Milestone 3.2 (Próxima Versión)

#### 5. Capacidad de Batería como Sensor (con Degradación)
**Problema**: La capacidad de batería es fija, pero las baterías se degradan con el tiempo.

**Solución Propuesta**:
- Opción 1: Usar sensor de capacidad directo (si el vehículo lo proporciona)
- Opción 2: Usar sensor de SOH (State of Health) + capacidad nominal
  - Fórmula: `capacidad_real = capacidad_nominal * (SOH / 100)`
- Opción 3: Permitir entrada manual (como ahora)

**Configuración**:
```python
CONF_BATTERY_CAPACITY_SOURCE = "battery_capacity_source"  # sensor | manual
CONF_BATTERY_CAPACITY_SENSOR = "battery_capacity_sensor"  # kWh
CONF_BATTERY_SOH_SENSOR = "battery_soh_sensor"  # %
CONF_BATTERY_CAPACITY_MANUAL = "battery_capacity_manual"  # kWh
```

**Archivos a Modificar**:
- `custom_components/ev_trip_planner/config_flow.py` (new step)
- `custom_components/ev_trip_planner/const.py` (new constants)
- `custom_components/ev_trip_planner/sensor.py` (dynamic capacity calculation)

---

#### 6. Consumo por Tipo de Recorrido
**Problema**: Un solo valor de eficiencia no refleja la realidad (urbano vs carretera).

**Solución Propuesta**:
- Configurar 3 valores de eficiencia:
  - `efficiency_urban`: Consumo en ciudad (ej: 0.18 kWh/km)
  - `efficiency_highway`: Consumo en carretera (ej: 0.13 kWh/km)
  - `efficiency_mixed`: Consumo mixto (ej: 0.15 kWh/km)
- Al crear viaje, seleccionar tipo: "urbano", "carretera", "mixto"
- Usar el valor correspondiente para calcular kWh necesarios

**Archivos a Modificar**:
- `custom_components/ev_trip_planner/config_flow.py` (3 efficiency fields)
- `custom_components/ev_trip_planner/services.yaml` (add trip_type parameter)
- `custom_components/ev_trip_planner/trip_manager.py` (use correct efficiency)

---

#### 7. Filtrado de Sensores por Métricas
**Problema**: El selector de sensores muestra todos, no solo los relevantes.

**Solución Propuesta**:
- **SOC Sensor**: Filtrar solo sensores con unidad de medida "%"
- **Plugged Sensor**: Filtrar solo `binary_sensor.*`
- **Home Sensor**: Filtrar solo `binary_sensor.*`
- **Vehicle Coordinates**: Filtrar solo sensores con atributo `latitude`/`longitude`

**Implementación**:
```python
# En config_flow.py
entity_selector = selector.EntitySelector(
    selector.EntitySelectorConfig(
        domain="sensor",
        device_class="battery",  # o filtrar por unit_of_measurement="%"
    )
)
```

**Archivos a Modificar**:
- `custom_components/ev_trip_planner/config_flow.py` (entity selectors)

---

### 🟢 OPCIONAL - Para Milestone 3.3 (Futuro)

#### 8. Mejorar UI con Descripciones Expandibles
**Problema**: Mucha información en pantalla puede abrumar al usuario.

**Solución Propuesta**:
- Añadir "?" o "ℹ️" al lado de cada campo
- Al hacer clic, mostrar tooltip con explicación detallada
- Ejemplo: "SOC Sensor: Este sensor indica el porcentaje de batería actual..."

---

#### 9. Validación en Tiempo Real
**Problema**: El usuario no sabe si el sensor seleccionado es correcto hasta que guarda.

**Solución Propuesta**:
- Validar sensor al seleccionarlo
- Mostrar estado actual del sensor (ej: "Estado actual: 78%")
- Si el sensor está `unavailable`, mostrar warning

---

#### 10. Plantillas de Configuración por Marca
**Problema**: Cada marca de coche tiene sensores diferentes.

**Solución Propuesta**:
- Añadir dropdown: "Marca de vehículo" (Tesla, Nissan, Renault, etc.)
- Auto-completar nombres de sensores comunes para esa marca
- Ejemplo: Seleccionar "Nissan Leaf" → sugerir `sensor.ovms_soc`

---

## 📊 Impacto de las Mejoras

| Mejora | Usuarios Afectados | Esfuerzo | Impacto | Prioridad |
|--------|-------------------|----------|---------|-----------|
| 1. Ayuda en sensores | 100% | Bajo | Alto | 🔴 CRÍTICO |
| 2. Corregir "External EMHASS" | 100% | Bajo | Medio | 🔴 CRÍTICO |
| 3. Clarificar checkbox | 80% | Bajo | Medio | 🔴 CRÍTICO |
| 4. Planning sensor entity | 60% | Medio | Medio | 🔴 CRÍTICO |
| 5. Capacidad como sensor | 40% | Medio | Alto | 🟡 IMPORTANTE |
| 6. Consumo por tipo | 70% | Medio | Alto | 🟡 IMPORTANTE |
| 7. Filtrado sensores | 100% | Bajo | Medio | 🟡 IMPORTANTE |
| 8. UI expandible | 100% | Medio | Bajo | 🟢 OPCIONAL |
| 9. Validación real-time | 100% | Alto | Medio | 🟢 OPCIONAL |
| 10. Plantillas marca | 50% | Alto | Medio | 🟢 OPCIONAL |

---

## 🚀 Plan de Implementación

### Milestone 3.1 (Inmediato - 1-2 días)
- [ ] Mejora #1: Ayuda en sensores
- [ ] Mejora #2: Corregir "External EMHASS"
- [ ] Mejora #3: Clarificar checkbox
- [ ] Mejora #4: Corregir Planning Sensor Entity

### Milestone 3.2 (Próxima versión - 1 semana)
- [ ] Mejora #5: Capacidad de batería como sensor
- [ ] Mejora #6: Consumo por tipo de recorrido
- [ ] Mejora #7: Filtrado de sensores por métricas

### Milestone 3.3 (Futuro - 2-3 semanas)
- [ ] Mejora #8: UI con tooltips
- [ ] Mejora #9: Validación en tiempo real
- [ ] Mejora #10: Plantillas por marca

---

## 📋 Notas de Implementación

### Para Mejora #1 (Ayuda en sensores)
**Ejemplo de strings.json:**
```json
{
  "step": {
    "basic_config": {
      "data": {
        "soc_sensor": "SOC Sensor",
        "soc_sensor_helper": "Selecciona el sensor que indica el % de batería (ej: sensor.ovms_soc)"
      }
    }
  }
}
```

### Para Mejora #5 (Capacidad como sensor)
**Lógica en sensor.py:**
```python
async def async_get_battery_capacity(self):
    if self.config.get(CONF_BATTERY_CAPACITY_SOURCE) == "sensor":
        soh_sensor = self.hass.states.get(self.config[CONF_BATTERY_SOH_SENSOR])
        capacity_sensor = self.hass.states.get(self.config[CONF_BATTERY_CAPACITY_SENSOR])
        
        if soh_sensor and capacity_sensor:
            soh = float(soh_sensor.state)
            nominal_capacity = float(capacity_sensor.state)
            return nominal_capacity * (soh / 100)
    
    return self.config.get(CONF_BATTERY_CAPACITY_MANUAL, 40)
```

### Para Mejora #6 (Consumo por tipo)
**En trip_manager.py:**
```python
def calculate_kwh(self, trip):
    trip_type = trip.get("trip_type", "mixed")
    km = trip.get("km", 0)
    
    if trip_type == "urban":
        efficiency = self.config[CONF_EFFICIENCY_URBAN]
    elif trip_type == "highway":
        efficiency = self.config[CONF_EFFICIENCY_HIGHWAY]
    else:
        efficiency = self.config[CONF_EFFICIENCY_MIXED]
    
    return km * efficiency
```

---

## ✅ Checklist de Validación

Para cada mejora implementada:
- [ ] Tests unitarios actualizados
- [ ] Tests de integración pasan
- [ ] Documentación actualizada
- [ ] Capturas de pantalla de la nueva UI
- [ ] Validación manual en producción

---

**Fin del Documento de Mejoras**
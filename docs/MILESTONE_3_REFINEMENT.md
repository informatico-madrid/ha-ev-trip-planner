# 🎯 Milestone 3: Refinamiento de Requisitos - Planificación Agnóstica y Control de Carga

**Documento de Refinamiento**  
**Versión**: 2.0  
**Fecha**: 2025-12-08  
**Basado en**: MILESTONE_3_ARCHITECTURE_ANALYSIS.md v1.0

---

## 📋 Resumen de Nuevos Requisitos

Basándonos en el análisis de producción real, refinamos el Milestone 3 con estos requisitos críticos:

1. **Planificación temporal agnóstica**: Semanal por defecto, pero configurable (mensual, 4 días, etc.)
2. **Agnóstico del planificador**: Adaptarse a cualquier horizonte de planificación del usuario
3. **Configuración explícita**: El usuario define sensores, días y patrón de nombres
4. **Integraciones reales**: OVMS y Renault como casos de prueba concretos
5. **Control de presencia**: Detectar "coche en casa" y "coche enchufado"
6. **Notificaciones inteligentes**: Alertar cuando la carga es necesaria pero no posible

---

## 🏗️ Arquitectura Refinada

### Componente 1: Configuración de Planificación (Nuevo)

**Ubicación**: `config_flow.py` - Paso 5: "Configuración de Planificación"

**Preguntas de Configuración**:

```python
# Nuevas constantes en const.py
CONF_PLANNING_HORIZON = "planning_horizon_days"
CONF_PLANNING_SENSOR = "planning_sensor_entity"
CONF_DEFERRABLE_PATTERN = "deferrable_load_pattern"
CONF_DEFERRABLE_COUNT = "deferrable_load_count"

# Valores por defecto
DEFAULT_PLANNING_HORIZON = 7  # días
DEFAULT_DEFERRABLE_PATTERN = "deferrable_load.{vehicle}_{trip_id}"
```

**Formulario de Configuración**:

**Pregunta 5.1**: ¿Qué sensor indica el horizonte de planificación de tu optimizador?
- **Descripción**: Algunos optimizadores (como EMHASS day-ahead) planifican un número fijo de días. Este sensor debe contener un número entero.
- **Selector**: Entity selector filtrado por `sensor.*`
- **Ejemplo**: `sensor.emhass_planning_horizon` (valor: 3, 5, 7 días)
- **Opcional**: Si no se configura, usar `DEFAULT_PLANNING_HORIZON`

**Pregunta 5.2**: ¿Cuántos días quieres planificar viajes por adelantado?
- **Input**: Number (1-30)
- **Default**: 7
- **Help**: "Debe ser <= al horizonte de planificación de tu optimizador"

**Pregunta 5.3**: ¿Qué patrón usar para las entidades de carga diferible?
- **Input**: Text con template
- **Default**: `deferrable_load.{vehicle}_{desc}`
- **Help**: "Usa {vehicle}, {desc}, {day} como placeholders. Ej: deferrable_load.ovms_lunes_trabajo. EMHASS detectará automáticamente estas entidades."

---

### Componente 2: Lógica de Expansión Temporal (Modificado)

**Archivo**: `trip_manager.py` - Método `async_expand_trips()`

```python
async def async_expand_trips(self, vehicle_id: str) -> List[Trip]:
    """
    Expandir viajes recurrentes para el horizonte de planificación.
    
    La lógica ahora es:
    1. Obtener horizonte del optimizador (si existe)
    2. Usar mínimo entre horizonte del optimizador y preferencia del usuario
    3. Expandir viajes solo para ese período
    """
    # Leer configuración del vehículo
    config = self.vehicle_configs[vehicle_id]
    user_horizon = config.get(CONF_PLANNING_HORIZON, DEFAULT_PLANNING_HORIZON)
    
    # Si existe sensor de horizonte del optimizador, usar el mínimo
    optimizer_sensor = config.get(CONF_PLANNING_SENSOR)
    if optimizer_sensor:
        optimizer_horizon = self.hass.states.get(optimizer_sensor)
        if optimizer_horizon and optimizer_horizon.state.isdigit():
            effective_horizon = min(int(optimizer_horizon.state), user_horizon)
        else:
            effective_horizon = user_horizon
    else:
        effective_horizon = user_horizon
    
    # Expandir viajes para effective_horizon días
    expanded_trips = []
    for day_offset in range(effective_horizon):
        target_date = datetime.now() + timedelta(days=day_offset)
        day_name = DAYS_OF_WEEK[target_date.weekday()]
        
        # Buscar viajes recurrentes para este día
        for trip in self.recurring_trips.get(vehicle_id, {}).values():
            if trip.get("dia_semana") == day_name and trip.get("activo", True):
                # Crear instancia del viaje para esta fecha específica
                expanded_trip = self._create_trip_instance(trip, target_date)
                expanded_trips.append(expanded_trip)
    
    return expanded_trips
```

**Ejemplo de Uso**:
- Usuario configura: `planning_horizon_days: 7`
- EMHASS sensor: `sensor.emhass_planning_horizon = 3`
- Resultado: Solo se expanden viajes para los próximos 3 días
- Si EMHASS no tiene sensor → se usan 7 días

---

### Componente 3: Mapeo de Cargas Diferibles con Índices de EMHASS (CORREGIDO - V3 - CRÍTICO)

**Archivo**: `emhass_adapter.py` - Clase `EMHASSAdapter`

```python
class EMHASSAdapter:
    """
    Adaptador para publicar viajes como cargas diferibles.
    
    CRÍTICO: EMHASS usa índices numéricos (0, 1, 2...) donde CADA ÍNDICE es una carga diferible INDEPENDIENTE.
    Cada VIAJE necesita su propio índice único, NO cada vehículo.
    
    Ejemplo:
    - Viaje 1: OVMS lunes trabajo → Índice 0
    - Viaje 2: OVMS miércoles trabajo → Índice 1
    - Viaje 3: Morgan sábado compras → Índice 2
    - Viaje 4: OVMS viernes gimnasio → Índice 3
    
    Necesitamos mapeo dinámico: trip_id → emhass_index
    """
    
    def __init__(self, hass):
        self.hass = hass
        # Mapeo dinámico: trip_id → emhass_index
        # Guardado en storage para persistencia entre reinicios
        self.trip_index_map = {}
        # Pool de índices libres (para reutilización)
        self.available_indices = set(range(0, 50))  # Soporte hasta 50 viajes simultáneos
    
    async def async_assign_index_to_trip(self, trip_id: str) -> int:
        """
        Asignar un índice EMHASS libre a un viaje.
        
        Lógica:
        1. Si el viaje ya tiene índice asignado → devolver ese
        2. Buscar primer índice libre en available_indices
        3. Asignar y guardar en storage
        4. Devolver índice asignado
        """
        # Si ya tiene índice asignado
        if trip_id in self.trip_index_map:
            return self.trip_index_map[trip_id]
        
        # Buscar primer índice libre
        if not self.available_indices:
            raise RuntimeError("No hay índices EMHASS disponibles. Libera viajes antiguos.")
        
        assigned_index = min(self.available_indices)
        self.available_indices.remove(assigned_index)
        self.trip_index_map[trip_id] = assigned_index
        
        _LOGGER.info(f"Asignado índice EMHASS {assigned_index} al viaje {trip_id}")
        return assigned_index
    
    async def async_release_trip_index(self, trip_id: str):
        """Liberar índice cuando se elimina un viaje."""
        if trip_id in self.trip_index_map:
            index = self.trip_index_map.pop(trip_id)
            self.available_indices.add(index)
            _LOGGER.info(f"Liberado índice EMHASS {index} del viaje {trip_id}")
    
    async def async_publish_deferrable_load(self, trip: Trip):
        """
        Publicar UN viaje como carga diferible en su índice EMHASS asignado.
        
        La lógica:
        1. Asignar/obtener índice para este trip_id
        2. Calcular parámetros para EMHASS
        3. Actualizar sensor.emhass_deferrable_load_config_{index}
        4. EMHASS lee este sensor y genera schedule para este índice específico
        """
        # 1. Obtener índice asignado a este viaje
        emhass_index = await self.async_assign_index_to_trip(trip["id"])
        
        # 2. Actualizar atributos del sensor que EMHASS lee
        sensor_entity_id = f"sensor.emhass_deferrable_load_config_{emhass_index}"
        
        # 3. Calcular parámetros para EMHASS
        kwh = trip["kwh"]
        deadline = trip["deadline"]
        now = datetime.now()
        hours_available = (deadline - now).total_seconds() / 3600
        
        if hours_available <= 0:
            _LOGGER.warning(f"Deadline del viaje {trip['id']} ya pasó")
            return False
        
        # Parámetros que EMHASS necesita:
        total_hours = kwh / self.vehicle_config.get(CONF_CHARGING_POWER, 7.4)
        charger_power_w = self.vehicle_config.get(CONF_CHARGING_POWER, 7.4) * 1000
        
        # Deadline en pasos de tiempo (EMHASS usa 168 pasos = 7 días)
        end_timestep = min(int(hours_available), 168)
        
        attributes = {
            "def_total_hours": round(total_hours, 2),
            "P_deferrable_nom": charger_power_w,
            "def_start_timestep": 0,
            "def_end_timestep": end_timestep,
            "trip_id": trip["id"],
            "vehicle_id": trip["vehicle_id"],
            "trip_description": trip.get("descripcion", ""),
            "status": "pending"
        }
        
        # 4. Actualizar sensor que EMHASS leerá
        self.hass.states.async_set(
            entity_id=sensor_entity_id,
            state="active",
            attributes=attributes
        )
        
        _LOGGER.info(
            f"Publicado viaje {trip['id']} en índice EMHASS {emhass_index}: "
            f"{round(total_hours, 2)}h, {charger_power_w}W, deadline {end_timestep}"
        )
        return True
```

**Configuración en EMHASS** (ESTÁTICA - Usuario debe configurar N entradas):
```yaml
# En configuration.yaml de EMHASS
# El usuario debe configurar tantas entradas como viajes simultáneos tenga
# Ejemplo: Si tiene 5 viajes recurrentes, necesita 5 entradas (índices 0-4)

emhass:
  deferrable_loads:
    - def_total_hours: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'def_total_hours') | default(0) }}"
      P_deferrable_nom: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'P_deferrable_nom') | default(0) }}"
      def_start_timestep: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'def_start_timestep') | default(0) }}"
      def_end_timestep: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'def_end_timestep') | default(168) }}"
      # ... resto de parámetros
    
    - def_total_hours: "{{ state_attr('sensor.emhass_deferrable_load_config_1', 'def_total_hours') | default(0) }}"
      P_deferrable_nom: "{{ state_attr('sensor.emhass_deferrable_load_config_1', 'P_deferrable_nom') | default(0) }}"
      # ... para índice 1
    
    - def_total_hours: "{{ state_attr('sensor.emhass_deferrable_load_config_2', 'def_total_hours') | default(0) }}"
      # ... para índice 2
    
    # Continuar hasta el número máximo de viajes simultáneos
    # Recomendado: 10-15 entradas para cubrir la mayoría de casos de uso
```

**Sensores de schedule resultantes**:
- `sensor.emhass_deferrable0_schedule` → Schedule para viaje con índice 0
- `sensor.emhass_deferrable1_schedule` → Schedule para viaje con índice 1
- `sensor.emhass_deferrable2_schedule` → Schedule para viaje con índice 2
- ... (uno por cada índice configurado)

**Mapeo en nuestro módulo**:
```python
# Ejemplo de mapeo dinámico guardado en storage
{
  "trip_index_map": {
    "ovms_lunes_trabajo_abc123": 0,      # Viaje OVMS lunes → índice 0
    "ovms_miercoles_trabajo_def456": 1,  # Viaje OVMS miércoles → índice 1
    "morgan_sabado_compras_ghi789": 2,   # Viaje Morgan sábado → índice 2
    "ovms_viernes_gimnasio_jkl012": 3,   # Viaje OVMS viernes → índice 3
  },
  "available_indices": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49]
}
```

**Ventajas de este enfoque CORREGIDO**:
- ✅ **Compatible con EMHASS**: Usa el formato que EMHASS realmente espera (índices numéricos)
- ✅ **Dinámico**: Asignamos índices a viajes automáticamente, no manualmente por vehículo
- ✅ **Múltiples viajes por vehículo**: Cada viaje tiene su propio índice, no hay conflicto
- ✅ **Flexible**: Podemos tener 5 viajes de OVMS y 3 de Morgan simultáneamente
- ✅ **Reutilización**: Cuando se elimina un viaje, su índice se libera para reutilización

**Limitaciones y Soluciones**:
- ⚠️ **Límite de índices**: EMHASS tiene límite (ej: 50 cargas diferibles)
  - **Solución**: Usar pool de índices con reutilización, soporte para 50+ viajes simultáneos es suficiente para la mayoría de usuarios
- ⚠️ **Configuración manual en EMHASS**: El usuario debe añadir N entradas (una por índice potencial)
  - **Solución**: Documentar claramente cuántas entradas necesita (recomendado: 10-15) y proporcionar snippet de configuración
- ⚠️ **Mapeo persistente**: Necesitamos guardar trip_id → índice en storage
  - **Solución**: Usar `Store` de Home Assistant para persistir el mapeo

**Nuevas Tareas para Implementar**:
- [ ] Persistencia del mapeo `trip_id → emhass_index` en `Store`
- [ ] Lógica de asignación de índices (buscar primero libre)
- [ ] Lógica de liberación de índices al eliminar viajes
- [ ] Manejo de error: "No hay índices disponibles"
- [ ] Documentación: Explicar al usuario cuántas entradas EMHASS necesita configurar

---

### Componente 4: Control de Presencia y Notificaciones (Nuevo - Mejorado)

**Archivo**: `presence_monitor.py` (nuevo componente)

```python
import math
from typing import Optional, Tuple

class PresenceMonitor:
    """
    Monitoriza si el vehículo está en casa y enchufado.
    Soporta dos métodos:
    1. Sensor binary_sensor directo (si el usuario lo tiene)
    2. Cálculo por distancia (usando coordenadas de casa y del coche)
    
    Genera notificaciones cuando la carga es necesaria pero no posible.
    """
    
    def __init__(self, hass, vehicle_config: dict):
        self.hass = hass
        self.vehicle_id = vehicle_config[CONF_VEHICLE_NAME]
        
        # Método 1: Sensor directo (preferido si existe)
        self.home_sensor = vehicle_config.get(CONF_HOME_SENSOR)  # binary_sensor
        
        # Método 2: Cálculo por coordenadas
        self.home_coords = vehicle_config.get(CONF_HOME_COORDINATES)  # [lat, lon]
        self.vehicle_coords_sensor = vehicle_config.get(CONF_VEHICLE_COORDINATES_SENSOR)  # sensor with [lat, lon]
        
        # Sensor de enchufado
        self.plugged_sensor = vehicle_config.get(CONF_PLUGGED_SENSOR)  # binary_sensor
    
    async def async_check_charging_readiness(self, trip: Trip):
        """
        Verificar si el vehículo está listo para cargar según el schedule.
        
        Escenarios:
        1. Coche en casa + enchufado → ✅ Todo bien
        2. Coche en casa + NO enchufado → 🔔 Notificar "Conecta el coche"
        3. Coche NO en casa → 🔔 Notificar "El coche no está en casa"
        4. No hay sensores/config → ⚠️ Asumir todo OK (modo ciego)
        """
        # Verificar si está en casa (por sensor o por coordenadas)
        at_home = await self._async_check_home_status()
        
        # Verificar si está enchufado
        is_plugged = True
        if self.plugged_sensor:
            plugged_state = self.hass.states.get(self.plugged_sensor)
            is_plugged = plugged_state and plugged_state.state == "on"
        
        # Lógica de notificaciones
        if not at_home:
            await self._async_notify(
                f"⚠️ Viaje programado: {trip['descripcion']}",
                f"El vehículo {self.vehicle_id} no está en casa. "
                f"Necesita {trip['kwh']} kWh antes de {trip['deadline']}"
            )
            return False
        
        if not is_plugged:
            await self._async_notify(
                f"🔌 Conectar vehículo: {self.vehicle_id}",
                f"Viaje programado: {trip['descripcion']}. "
                f"Necesita {trip['kwh']} kWh antes de {trip['deadline']}"
            )
            return False
        
        return True
    
    async def _async_check_home_status(self) -> bool:
        """
        Verificar si el vehículo está en casa.
        
        Prioridad:
        1. Si hay sensor directo → usar eso
        2. Si hay coordenadas de casa y sensor de coordenadas del coche → calcular distancia
        3. Si no hay nada → asumir True (modo ciego)
        """
        # Método 1: Sensor directo (preferido)
        if self.home_sensor:
            home_state = self.hass.states.get(self.home_sensor)
            return home_state and home_state.state == "on"
        
        # Método 2: Cálculo por coordenadas
        if self.home_coords and self.vehicle_coords_sensor:
            vehicle_state = self.hass.states.get(self.vehicle_coords_sensor)
            if vehicle_state and vehicle_state.state:
                try:
                    # Parsear coordenadas del coche
                    vehicle_coords = self._parse_coordinates(vehicle_state.state)
                    if vehicle_coords:
                        # Calcular distancia a casa
                        distance_km = self._calculate_distance(
                            self.home_coords,
                            vehicle_coords
                        )
                        # Considerar "en casa" si está a menos de 500 metros
                        return distance_km < 0.5
                except Exception as e:
                    _LOGGER.warning(f"Error calculando distancia para {self.vehicle_id}: {e}")
        
        # Método 3: No hay forma de verificar → asumir OK
        return True
    
    def _parse_coordinates(self, state_value: str) -> Optional[Tuple[float, float]]:
        """Parsear coordenadas desde string."""
        # Formatos soportados: "[40.123, -3.456]" o "40.123, -3.456"
        try:
            if state_value.startswith("[") and state_value.endswith("]"):
                state_value = state_value[1:-1]
            lat, lon = map(float, state_value.split(","))
            return (lat, lon)
        except:
            return None
    
    def _calculate_distance(self, coords1: Tuple[float, float],
                           coords2: Tuple[float, float]) -> float:
        """Calcular distancia entre dos puntos (fórmula Haversine)."""
        lat1, lon1 = coords1
        lat2, lon2 = coords2
        
        # Convertir a radianes
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Diferencias
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Fórmula Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radio de la Tierra en km
        r = 6371
        
        return c * r
    
    async def _async_notify(self, title: str, message: str):
        """Enviar notificación persistente."""
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": message,
                "notification_id": f"ev_trip_planner_{self.vehicle_id}"
            }
        )
```

**Configuración en Config Flow**:

**Pregunta 4.3**: ¿Cómo detectamos si el vehículo está en casa? (Opcional pero recomendado)

**Opción A**: Usar sensor existente
- **Selector**: Entity selector filtrado por `binary_sensor.*`
- **Ejemplo**: `binary_sensor.ovms_chispitas_en_casa`
- **Nota**: Si tienes un sensor que indica presencia, úsalo (más preciso)

**Opción B**: Calcular por coordenadas (autodetectar)
- **Sub-pregunta 4.3.1**: ¿Quieres usar autodetección de coordenadas de casa?
  - **Toggle**: Sí/No
  - **Si Sí**: El módulo detectará coordenadas de tu zona de HA
  - **Si No**: Introducir manualmente latitud/longitud

- **Sub-pregunta 4.3.2**: ¿Qué sensor tiene las coordenadas del vehículo?
  - **Selector**: Entity selector filtrado por `sensor.*`
  - **Ejemplo**: `sensor.ovms_chispitas_location`
  - **Help**: Debe devolver formato `[lat, lon]` o `lat, lon`

**Pregunta 4.4**: ¿Qué sensor indica si el vehículo está físicamente enchufado?
- **Selector**: Entity selector filtrado por `binary_sensor.*`
- **Ejemplo**: `binary_sensor.cargador_ovms_conectado`
- **Opcional**: Si no se configura, solo se verifica "en casa"

**Nota**: Si no configuras ni sensor de casa ni coordenadas, el módulo asumirá que el vehículo siempre está disponible para cargar (modo ciego).

---

## 📍 Nota sobre Configuración de "En Casa"

La detección de si el vehículo está en casa es **opcional pero altamente recomendada**. Sin esta configuración, el módulo no podrá notificarte si el coche necesita cargar pero no está disponible.

### Por qué es un "extra"

- **No todos los usuarios tienen sensor de presencia**: Algunas integraciones de vehículos no exponen un `binary_sensor.{vehicle}_en_casa`
- **Cálculo por coordenadas requiere setup**: Necesitamos saber dónde está "casa" y el coche debe reportar su ubicación
- **El módulo funciona sin esto**: Pero con menos inteligencia (no notificaciones de "coche no está en casa")

### Cómo funciona la autodetección

**Coordenadas de Casa**:
```python
# Al configurar el vehículo, podemos:
# 1. Autodetectar de la configuración de HA (zone.home)
home_coords = hass.states.get("zone.home").attributes["latitude"], hass.states.get("zone.home").attributes["longitude"]

# 2. Pedir al usuario que introduzca manualmente
# 3. Usar la ubicación del dispositivo móvil del usuario (si da permiso)
```

**Coordenadas del Coche**:
- Depende de la integración: OVMS, Renault, Tesla, etc.
- Algunas integraciones tienen `sensor.{vehicle}_location` con formato `[lat, lon]`
- Otras requieren llamada a API externa (más complejo)

### Guardado en Configuración

Las coordenadas de casa se guardan **una vez** en la config entry del vehículo:

```json
{
  "vehicle_name": "chispitas",
  "home_detection_method": "coordinates",  // "sensor" o "coordinates"
  "home_coordinates": [40.1234, -3.5678],  // solo si método = coordinates
  "vehicle_coordinates_sensor": "sensor.ovms_chispitas_location",
  // ... resto de config
}
```

### Recomendación para el Usuario

En el config flow, podemos mostrar:

> **"Detección de presencia (opcional)"**
>
> Para recibir notificaciones cuando tu coche necesite cargar pero no esté en casa, configura una de estas opciones:
>
> - **Opción 1 (recomendada si disponible)**: Usa un sensor que indique si el coche está en casa
> - **Opción 2**: Usa coordenadas (autodetectadas de tu zona "home" o manuales) + sensor de ubicación del coche
>
> *Si no configuras nada, el módulo asumirá que el coche siempre está disponible para cargar.*

### ⚠️ Importancia Crítica: Prevenir Activación Fuera de Casa

**El propósito principal de detectar "en casa" es EVITAR que el planificador active la carga cuando el coche NO está en casa.**

**Escenarios de riesgo sin detección de presencia**:

1. **Coche en centro comercial**:
   - El planificador genera schedule: "cargar ahora" (porque la luz es barata)
   - Nuestro módulo activa `switch.ovms_carga`
   - **RESULTADO**: ⚠️ Estamos intentando cargar un coche que está a 20 km de casa

2. **Coche en electrolinera de viaje**:
   - El planificador detecta que el coche necesita 20 kWh para mañana
   - Nuestro módulo activa la carga
   - **RESULTADO**: ⚠️ No hay ningún cargador conectado al switch, acción inútil y potencialmente peligrosa

3. **Coche en casa de un amigo**:
   - Similar a los casos anteriores, activaríamos un switch que no está conectado a nada

**Cómo lo prevenimos**:

```python
# En schedule_monitor.py
async def _async_execute_schedule(self, vehicle_id: str, action: str):
    """
    Ejecutar acción de carga solo si el vehículo está en casa.
    """
    # Verificar presencia ANTES de activar/desactivar
    presence_monitor = self.presence_monitors.get(vehicle_id)
    
    if not presence_monitor:
        _LOGGER.warning(f"No hay monitor de presencia para {vehicle_id}, asumiendo que está en casa")
        # Continuar con la acción (modo ciego)
        await self._async_execute_control(vehicle_id, action)
        return
    
    # Verificar si está en casa
    is_at_home = await presence_monitor._async_check_home_status()
    
    if not is_at_home:
        _LOGGER.info(f"Vehículo {vehicle_id} no está en casa, ignorando acción: {action}")
        # NO ejecutar la acción, el coche no está aquí
        await self._async_notify_vehicle_not_home(vehicle_id)
        return
    
    # Verificar si está enchufado
    is_plugged = await presence_monitor._async_check_plugged_status()
    
    if not is_plugged:
        _LOGGER.info(f"Vehículo {vehicle_id} no está enchufado, ignorando acción: {action}")
        # NO ejecutar la acción, no hay cargador conectado
        await self._async_notify_vehicle_not_plugged(vehicle_id)
        return
    
    # Si llegamos aquí: coche en casa + enchufado → Ejecutar acción
    await self._async_execute_control(vehicle_id, action)
```

**Beneficios de esta protección**:

- ✅ **Seguridad**: Nunca activamos cargadores que no están conectados al coche
- ✅ **Eficiencia**: No ejecutamos acciones inútiles que no tendrán efecto
- ✅ **Ahorro**: Evitamos "falsos positivos" en el log de automatizaciones
- ✅ **Flexibilidad**: El usuario puede llevarse el coche sin preocuparse de desactivar el planificador

**Nota**: Si el usuario NO configura detección de presencia, el módulo funciona en **modo ciego** (asume que el coche siempre está en casa). Esto es útil para usuarios avanzados que gestionan la presencia manualmente o que siempre dejan el coche en casa.

---

## 🚗 Integraciones Específicas: OVMS y Renault

### OVMS (Nissan Leaf - "Chispitas")

**Sensores Requeridos**:
- `sensor.ovms_chispitas_soc` (State of Charge %)
- `binary_sensor.ovms_chispitas_en_casa` (presencia)
- `switch.ovms_chispitas_carga` (control de carga)
- Opcional: `binary_sensor.ovms_chispitas_enchufado`

**Configuración de Control**:
```yaml
# En config entry
vehicle_integration: "ovms"
charge_control_entity: "switch.ovms_chispitas_carga"
home_sensor: "binary_sensor.ovms_chispitas_en_casa"
plugged_sensor: "binary_sensor.ovms_chispitas_enchufado"
```

### Renault (Dacia Spring - "Morgan")

**Sensores Requeridos**:
- `sensor.morgan_battery_level` (SOC %)
- `binary_sensor.morgan_en_casa` (presencia)
- `switch.morgan_cargador` (control de carga)
- Opcional: `sensor.morgan_cargador_conectado`

**Configuración de Control**:
```yaml
# En config entry
vehicle_integration: "renault"
charge_control_entity: "switch.morgan_cargador"
home_sensor: "binary_sensor.morgan_en_casa"
plugged_sensor: "sensor.morgan_cargador_conectado"
```

### Estrategia de Control: SwitchEntityStrategy

```python
class SwitchEntityStrategy:
    """Estrategia de control usando switch entity."""
    
    def __init__(self, hass, switch_entity_id: str):
        self.hass = hass
        self.switch_entity_id = switch_entity_id
    
    async def async_activate(self):
        """Activar carga."""
        await self.hass.services.async_call(
            "switch", "turn_on", {"entity_id": self.switch_entity_id}
        )
    
    async def async_deactivate(self):
        """Desactivar carga."""
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self.switch_entity_id}
        )
    
    async def async_get_status(self) -> bool:
        """Obtener estado actual."""
        state = self.hass.states.get(self.switch_entity_id)
        return state and state.state == "on"
```

---

## 📊 Flujo de Datos Completo (Ejemplo)

### Escenario: Viaje Lunes 9:00 AM, 24 km, 3.6 kWh

**Día Domingo 18:00**:
1. **Trip Manager**: Expande viajes para próximos 3 días (horizonte EMHASS)
2. **EMHASS Adapter**: Crea entidad `deferrable_load.ovms_lunes_trabajo`
   - `power`: 3.6 kW (asumiendo carga a 3.6 kW)
   - `duration`: 1 hora
   - `deadline`: 2025-12-09T09:00:00
   - `priority`: 5 (alta - trabajo)
3. **EMHASS**: Ejecuta optimización day-ahead
4. **Schedule Monitor**: Lee `sensor.emhass_deferrable0_schedule`
   - Programa carga de 02:00-03:00 (hora barata)
5. **Presence Monitor**: Verifica a las 02:00
   - ¿Coche en casa? ✅
   - ¿Enchufado? ❌
   - **Acción**: Notificación persistente + log
6. **Usuario**: Recibe notificación, conecta el coche a las 02:15
7. **Schedule Monitor**: A las 02:15 detecta conexión
   - **Acción**: Activa `switch.ovms_chispitas_carga`
8. **Coche**: Carga durante 1 hora, completa 3.6 kWh
9. **Schedule Monitor**: A las 03:15 desactiva carga

---

## 🔔 Notificaciones y Alertas

### Tipos de Notificaciones

1. **Carga Requerida pero No Enchufado** (Prioridad: Alta)
   - **Título**: "🔌 Conectar vehículo: {vehicle}"
   - **Mensaje**: "Viaje '{description}' necesita {kwh} kWh antes de {deadline}"
   - **Acción**: Sonido + persistent_notification

2. **Coche No en Casa** (Prioridad: Media)
   - **Título**: "⚠️ Viaje programado: {description}"
   - **Mensaje**: "El vehículo {vehicle} no está en casa. Necesita {kwh} kWh"
   - **Acción**: Persistent notification (no sonido)

3. **Carga Completada** (Prioridad: Baja)
   - **Título**: "✅ Carga completada: {vehicle}"
   - **Mensaje**: "Se han cargado {kwh} kWh para el viaje '{description}'"
   - **Acción**: Notification que se auto-elimina en 1 hora

4. **Planificación Generada** (Prioridad: Info)
   - **Título**: "📊 Plan de carga generado"
   - **Mensaje**: "EMHASS ha programado {hours}h de carga para {vehicle}"
   - **Acción**: Log + opcional notification

### Configuración de Notificaciones

**Pregunta 6.1**: ¿Quieres recibir notificaciones cuando el coche necesite cargar?
- **Toggle**: Sí/No
- **Default**: Sí

**Pregunta 6.2**: ¿Quieres sonido en las notificaciones críticas?
- **Toggle**: Sí/No
- **Default**: Sí

**Pregunta 6.3**: ¿Qué dispositivos deben recibir notificaciones?
- **Selector**: Dispositivos móviles con app HA
- **Múltiple**: true

---

## 🧪 Plan de Testing para OVMS y Renault

### Test Suite: OVMS Integration

```python
# tests/test_ovms_integration.py

async def test_ovms_complete_flow(hass):
    """Test flujo completo con OVMS."""
    
    # 1. Configurar vehículo OVMS
    config = {
        CONF_VEHICLE_NAME: "chispitas",
        CONF_VEHICLE_INTEGRATION: "ovms",
        CONF_CHARGE_CONTROL_ENTITY: "switch.ovms_chispitas_carga",
        CONF_HOME_SENSOR: "binary_sensor.ovms_chispitas_en_casa",
        CONF_PLUGGED_SENSOR: "binary_sensor.ovms_chispitas_enchufado",
        CONF_PLANNING_HORIZON: 7,
        CONF_DEFERRABLE_COUNT: 2,
    }
    
    # 2. Crear viaje recurrente
    await hass.services.async_call(
        DOMAIN, "add_recurring_trip",
        {
            "vehicle_id": "chispitas",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
            "descripcion": "Trabajo"
        }
    )
    
    # 3. Verificar que se creó entidad deferrable_load
    state = hass.states.get("deferrable_load.chispitas_lunes_trabajo")
    assert state is not None
    assert state.attributes["power"] == 3.6
    assert state.attributes["duration"] == 1.0
    
    # 4. Simular schedule de EMHASS
    hass.states.async_set("sensor.emhass_deferrable0_schedule", "02:00-03:00")
    
    # 5. Verificar que se activó el switch
    await asyncio.sleep(1)  # Esperar a que el monitor actúe
    switch_state = hass.states.get("switch.ovms_chispitas_carga")
    assert switch_state.state == "on"
```

### Test Suite: Renault Integration

```python
# tests/test_renault_integration.py

async def test_renault_presence_detection(hass):
    """Test detección de presencia para Renault."""
    
    # Configurar vehículo Renault
    config = {
        CONF_VEHICLE_NAME: "morgan",
        CONF_VEHICLE_INTEGRATION: "renault",
        CONF_CHARGE_CONTROL_ENTITY: "switch.morgan_cargador",
        CONF_HOME_SENSOR: "binary_sensor.morgan_en_casa",
        CONF_PLUGGED_SENSOR: "sensor.morgan_cargador_conectado",
    }
    
    # Simular: coche en casa pero NO enchufado
    hass.states.async_set("binary_sensor.morgan_en_casa", "on")
    hass.states.async_set("sensor.morgan_cargador_conectado", "0")  # No conectado
    
    # Crear viaje para mañana
    await hass.services.async_call(
        DOMAIN, "add_punctual_trip",
        {
            "vehicle_id": "morgan",
            "datetime": (datetime.now() + timedelta(days=1)).isoformat(),
            "km": 50,
            "kwh": 7.5,
            "descripcion": "Viaje a Valencia"
        }
    )
    
    # Verificar que se generó notificación
    notifications = hass.states.async_all("persistent_notification")
    assert any("Conectar vehículo: morgan" in n.attributes.get("message", "") 
               for n in notifications)
```

---

## 📦 Configuración de Ejemplo Completa

### Config Entry para OVMS

```json
{
  "entry_id": "ovms_chispitas",
  "vehicle_name": "chispitas",
  "vehicle_integration": "ovms",
  "soc_sensor": "sensor.ovms_chispitas_soc",
  "battery_capacity_kwh": 40,
  "charging_power_kw": 7.4,
  "kwh_per_km": 0.15,
  "safety_margin_percent": 10,
  "control_type": "switch",
  "charge_control_entity": "switch.ovms_chispitas_carga",
  "home_sensor": "binary_sensor.ovms_chispitas_en_casa",
  "plugged_sensor": "binary_sensor.ovms_chispitas_enchufado",
  "planning_horizon_days": 7,
  "planning_sensor_entity": "sensor.emhass_planning_horizon",
  "deferrable_load_count": 2,
  "deferrable_load_pattern": "deferrable_load.{vehicle}_{trip_id}",
  "notifications_enabled": true,
  "notification_devices": ["mobile_app_iphone_malka"]
}
```

### Config Entry para Renault

```json
{
  "entry_id": "renault_morgan",
  "vehicle_name": "morgan",
  "vehicle_integration": "renault",
  "soc_sensor": "sensor.morgan_battery_level",
  "battery_capacity_kwh": 27.4,
  "charging_power_kw": 7.4,
  "kwh_per_km": 0.13,
  "safety_margin_percent": 10,
  "control_type": "switch",
  "charge_control_entity": "switch.morgan_cargador",
  "home_sensor": "binary_sensor.morgan_en_casa",
  "plugged_sensor": "sensor.morgan_cargador_conectado",
  "planning_horizon_days": 7,
  "deferrable_load_count": 2,
  "deferrable_load_pattern": "deferrable_load.{vehicle}_{desc}",
  "notifications_enabled": true,
  "notification_devices": ["mobile_app_iphone_malka", "mobile_app_ipad"]
}
```

---

## 🚀 Roadmap de Implementación Actualizado

### Semana 1: Configuración y Expansión
- **Día 1-2**: Extender `config_flow.py` con pasos 4 y 5
- **Día 3-4**: Modificar `trip_manager.py` para horizonte agnóstico
- **Día 5**: Tests unitarios para expansión temporal

### Semana 2: EMHASS Adapter
- **Día 1-2**: Crear `emhass_adapter.py` con patrón configurable
- **Día 3-4**: Integrar con `sensor.py` para publicar entidades
- **Día 5**: Tests unitarios para creación de deferrable loads

### Semana 3: Vehicle Controller y Presence Monitor
- **Día 1-2**: Crear `vehicle_controller.py` con estrategias
- **Día 3-4**: Crear `presence_monitor.py` con notificaciones
- **Día 5**: Tests de integración OVMS y Renault

### Semana 4: Schedule Monitor
- **Día 1-2**: Crear `schedule_monitor.py` con mapeo dinámico
- **Día 3-4**: Integrar todos los componentes
- **Día 5**: Tests E2E con mocks de EMHASS

### Semana 5: Testing en Producción de Prueba
- **Día 1-2**: Deploy en entorno de prueba con OVMS real
- **Día 3-4**: Monitoreo y ajustes
- **Día 5**: Documentación y preparación para release

---

## ✅ Checklist de Validación

Antes de empezar implementación, validar:

- [ ] **Configuración de OVMS**: Todos los sensores requeridos existen en producción
- [ ] **Configuración de Renault**: Todos los sensores requeridos existen en producción
- [ ] **EMHASS**: Versión soporta configuración de deferrable loads por nombre
- [ ] **Notificaciones**: Dispositivos móviles configurados en HA
- [ ] **Patrón de Nombres**: Decidir patrón final (recomiendo `deferrable_load.{vehicle}_{desc}`)

---

## 🎯 Próximos Pasos Concretos

1. **Validar sensores OVMS**: Ejecutar `get_live_context.py` para verificar que existen:
   - `sensor.ovms_chispitas_soc`
   - `binary_sensor.ovms_chispitas_en_casa`
   - `switch.ovms_chispitas_carga`

2. **Validar sensores Renault**: Verificar que existen:
   - `sensor.morgan_battery_level`
   - `binary_sensor.morgan_en_casa`
   - `switch.morgan_cargador`

3. **Decidir patrón de nombres**: ¿Usamos `deferrable_load.{vehicle}_{trip_id}` o `deferrable_load.{vehicle}_{desc}`?

4. **Crear issue en GitHub**: Para Milestone 3A con especificaciones técnicas

---

## 🤔 Preguntas Abiertas para Decisión

1. **Patrón de nombres**: ¿Usar `trip_id` (técnico) o `desc` (legible) en entity_id?
   - `deferrable_load.ovms_rec_lun_abc123` vs `deferrable_load.ovms_lunes_trabajo`

2. **Horizonte de planificación**: ¿Deberíamos limitar a 7 días máximo por ahora?
   - Pros: Más simple, menos entidades
   - Cons: No soporta planificación mensual futura

3. **Notificaciones**: ¿Usar `persistent_notification` o `notify.mobile_app`?
   - `persistent` queda en UI pero no push
   - `mobile_app` push pero puede ser spam

4. **Testing**: ¿Tienes un entorno de prueba separado o probamos directo en producción con cuidado?

---

**Recomendación**: Empezar con Milestone 3A (Configuración y Expansión) y validar los sensores reales de OVMS y Renault antes de escribir código de control.
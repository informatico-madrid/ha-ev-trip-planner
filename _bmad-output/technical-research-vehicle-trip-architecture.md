# Análisis Arquitectónico: HA EV Trip Planner

> Fecha: 2026-04-18 | Analista: BMad Technical Research | Proyecto: ha-ev-trip-planner

## Resumen Ejecutivo

El proyecto presenta un **problema arquitectónico fundamental** relacionado con la gestión de identidad de vehículos y la coordinación entre almacenamiento, tests y coordinación de entidades. Este problema se manifiesta como:

- **Síntoma**: Arreglar tests estropea persistencia, arreglar persistencia estropea coordinación
- **Causa raíz**: Múltiples mecanismos de almacenamiento con normalización inconsistente de `vehicle_id`

---

## 1. Arquitectura Actual del Sistema

### 1.1 Flujo de Datos

```
ConfigEntry (vehicle_name) 
    → TripManager (vehicle_id normalizado)
    → Storage (storage_key = f"ev_trip_planner_{vehicle_id}")
    → Coordinator (datos para sensores)
```

### 1.2 Componentes Principales

| Componente | Responsabilidad | Problemas Identificados |
|------------|-----------------|--------------------------|
| `config_flow.py` | Crear ConfigEntry con `vehicle_name` | Normalización solo en coordinator, no en storage |
| `trip_manager.py` | CRUD de trips, almacenamiento | Fallback dual (Store + YAML) con lógica duplicada |
| `yaml_trip_storage.py` | Persistencia alternativa | No usa protocolos consistente con TripManager |
| `coordinator.py` | Sincronizar datos para sensores | Dependiente de normalización correcta |
| `tests/conftest.py` | Fixtures para tests | Mock store incompleto para casos de persistencia |

---

## 2. Problemas Arquitectónicos Identificados

### 2.1 Normalización Inconsistente de vehicle_id

**Problema Central**: El `vehicle_id` se normaliza en algunos lugares pero no en otros.

```python
# coordinator.py (líneas 72-76) - normaliza correctamente
self._vehicle_id = (
    self._entry.data.get(CONF_VEHICLE_NAME, "unknown")
    .lower()
    .replace(" ", "_")
)

# trip_manager.py (línea 238) - usa vehicle_id directamente
storage_key = f"{DOMAIN}_{self.vehicle_id}"
```

**Síntoma**: Un vehículo creado como "Test Vehicle" genera:
- ConfigEntry con `vehicle_name = "Test Vehicle"`
- TripManager con `vehicle_id = "test_vehicle"` (normalizado)
- Storage con key `"ev_trip_planner_test_vehicle"`

**Pero**: Si algún código pasa `vehicle_id` sin normalizar (ej: "Test Vehicle"), el storage key sería diferente y los datos no se encontrarían.

### 2.2 Fallback Dual de Almacenamiento

El `TripManager` tiene lógica duplicada para cargar datos:

```python
# trip_manager.py líneas 231-245 - primer mecanismo
if self._storage is not None:
    stored_data = await self._storage.async_load()
else:
    # Fallback a Store directo
    storage_key = f"{DOMAIN}_{self.vehicle_id}"
    store = ha_storage.Store(...)

# trip_manager.py líneas 335-383 - fallback YAML (duplicado)
async def _load_trips_yaml(self, storage_key: str) -> None:
    # Misma lógica pero en archivo separado
```

**Problema**: Cualquier fix en un mecanismo debe replicarse en el otro, creando inconsistencias.

### 2.3 Inyección de Dependencias Incompleta

El `TripManager.__init__` acepta `storage` como parámetro opcional:

```python
def __init__(self, ..., storage: Optional[TripStorageProtocol] = None, ...):
    self._storage: Optional[TripStorageProtocol] = storage
```

**Problema**: Los tests que NO inyectan storage usan el fallback directo a HA Store, que requiere mock específico en `conftest.py`. Pero los tests que SÍ inyectan storage usan `YamlTripStorage` que tiene una implementación diferente.

### 2.4 Mock Store Incompleto

El fixture `mock_store` en `conftest.py` (líneas 220-243) tiene una implementación que puede no reflejar el comportamiento real:

```python
@pytest.fixture
def mock_store():
    store = MagicMock()
    store._storage = {}
    
    async def _async_load():
        return store._storage.get("data", None)  # ⚠️ key inconsistente
    
    async def _async_save(data):
        store._storage["data"] = data  # ⚠️ storage different behavior
```

**Problema**: El store real de HA retorna datos envueltos en `"data"`, pero este mock no lo hace consistentemente.

### 2.5 Relación Vehicle↔Trip en Tests

Los tests usan fixtures diferentes para crear TripManager:

```python
# tests/test_trip_crud.py línea 80-82
def trip_manager(mock_hass_storage, vehicle_id):
    return TripManager(mock_hass_storage, vehicle_id)  # ⚠️ Sin entry_id

# tests/test_trip_manager.py línea 77-80  
def trip_manager_no_storage(mock_hass_no_storage, vehicle_id):
    return TripManager(mock_hass_no_storage, vehicle_id)  # ⚠️ Sin storage
```

**Problema**: Falta `entry_id` en muchos fixtures, lo que significa que `publish_deferrable_loads()` no puede refrescar el coordinator correctamente (líneas 184-197 en trip_manager.py).

---

## 3. Modelo de Datos

### 3.1 Estructura de Trip

```python
# Trip punctual
{
    "id": "pun_20251119_abc123",
    "tipo": "puntual",
    "datetime": "2025-11-19T15:00:00",
    "km": 110,
    "kwh": 16.5,
    "descripcion": "Viaje a Toledo",
    "estado": "pendiente",  # ⚠️ Estado agregado en alguns places
    "creado": "2025-11-18T10:30:00"
}

# Trip recurrente
{
    "id": "rec_lun_12345678",
    "tipo": "recurrente",
    "dia_semana": "lunes",
    "hora": "09:00",
    "km": 24,
    "kwh": 3.6,
    "descripcion": "Trabajo",
    "activo": true,
    "creado": "2025-11-18T10:00:00"
}
```

### 3.2 Storage Data Structure

```python
# En .storage/ev_trip_planner_{vehicle_id}
{
    "trips": {},
    "recurring_trips": {...},
    "punctual_trips": {...},
    "last_update": "2025-11-18T10:30:00"
}
```

---

## 4. Interacciones Problemáticas

### 4.1 Test → Persistencia

Cuando un test arregla el mock del store para que funcione, el store real puede comportarse diferente, causando que la persistencia real falle.

### 4.2 Persistencia → Coordinación

Cuando la persistencia funciona pero no se normaliza correctamente el vehicle_id, el coordinator puede leer datos de un storage key incorrecto, causando que los sensores muestren datos antiguos o vacíos.

### 4.3 Coordinación → EMHASS

El adapter EMHASS depende del vehicle_id normalizado para crear sensores. Si el vehicle_id no está normalizado, los sensores EMHASS pueden quedar huérfanos.

---

## 5. Causa Raíz

**Normalización de identidad no centralizada**: No hay un lugar único donde se normalice el `vehicle_id` y se use consistentemente en todo el código.

- `config_flow.py` crea entries con `vehicle_name` original
- `coordinator.py` normaliza para sí mismo
- `trip_manager.py` espera normalización pero no la garantiza
- `yaml_trip_storage.py` usa `_vehicle_id` directamente
- Los tests usan vehicle_ids sin normalizar en muchos casos

---

## 6. Recomendación de Solución

### Fase 1: Centralizar Normalización

Crear una función centralizada para normalizar vehicle_id:

```python
# custom_components/ev_trip_planner/utils.py (agregar)
def normalize_vehicle_id(vehicle_name: str) -> str:
    """Normalize vehicle name to vehicle_id format."""
    return vehicle_name.lower().replace(" ", "_")
```

Y usar esta función en:
1. `config_flow.py` - al guardar entry.data
2. `trip_manager.py` - en __init__ ystorage key
3. `yaml_trip_storage.py` - en __init__
4. `coordinator.py` - ya lo hace, mantener

### Fase 2: Unificar Mecanismo de Storage

Eliminar el fallback dual y usar un único mecanismo:
- En producción: `YamlTripStorage` (implementación actual)
- En tests: Mock que implemente `TripStorageProtocol` correctamente

### Fase 3: Asegurar entry_id en Todos los Tests

Todos los fixtures de TripManager deben incluir `entry_id` para que `publish_deferrable_loads()` pueda llamar al coordinator.

---

## 7. Siguiente Paso Recomendado

Usar el agente `bmad-review-adversarial-general` para una revisión línea por línea del código, enfocándose en:

1. Todas las usages de `vehicle_id` sin normalizar
2. Todos los lugares donde se crea storage_key
3. Fixture de mock_store en conftest.py

**Comando**: `/bmad-review-adversarial-general` (luego indicar el path a los archivos principales)

---

## Archivos Críticos para Revisión

| Archivo | Líneas | Razón |
|---------|--------|-------|
| `trip_manager.py` | 91-127 | Constructor e inyección de storage |
| `trip_manager.py` | 231-245 | Fallback storage |
| `trip_manager.py` | 184-197 | publish_deferrable_loads con coordinator |
| `yaml_trip_storage.py` | 28-68 | Implementación storage alternativa |
| `coordinator.py` | 72-86 | Normalización vehicle_id |
| `tests/conftest.py` | 220-243 | Mock store |
| `tests/conftest.py` | 86-197 | Fixture hass |
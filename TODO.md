# TODO - EV Trip Planner

## Prioridad Alta
### 8. Normalización de días de la semana (case-insensitive, sin tildes)
**Issue**: La validación actual es case-sensitive ('miercoles' vs 'Miércoles') y no maneja tildes, causando duplicados por inconsistencias de formato.

**Solución**:
- Implementar sanitización de entrada que convierta cualquier variante (Miércoles, Miercoles, miercoles, MIÉRCOLES) al valor canónico sin tildes y en minúsculas
- Usar `unidecode` o similar para eliminar tildes
- Actualizar `_DAY_MAP` para usar valores normalizados como claves
- Añadir helper `_normalize_day_name(day_str: str) -> str`

**Test primero**:
```python
async def test_add_recurring_trip_normalizes_day_variants():
    """Test que cualquier variante de día se normaliza correctamente."""
    # RED phase - probar: Miércoles, Miercoles, miercoles, MIÉRCOLES
```

**Archivos a modificar**:
- `custom_components/ev_trip_planner/trip_manager.py` (método `async_add_recurring_trip`)
- `custom_components/ev_trip_planner/trip_manager.py` (añadir helper `_normalize_day_name`)

---

### 9. Eliminación de redundancia km/kWh y cálculo automático
**Issue**: El campo kWh es redundante y genera riesgo de datos contradictorios (ej: 1000 km con 1 kWh). El usuario no debería calcular manualmente el consumo.

**Solución**:
- **Fase 1**: Refactorizar para solicitar únicamente:
  - Origen-destino (direcciones o coordenadas)
  - Hora de salida
  - Modelo de vehículo (para obtener eficiencia)
- **Fase 2**: Implementar cálculo automático:
  - Distancia total (via geocoding API: Google Maps, OpenStreetMap)
  - Consumo kWh estimado: `kwh = distance_km * vehicle_efficiency_kwh_per_km`
  - Tiempo de viaje estimado
- **Fase 3**: Mantener compatibilidad hacia atrás (campos opcionales)

**Test primero**:
```python
async def test_add_trip_with_origin_destination_calculates_kwh():
    """Test que origen-destino calcula kWh automáticamente."""
    # RED phase
```

**Archivos a modificar**:
- `custom_components/ev_trip_planner/trip_manager.py` (nuevos parámetros)
- `custom_components/ev_trip_planner/services.yaml` (nuevo schema)
- `custom_components/ev_trip_planner/config_flow.py` (configurar API key)

---

### 1. Mejorar feedback de errores en servicios
**Issue**: Si usas `vehicle_id` incorrecto, el servicio responde "OK" pero no hace nada. No hay feedback de error.

**Solución**: 
- Validar que `vehicle_id` exista en `hass.data[DOMAIN]`
- Lanzar `ServiceValidationError` con mensaje claro si no existe
- Ejemplo: "Vehicle 'chispitas Test' not found. Available vehicles: ['Chispitas Test']"

**Test primero**: 
```python
async def test_service_invalid_vehicle_id_raises_error():
    """Test que servicio con vehicle_id inválido lanza error."""
    # RED phase
```

---

### 2. Implementar DataUpdateCoordinator para sensores reactivos
**Issue**: Los sensores usan polling (`should_poll = True`) y solo se actualizan cada 30s. No son reactivos a cambios del TripManager.

**Solución**:
- Crear `TripPlannerCoordinator(DataUpdateCoordinator)` en `__init__.py`
- Envolver `TripManager` y hacer `async_request_refresh()` después de cada operación CRUD
- Sensores se suscriben al coordinator (`CoordinatorEntity`)
- Actualización instantánea sin polling

**Test primero**:
```python
async def test_coordinator_refresh_after_add_trip():
    """Test que coordinator actualiza después de añadir viaje."""
    # RED phase
```

**Referencias**:
- [DataUpdateCoordinator docs](https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities)
- Patrón usado por: Renault, Tesla, etc.

---

### 3. Normalizar vehicle_id (slug)
**Issue**: `vehicle_id` con espacios y mayúsculas causa confusión ("Chispitas Test" vs "chispitas Test")

**Solución**:
- En `config_flow.py`, normalizar a slug: `vehicle_name.lower().replace(" ", "_")`
- Guardar ambos: `vehicle_name` (display) y `vehicle_id` (slug)
- Usar slug internamente, name para UI

**Test primero**:
```python
async def test_config_flow_normalizes_vehicle_id():
    """Test que vehicle_id se normaliza a slug."""
    # RED phase
```

---

## Prioridad Media

### 4. Refactorizar tests antiguos a Storage API
**Issue**: 16 tests fallan porque usan mocks de `input_text` (deprecated)

**Solución**:
- Actualizar `test_trip_manager_core.py` para mockear `Store` en lugar de `input_text`
- Reutilizar fixtures de `test_trip_manager_storage.py`
- Mantener cobertura >80%

**O deprecar**: Marcar tests antiguos como `@pytest.mark.skip` y depender de los nuevos Storage tests.

---

### 5. Añadir validación de sensores OVMS en config_flow
**Issue**: Usuario puede configurar sensor SOC que no existe → errores en runtime

**Solución**:
- En `async_step_sensors`, validar que `soc_sensor` existe en `hass.states`
- Mostrar error en UI si no existe
- Sugerir sensores disponibles con `sensor.*.soc` pattern

---

### 6. Implementar import/export de viajes
**Issue**: No hay forma de hacer backup/restore de viajes

**Solución**:
- Servicio `ev_trip_planner.export_trips` → devuelve YAML
- Servicio `ev_trip_planner.import_trips` → desde YAML
- Útil para migración entre vehículos

---

### 7. Autocrear panel al configurar (mejora UX)
**Issue**: El usuario final no debería crear el panel Lovelace manualmente; al configurar la integración debería aparecer un panel con los viajes desde el principio.

**Solución**:
- Añadir opción en `config_flow`/`options_flow`: "Crear panel automáticamente" (por defecto activada).
- Idempotente: si el panel ya existe, no duplicar.
- Detectar modo de Lovelace:
    - `storage`: usar la API interna de Lovelace para crear dashboard/view y tarjetas.
    - `yaml`: generar `lovelace-<slug_vehiculo>-trip-planner.yaml` y notificar al usuario (persistent_notification) con un botón/servicio para que confirme añadirlo (no editar `configuration.yaml` automáticamente).
- Exponer servicio manual `ev_trip_planner.create_dashboard` para recrear/forzar la creación del panel.
- Al eliminar la integración: ocultar/eliminar el panel (si fue creado automáticamente) o preguntar al usuario.

**Test primero**:
```python
async def test_create_dashboard_service_idempotent(hass):
        """Crea el panel una vez y al repetir no duplica."""
        # RED phase
```

**Notas**:
- Plantillas de tarjetas reutilizan las entidades: `sensor.<slug>_trips_list`, `sensor.<slug>_recurring_trips_count`, `sensor.<slug>_punctual_trips_count`.
- Usar slug de `vehicle_id` para rutas/filenames.

---

## Prioridad Baja

### 7. Dashboard interactivo con custom card
**Issue**: Dashboard actual es estático (Markdown + entities)

**Solución**:
- Crear custom Lovelace card con grid visual de semana
- Click en celda → editar viaje inline
- Drag & drop para cambiar horarios

**Requiere**: Frontend (JS/TypeScript), fuera de scope MVP

---

### 8. Tests de integración E2E
**Issue**: Tests actuales son unitarios; no cubren integración completa HA

**Solución**:
- Tests con `hass` real (no mock)
- Verificar flujo completo: config_flow → services → sensors
- Usar `pytest-homeassistant-custom-component` fixtures

---

## Completado ✅

- ✅ Migrar de `input_text` a `Storage API` (18-nov-2025)
- ✅ Crear tests TDD para Storage (`test_trip_manager_storage.py`)
- ✅ Compartir TripManager instance entre servicios y sensores via `hass.data`

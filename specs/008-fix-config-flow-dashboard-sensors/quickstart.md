# Quickstart: Implementación Fix Config Flow Dashboard Sensors

## Resumen de Cambios

Esta feature corrige 4 problemas críticos en el componente EV Trip Planner:

1. Eliminar selector de tipo de vehículo irrelevante
2. Traducir charging_status_sensor al español
3. Corregir importación de dashboard (sobrescribir existente)
4. Solucionar sensores no actualizados

---

## Archivos a Modificar

### 1. config_flow.py

**Cambio**: Eliminar selector vehicle_type

```python
# ANTES (líneas 50-52):
vol.Required("vehicle_type", default=VEHICLE_TYPE_EV): vol.In(
    [VEHICLE_TYPE_EV, VEHICLE_TYPE_PHEV]
),

# DESPUÉS: Eliminar completamente
```

### 2. strings.json

**Cambio**: Agregar traducción para charging_status_sensor

```json
{
  "config": {
    "step": {
      "presence": {
        "data": {
          "charging_status_sensor": "Sensor de Estado de Carga"
        },
        "data_description": {
          "charging_status_sensor": "Sensor binario que indica si el vehículo está cargando (on = cargando). Busca sensores con 'charging', 'charge' o 'plugged' en el nombre. Ejemplo: binary_sensor.ovms_chispitas_charging"
        }
      }
    }
  }
}
```

### 3. __init__.py

**Cambio 1**: Modificar `import_dashboard` para sobrescribir

```python
async def import_dashboard(
    hass: HomeAssistant,
    vehicle_id: str,
    vehicle_name: str,
    use_charts: bool = False,
) -> bool:
    """Import a Lovelace dashboard for the vehicle."""
    # ... existing code ...
    
    # ADD: Check if dashboard exists and overwrite
    existing_dashboards = await hass.storage.async_read("lovelace")
    if existing_dashboards and "data" in existing_dashboards:
        views = existing_dashboards["data"].get("views", [])
        # Find and update existing dashboard
        for i, view in enumerate(views):
            if view.get("path") == f"ev-trip-planner-{vehicle_id}":
                views[i] = new_view  # Replace
                updated = True
                break
    
    # Always save at the end
```

**Cambio 2**: Verificar que servicios actualizan coordinator

```python
# En handle_add_punctual y handle_add_recurring:
async def handle_add_punctual(call: ServiceCall) -> None:
    """Handle adding a punctual trip."""
    data = call.data
    vehicle_id = data["vehicle_id"]
    mgr = _get_manager(hass, vehicle_id)
    await mgr.async_add_punctual_trip(...)
    
    # CRITICAL: Refresh coordinator
    coordinator = _get_coordinator(hass, vehicle_id)
    if coordinator:
        await coordinator.async_refresh_trips()
```

### 4. sensor.py

**Cambio**: Verificar que sensores leen de coordinator correctamente

```python
# En TripsListSensor.native_value:
@property
def native_value(self) -> Any:
    """Return sensor value - read directly from coordinator.data."""
    if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
        data = self._coordinator.data
        if data:
            recurring = data.get("recurring_trips", [])
            punctual = data.get("punctual_trips", [])
            # ... actualizar cache ...
            return len(recurring) + len(punctual)
    return 0
```

### 5. trip_manager.py

**Cambio**: Posible problema con persistencia

```python
async def _load_trips(self) -> None:
    """Carga los viajes desde el almacenamiento persistente."""
    try:
        # FIX: Verificar que usa hass.data correcto
        # El namespace debe ser: ev_trip_planner_{entry_id}
        entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
        if entry:
            namespace = f"{DOMAIN}_{entry.entry_id}"
            self._trips = self.hass.data.get(namespace, {}).get("trips", {})
            # ...
```

---

## Tests Requeridos

```bash
# Ejecutar tests existentes
pytest tests/ -v --cov=custom_components/ev_trip_planner

# Tests específicos a crear/actualizar:
# - test_config_flow_issues.py::test_no_vehicle_type_selector
# - test_config_flow_issues.py::test_charging_status_sensor_translated
# - test_sensor_update.py::test_sensors_update_after_trip_creation
# - test_coordinator_update.py::test_coordinator_refresh_on_trip_add
```

---

## Verificación Post-Implementación

1. **Config Flow**:
   - [ ] Flujo de configuración tiene 4 pasos (no 5)
   - [ ] No hay selector de tipo de vehículo
   - [ ] charging_status_sensor tiene hint en español

2. **Dashboard**:
   - [ ] Dashboard se importa tras configuración
   - [ ] Dashboard sobrescribe versión anterior si existe

3. **Sensores**:
   - [ ] Crear trip via servicio -> sensor muestra count correcto
   - [ ] Sensores se actualizan <1s después de crear trip
   - [ ] Trips persisten tras reinicio de HA

4. **Coverage**:
   - [ ] Coverage >80% en código modificado

---

## Notas Adicionales

- Esta implementación sigue la constitución del proyecto:
  - Line length: 88 caracteres
  - Type hints requeridos
  - Docstrings Google style
  - Imports ordenados (isort)
  - Async/await siempre
- Usar Conventional Commits: `fix: eliminar selector vehicle_type`, etc.

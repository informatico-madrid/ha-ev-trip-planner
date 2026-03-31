# Research: EV Trip Planner Integration Fixes

## Executive Summary

This research analyzes critical bugs in the EV Trip Planner HA integration. Findings from HA core and frontend source code reveal root causes and proper patterns for fix implementation.

**Key findings:**
- Panel duplicado: doble registro de panel (config_flow + __init__)
- Panel flickering: causado por duplicated panels + aggressive refresh
- Cascade delete: `async_delete_all_trips()` called but method NOT implemented
- Sensores orphaned: cleanup incomplete en unload flow
- EMHASS profile 0W: wrong entry lookup + discarded values

## Research Sources

### HA Core (investigado)
- `/mnt/bunker_data/ha-ev-trip-planner/ha-core-source/homeassistant/components/panel_custom/__init__.py`
- `/mnt/bunker_data/ha-ev-trip-planner/ha-core-source/homeassistant/core.py` (ConfigEntries)
- `/mnt/bunker_data/ha-ev-trip-planner/ha-core-source/homeassistant/components/frontend/__init__.py`

### HA Frontend (investigado)
- `/mnt/bunker_data/ai/home-assistant-frontend/src/layouts/partial-panel-resolver.ts`
- `/mnt/bunker_data/ai/home-assistant-frontend/src/panels/lovelace/ha-panel-lovelace.ts`
- `/mnt/bunker_data/ai/home-assistant-frontend/src/panels/lovelace/hui-root.ts`

### EV Trip Planner Codebase
- `custom_components/ev_trip_planner/__init__.py`
- `custom_components/ev_trip_planner/config_flow.py`
- `custom_components/ev_trip_planner/trip_manager.py`
- `custom_components/ev_trip_planner/emhass_adapter.py`
- `custom_components/ev_trip_planner/panel.py`

---

## Bug 1: Panel Duplicado

### Root Cause (CONFIRMED)

El panel se registra DOS VECES en puntos diferentes:

1. **En `config_flow.py:778-782`** (durante `_async_create_entry`):
   ```python
   await panel_module.async_register_panel(
       hass,
       vehicle_id=vehicle_id,  # lowercase desde normalize_vehicle_id
       vehicle_name=vehicle_name,
   )
   ```

2. **En `__init__.py:652`** (durante `async_setup_entry`):
   ```python
   await panel_module.async_register_panel(
       hass,
       vehicle_id=vehicle_id,  # PROBLEMA: aquí vehicle_id NO está normalizado!
       vehicle_name=vehicle_name,
   )
   ```

### Evidence from HA Core

**Panel registration** (`frontend/__init__.py` lines 359-393):
```python
def async_register_built_in_panel(...) -> None:
    panel = Panel(...)
    panels = hass.data.setdefault(DATA_PANELS, {})
    if not update and panel.frontend_url_path in panels:
        raise ValueError(f"Overwriting panel {panel.frontend_url_path}")
    panels[panel.frontend_url_path] = panel
    hass.bus.async_fire(EVENT_PANELS_UPDATED)
```

**HA usa `frontend_url_path` como key** - si "Chispitas" y "chispitas" son tratados diferente, se crean 2 paneles.

### Fix Required

En `__init__.py:471`, normalizar vehicle_id ANTES de pasar a `async_register_panel`:
```python
vehicle_id_raw = entry.data.get("vehicle_name", "")
vehicle_id = vehicle_id_raw.lower().replace(" ", "_") if vehicle_id_raw else ""
```

O eliminar el registro de panel de `__init__.py` y solo dejarlo en `config_flow.py`.

---

## Bug 2: Panel Parpadeando (Flickering)

### Root Cause Analysis

**No es problema del DataUpdateCoordinator** - es causado por:

1. **Duplicate panels** (Bug 1) - dos paneles con URLs diferentes cargando el mismo contenido
2. **Frontend view recreation** - cuando cambia algo, el frontend recrea toda la view

### Evidence from HA Frontend

**`hui-root.ts` view selection** (lines 1160-1214):
```typescript
private _selectView(viewIndex: HUIRoot["_curView"]): void {
  if (root.lastChild) {
    root.removeChild(root.lastChild);  // Full removal!
  }
  root.appendChild(view);  // Append new view
}
```

**`hui-view.ts` update pattern** (lines 203-256):
```typescript
protected update(changedProperties: PropertyValues) {
  super.update(changedProperties);
  if (this._layoutElement) {
    if (changedProperties.has("hass")) {
      this._badges.forEach((badge) => { badge.hass = this.hass; });
      this._cards.forEach((element) => { element.hass = this.hass; });
      // Cada card se actualiza con el nuevo hass
    }
  }
}
```

**Refresh debouncing** en Lovelace (`ha-panel-lovelace.ts` lines 359-411):
```typescript
if (this.lovelace && this.lovelace.mode === "yaml") {
  this._ignoreNextUpdateEvent = true;
  setTimeout(() => {
    this._ignoreNextUpdateEvent = false;
  }, 2000);  // 2-second ignore window
}
```

### Source of WARNING Logs

Los WARNING logs en `__init__.py:1326, 1328` son de `handle_trip_list()` service handler - NO del coordinator:
```python
_LOGGER.warning("First recurring trip: %s", recurring_trips[0])
_LOGGER.warning("total_trips: %d", result["total_trips"])
```

Estos se llaman cuando el servicio `trip_list` es invocado. Si el panel está refreshindo constantemente, cada refresh llama el servicio.

### Fix Required

1. **Fix Bug 1** (duplicate panels) - esto eliminará el flickering
2. Cambiar WARNING logs a DEBUG para evitar spam en consola
3. Implementar debounce si es necesario

---

## Bug 3: Cascade Delete Roto

### Root Cause (CONFIRMED)

**`__init__.py:739` llama `trip_manager.async_delete_all_trips()` pero el método NO existe en TripManager.**

### Evidence from HA Core

**Config entry unload flow** (`core.py` lines 994-1032):
```python
result = await component.async_unload_entry(hass, self)
if result:
    await self._async_process_on_unload(hass)  # Procesa callbacks
    if hasattr(self, "runtime_data"):
        object.__delattr__(self, "runtime_data")
```

**Entity cleanup** (`entity_platform.py` lines 1000-1023):
```python
async def async_reset(self) -> None:
    for entity in list(self.entities.values()):
        await entity.async_remove()  # Cada entidad se limpia
```

### Fix Required

Implementar `async_delete_all_trips()` en `trip_manager.py`:
```python
async def async_delete_all_trips(self) -> None:
    """Elimina todos los viajes de este vehículo."""
    self._recurring_trips.clear()
    self._punctual_trips.clear()
    await self.async_save_trips()
```

---

## Bug 4: Sensores Old Persisten (Orphaned Sensors)

### Root Cause

Cuando se borra un vehículo:
1. El panel se desregistra (`async_unregister_panel`)
2. Los entities se limpian via `async_unload_platforms`
3. **PERO** los sensors de tipo `sensor.py` basados en `EntityPlatform` deberían limpiarse automáticamente

El problema es que el **sensor `emhass_perfil_diferible_01kn2grt...`** tiene un ID que sugiere que es de una instalación anterior.

### Possible Cause

El entity_id del sensor EMHASS usa un suffix basado en entry_id:
```python
# sensor.py línea ~350
f"{DOMAIN}_emhass_perfil_diferible_{entry.entry_id[-13:]}"
```

Si el entry_id es diferente pero el vehicle_name es igual, el sensor podría tener un nombre residual.

### Fix Required

Verificar que `EmhassDeferrableLoadSensor` se limpia correctamente cuando el vehículo se desinstala.

---

## Bug 5: EMHASS Profile Muestra 0W

### Root Cause (CONFIRMED - Multiple Issues)

**Issue 5a**: Wrong entry lookup in `trip_manager.py`:
```python
# Línea 1919 - USA self.vehicle_id (nombre) en vez de entry_id!
entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
# Esto siempre retorna None porque vehicle_id NO es entry_id
```

**Issue 5b**: Return values discarded:
```python
# Línea 1921 - return value IGNORED!
entry.data.get("battery_capacity_kwh", 50.0)

# Línea 1926 - return value IGNORED!
await self.async_get_vehicle_soc(self.vehicle_id)
```

**Issue 5c**: Always falls back to defaults:
```python
battery_capacity = 50.0  # Default hardcoded
soc_current = 50.0       # Default hardcoded
```

### Fix Required

1. Fix entry lookup:
```python
entry = self.hass.config_entries.async_get_entry(self._entry_id)
```

2. Guardar y usar los valores:
```python
battery_capacity = entry.data.get("battery_capacity_kwh", 50.0)
soc_current = await self.async_get_vehicle_soc(self.vehicle_id)
```

---

## Bug 6: SOC No Se Muestra

### Root Cause

Dashboard template usa:
```yaml
{% set soc_sensor = states('sensor.{{ vehicle_id }}_soc') %}
```

Pero el SOC real viene de `entry.data.get("soc_sensor")` que tiene nombre diferente (ej: `sensor.ovms_chispitas_metric_v_b_soc`).

### Fix Required

El panel/dashboard debe usar el `soc_sensor` configurado, no un sensor inferido del vehicle_id.

---

## Bug 7: kWh Debería Auto-Calcularse

### Current State

El campo `kwh` es input de usuario. Debería calcularse de `km * consumption / 100`.

### Evidence

`calcular_energia_kwh()` existe en `utils.py` pero no se usa como source primario.

### Fix Required

1. Hacer campo kWh readonly en UI
2. Calcular automáticamente cuando `km` cambia

---

## HA Core Patterns Reference

### Panel Registration (Correct Pattern)
```python
# frontend/__init__.py
def async_register_built_in_panel(...):
    panels = hass.data.setdefault(DATA_PANELS, {})
    if not update and panel.frontend_url_path in panels:
        raise ValueError(f"Overwriting panel {panel.frontend_url_path}")
    panels[panel.frontend_url_path] = panel
```

### Cascade Delete (Correct Pattern)
```python
# En async_unload_entry del componente:
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # 1. Limpiar datos propios
    await trip_manager.async_delete_all_trips()

    # 2. Unload platforms (limpia entities)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # 3. Limpiar runtime data
    if DATA_RUNTIME in hass.data:
        hass.data[DATA_RUNTIME].pop(namespace, None)

    return unload_ok
```

---

## Skills Identified for Implementation

| Skill | Purpose |
|-------|---------|
| `homeassistant-dashboard-designer` | Para arreglar panel flickering y UI del panel |
| `homeassistant-best-practices` | Patrones correctos de HA para cascade delete, entity cleanup |
| `ha-e2e-testing` | Tests E2E para verificar fixes |

---

## Next Steps

1. **Fix Bug 1** (panel duplicado) - normalizar vehicle_id
2. **Fix Bug 3** (cascade delete) - implementar `async_delete_all_trips()`
3. **Fix Bug 5** (EMHASS 0W) - corregir entry lookup
4. **Fix Bug 2** (flickering) - debería resolverse con Bug 1
5. **Fix Bug 4** (orphan sensors) - verificar cleanup de sensors
6. **Fix Bug 6** (SOC display) - usar soc_sensor correcto
7. **Fix Bug 7** (kWh auto-calc) - implementar cálculo automático

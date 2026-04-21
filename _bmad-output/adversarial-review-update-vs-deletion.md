# Adversarial Review: Mecanismo de Actualización vs Bug de Eliminación

**Fecha**: 2026-04-19  
**Tipo**: Adversarial Review — Análisis cínico  
**Alcance**: Funcionalidad que mantiene viajes/sensor actualizados vs interferencia con eliminación  
**Archivos auditados**: `coordinator.py`, `emhass_adapter.py`, `trip_manager.py`, `services.py`

---

## Findings

### F1: `_handle_config_entry_update` puede re-publicar viajes durante eliminación — **CRÍTICO**

**Ubicación**: [`emhass_adapter.py:1920-1950`](custom_components/ev_trip_planner/emhass_adapter.py:1920)

El callback `_handle_config_entry_update` tiene una ruta de "reload from trip_manager":

```python
# Línea 1933-1948
if not self._published_trips:
    coordinator = self._get_coordinator()
    if coordinator is not None and hasattr(coordinator, "_trip_manager"):
        trip_manager = coordinator._trip_manager
        if trip_manager is not None:
            all_trips = trip_manager.get_all_trips()
            if all_trips:
                all_trips_list = all_trips.get("recurring", []) + all_trips.get("punctual", [])
                self._published_trips = all_trips_list  # ← RE-PUBLICA viajes viejos
```

Luego llama [`update_charging_power()`](custom_components/ev_trip_planner/emhass_adapter.py:1952) que ejecuta:
```python
await self.publish_deferrable_loads(self._published_trips, new_power)  # línea 1990
```

**El guardia actual** (remover listener en [`services.py:1418`](custom_components/ev_trip_planner/services.py:1418)) es correcto PERO asume que ningún evento de config entry update está pendiente en el event loop. Si HA dispara un evento de update durante el inicio de `async_unload_entry`, el callback podría ejecutarse ANTES de que la línea 1418 se procese.

**Escenario de fallo**:
1. HA inicia `async_unload_entry` 
2. HA dispara evento de config entry update (por cambio interno durante unload)
3. `_handle_config_entry_update` se encola en el event loop
4. `async_unload_entry_cleanup` ejecuta y remueve el listener (línea 1418)
5. **PERO** el evento ya encolado en paso 3 se ejecuta después
6. `_published_trips` aún no está vacío → no entra al reload
7. `update_charging_power` re-publica viajes con `self._published_trips` viejos

### F2: `publish_deferrable_loads(None)` re-fetchea todos los viajes — **ALTO**

**Ubicación**: [`trip_manager.py:167-178`](custom_components/ev_trip_planner/trip_manager.py:167)

```python
async def publish_deferrable_loads(self, trips=None):
    if trips is None:
        trips = await self._get_all_active_trips()  # ← Lee de _trips dict
```

Si cualquier código llama `publish_deferrable_loads()` sin argumentos durante el flujo de eliminación (ANTES de que `_trips` se limpie), se re-publican todos los viajes.

**Lugares donde se llama sin argumentos**:
- [`trip_manager.py:208`](custom_components/ev_trip_planner/trip_manager.py:208) — `async_setup()` 
- [`trip_manager.py:1005`](custom_components/ev_trip_planner/trip_manager.py:1005) — pausar viaje
- [`trip_manager.py:1033`](custom_components/ev_trip_planner/trip_manager.py:1033) — reanudar viaje
- [`trip_manager.py:1049`](custom_components/ev_trip_planner/trip_manager.py:1049) — editar viaje
- [`presence_monitor.py:566`](custom_components/ev_trip_planner/presence_monitor.py:566) — cambio de SOC

**Ninguno de estos debería ejecutarse durante eliminación**, pero el `presence_monitor` tiene un listener de SOC que podría disparar si el vehículo está conectado.

### F3: El coordinator se refresca cada 30 segundos y puede propagar datos stale — **MEDIO**

**Ubicación**: [`coordinator.py:67`](custom_components/ev_trip_planner/coordinator.py:67)

```python
update_interval=timedelta(seconds=30),
```

El coordinator lee de dos fuentes en [`_async_update_data`](custom_components/ev_trip_planner/coordinator.py:88):
1. `trip_manager.async_get_recurring_trips()` — lee de `_trips` dict
2. `emhass_adapter.get_cached_optimization_results()` — lee de cache

**Timing issue**: Si el coordinator refresca entre el paso 1 (limpiar `_trips`) y el paso 3 (limpiar cache) de `async_delete_all_trips`:
- `recurring_trips` y `punctual_trips` serán `{}`
- Pero `per_trip_emhass_params` aún tendrá datos stale del cache
- El sensor EMHASS mostraría viajes en `def_total_hours_array` pero sin datos de viaje

**Se resuelve solo** en el siguiente refresh (30s después), pero puede causar falsos positivos en tests E2E que leen el estado inmediatamente después de la eliminación.

### F4: `async_delete_all_trips` llama `coordinator.async_refresh()` que re-dispara `_async_update_data` — **MEDIO**

**Ubicación**: [`trip_manager.py:768`](custom_components/ev_trip_planner/trip_manager.py:768)

```python
await coordinator.async_refresh()
```

Esto dispara `_async_update_data` que lee de `trip_manager` (ya vacío) y `emhass_adapter` cache (ya limpio). El resultado debería ser correcto.

**PERO**: `async_refresh()` puede causar que entidades eliminadas se re-agreguen a `hass.states` temporalmente. El propio código tiene un comentario al respecto:

```python
# línea 1736: "Do NOT call coordinator.async_refresh() here - it can cause the removed
# entity to be re-added to hass.states."
```

Sin embargo, `async_delete_all_trips` SÍ llama `async_refresh()` en la línea 768. Esto es inconsistente.

### F5: `update_charging_power` no verifica si la integración está siendo eliminada — **MEDIO**

**Ubicación**: [`emhass_adapter.py:1952-1990`](custom_components/ev_trip_planner/emhass_adapter.py:1952)

```python
async def update_charging_power(self):
    ...
    await self.publish_deferrable_loads(self._published_trips, new_power)
```

No hay ningún flag o check que indique "estoy en modo eliminación". Si `_published_trips` tiene datos stale y este método se llama, re-publica viajes viejos.

**Solución**: Agregar un flag `_shutting_down` al adapter que se setee en `async_cleanup_vehicle_indices` o en `async_unload_entry_cleanup`.

### F6: El `presence_monitor` puede disparar `publish_deferrable_loads()` durante eliminación — **ALTO**

**Ubicación**: [`presence_monitor.py:566`](custom_components/ev_trip_planner/presence_monitor.py:566)

```python
await self._trip_manager.publish_deferrable_loads()
```

El `presence_monitor` tiene un listener de SOC que se ejecuta cuando el estado del sensor de batería cambia. Si el vehículo está conectado y cargando durante la eliminación:
1. El listener de SOC dispara
2. `publish_deferrable_loads()` se llama sin argumentos
3. `_get_all_active_trips()` lee de `_trips` (aún no vacío si es temprano en el flujo)
4. Se re-publican todos los viajes

**No hay guardia** que cancele el listener del presence_monitor durante la eliminación.

### F7: `async_cleanup_stale_storage` solo se ejecuta en re-add, no en delete — **BAJO**

**Ubicación**: [`services.py:1120`](custom_components/ev_trip_planner/services.py:1120)

Si el usuario borra la integración y NO la re-agrega, el storage persiste. Esto ya se documentó en el research anterior. No es un bug del mecanismo de actualización pero contribuye al problema percibido.

### F8: `async_cleanup_orphaned_emhass_sensors` es un stub — **MEDIO**

**Ubicación**: [`services.py:1175-1190`](custom_components/ev_trip_planner/services.py:1175)

Esta función se llama en cada [`async_setup_entry`](custom_components/ev_trip_planner/__init__.py:109) pero no hace nada. Si un vehículo A se elimina parcialmente y el usuario agrega un vehículo B, los sensores huérfanos de A no se limpian.

### F9: El coordinator lee de `get_cached_optimization_results()` que puede tener datos stale — **MEDIO**

**Ubicación**: [`coordinator.py:126`](custom_components/ev_trip_planner/coordinator.py:126)

```python
emhass_data = self._emhass_adapter.get_cached_optimization_results()
```

El coordinator lee del cache del adapter. Si el adapter fue limpiado pero el coordinator aún no refrescó, los sensores muestran datos stale. El `async_refresh()` en `async_delete_all_trips` debería resolver esto, pero hay una ventana de tiempo.

### F10: Múltiples safeguards en `async_delete_all_trips` indican diseño frágil — **ALTO**

**Ubicación**: [`trip_manager.py:706-770`](custom_components/ev_trip_planner/trip_manager.py:706)

El método tiene **5 safeguards** diferentes:
1. Clear `_trips` dict first
2. Clear `_published_trips` and cache
3. Call `publish_deferrable_loads([])` with explicit empty list
4. Extra safeguard: directly clear adapter cache again
5. Directly set `coordinator.data` and call `async_refresh()`

Cada safeguard fue agregado para fixear un bug específico. Esto indica que el diseño fundamental es frágil: no hay un mecanismo atómico de "shut down" que prevenga todas las race conditions de una vez.

**Solución arquitectónica**: Agregar un flag `_shutting_down` al TripManager/EMHASSAdapter que:
- Se setee al inicio de `async_unload_entry_cleanup`
- Todas las funciones de publish/update lo verifiquen antes de ejecutar
- Cancele todos los listeners y timers inmediatamente

---

## Conclusión

**El mecanismo de actualización SÍ puede interferir con la eliminación** a través de estos caminos:

1. **`_handle_config_entry_update`** (F1) — puede re-publicar viajes si un evento está pendiente
2. **`presence_monitor`** (F6) — puede disparar `publish_deferrable_loads()` durante eliminación
3. **Coordinator refresh** (F3) — puede propagar datos stale temporalmente

**La solución más efectiva** es implementar un flag `_shutting_down` que se active al inicio del flujo de eliminación y que todas las funciones de actualización verifiquen antes de ejecutar.

---
name: ha_container_restart_issue
description: Problema con reinicio de contenedor HA y pérdida de trip_manager en memoria volátil
type: feedback
---

**Regla:** Cuando un contenedor de HA se reinicia, `hass.data[DATA_RUNTIME]` se pierde porque es memoria volátil. Los TripManagers guardados en runtime se pierden y hay que recargar desde YAML storage.

**Problema encontrado:** El `_get_manager` creaba TripManagers vacíos después de cada restart porque no recuperaba los viajes del YAML storage.

**Solución aplicada:** Cuando el manager no está en runtime storage, crear uno nuevo y cargar los viajes desde YAML usando `async_setup()`:

```python
def _get_manager(hass: HomeAssistant, vehicle_id: str) -> TripManager:
    entry = _find_entry_by_vehicle(hass, vehicle_id)
    namespace = f"{DOMAIN}_{entry.entry_id}"
    runtime_data = hass.data.get(DATA_RUNTIME, {})
    namespace_data = runtime_data.get(namespace, {})
    trip_manager = namespace_data.get("trip_manager")

    if not trip_manager:
        trip_manager = TripManager(hass, vehicle_id)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(trip_manager.async_setup())

    return trip_manager
```

**Por qué:** El YAML storage persiste en `/config/ev_trip_planner/ev_trip_planner_chispitas.yaml` y se carga en `async_setup()` -> `async_load_trips()` -> `_load_trips_yaml()`.

**Nota:** Evitar `async` en `_get_manager` porque se llama desde contextos no asíncronos. Usar `loop.run_until_complete()` para cargar trips.

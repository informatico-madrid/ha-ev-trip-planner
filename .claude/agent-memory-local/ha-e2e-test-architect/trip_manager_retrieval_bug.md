---
name: trip_manager_retrieval_bug
description: Bug en _get_manager que crea TripManager nuevo en lugar de usar el existente
type: feedback
---

**Regla:** El `_get_manager` debe recuperar el TripManager existente de `hass.data[DATA_RUNTIME][namespace]["trip_manager"]`, no crear uno nuevo.

**Por qué:** El código original intentaba obtener el manager desde `managers.get(vehicle_id)` que siempre retornaba `None`, causando que se creara un `TripManager(hass, vehicle_id)` nuevo en cada llamada. Esto significaba que los viajes guardados en el manager original no eran visibles cuando se llamaba al servicio `trip_list`.

**Código original (incorrecto):**
```python
managers = runtime_data.get(namespace, {}).get("managers", {})
return managers.get(vehicle_id) or TripManager(hass, vehicle_id)
```

**Código corregido:**
```python
namespace_data = runtime_data.get(namespace, {})
return namespace_data.get("trip_manager") or TripManager(hass, vehicle_id)
```

**Cómo aplicar:** Verificar que cualquier función que necesite acceder al TripManager use `namespace_data.get("trip_manager")` en lugar de `managers.get(vehicle_id)`.

**Verificación:** Después del fix, los servicios que listan viajes (`trip_list`) ahora retornan correctamente los viajes almacenados en el manager existente.

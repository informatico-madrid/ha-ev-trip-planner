---
name: datetime_field_bug
description: Bug en servicio handle_add_punctual con campo datetime incorrecto
type: feedback
---

**Problema encontrado:** El servicio `handle_add_punctual` estaba pasando el campo de fecha con nombre inconsistente.

**Causa raíz:** El servicio recibía `data["datetime"]` del frontend, pero al llamar a `async_add_punctual_trip` se estaba pasando como `datetime_str=data["datetime"]`. Sin embargo, en el método `async_add_punctual_trip` se esperaba `datetime_str` en kwargs pero el servicio ya lo estaba pasando con ese nombre.

**Solución verificada:** Mantener `datetime_str` como nombre del parámetro para consistencia:
```python
await mgr.async_add_punctual_trip(
    datetime_str=data["datetime"],  # Correcto
    km=float(data["km"]),
    kwh=float(data["kwh"]),
    descripcion=str(data.get("descripcion", "")),
)
```

**Error causado:** Viajes puntuales se guardaban con `datetime: null` en el YAML storage, causando errores `strptime() argument 1 must be str, not None` al intentar parsear las fechas.

**Verificación:** Los viajes puntuales ahora se guardan correctamente con el campo `datetime` poblado en el YAML storage.

**Ficheros afectados:** custom_components/ev_trip_planner/__init__.py línea 662-667, trip_manager.py línea 318
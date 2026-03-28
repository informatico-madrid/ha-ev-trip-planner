---
name: metodologia_verificacion
description: Verificar con logs Y observabilidad frontend, no solo logs de backend
type: procedural
---

# Verificación con Logs Y Observabilidad Frontend

## Regla Crítica

Después de implementar cualquier fix, verificar **SIEMPRE** con:

1. **Logs de backend** (`home-assistant.log`, `_LOGGER.warning()`)
2. **Observabilidad frontend** (`browser_snapshot()`, `console_messages()`, `browser_evaluate()`)

**NUNCA** te confíes solo de los logs de backend.

## Por Qué

Los logs de backend pueden mostrar que el código se ejecuta correctamente, pero el frontend puede tener:

- Errores de rendering
- Estado no actualizado
- Errores de JavaScript que los logs no capturan
- Datos no mostrados aunque se carguen correctamente

## Ejemplo: Bug de Store API (2026-03-27)

### Backend Logs ✅
```
=== _load_trips START === vehicle=chispitas
=== async_load returned: True ===
=== self._recurring_trips: 1 recurrentes ===
```

### Verificación Frontend
```javascript
// ¿Los viajes aparecen en el panel?
await browser_snapshot();
// Inspeccionar el DOM
await browser_evaluate(() => document.querySelectorAll('.trip-card').length);
// Verificar consola JS
await browser_console_messages();
```

## Cómo Aplicar

### Paso 1: Implementar Fix
```python
# En trip_manager.py
if isinstance(stored_data, dict) and "data" in stored_data:
    data = stored_data.get("data", {})
else:
    data = stored_data  # Fallback

self._recurring_trips = data.get("recurring_trips", {})
```

### Paso 2: Verificar Backend
```bash
# Buscar logs en home-assistant.log
docker exec homeassistant tail -n 2000 /config/home-assistant.log | \
  grep "self._recurring_trips: 1 recurrentes"
```

### Paso 3: Verificar Frontend
```javascript
// Usar browser_snapshot() para ver el DOM
await browser_snapshot();

// Verificar si los viajes aparecen
await browser_evaluate(() => {
  const trips = document.querySelectorAll('.trip-card');
  console.log('Trips found:', trips.length);
  return trips.length;
});

// Verificar consola JS
await browser_console_messages();
```

## Casos Críticos

### 1. Bugs de Rendering
- Backend carga datos ✅
- Frontend NO muestra elementos ❌
- **Causa:** Error en `_formatTripDisplay()`, `_render()`, o template

### 2. Estado No Sincronizado
- Backend actualiza datos ✅
- Frontend no actualiza estado ❌
- **Causa:** No se llama `this.requestUpdate()` o estado no se actualiza

### 3. Errores de JavaScript
- Backend funciona ✅
- Consola JS muestra errores ❌
- **Causa:** JavaScript no carga, selector incorrecto, callback no existe

### 4. Datos No Mostrados
- Backend carga datos ✅
- Frontend muestra "No hay viajes" ❌
- **Causa:** `_getTripsList()` no llama al servicio correcto, `_loadTrips()` no actualiza

## Checklist de Verificación

- [ ] Logs de backend muestran datos cargados
- [ ] `browser_snapshot()` muestra elementos en DOM
- [ ] `console_messages()` no muestra errores JS
- [ ] `browser_evaluate()` confirma estado correcto
- [ ] Botones CRUD funcionan (Editar, Eliminar, etc.)
- [ ] Datos aparecen con valores correctos

## Ejemplo de Verificación Completa

```python
# 1. Backend logs
docker exec homeassistant tail -n 1000 /config/home-assistant.log | \
  grep -E "WARNING.*_load_trips|WARNING.*_recurring_trips"

# 2. Frontend snapshot
await browser_snapshot(filename="panel-after-fix.png");

# 3. Verificar consola JS
await browser_console_messages(level="error");

# 4. Inspeccionar estado
await browser_evaluate(() => {
  const panel = document.querySelector('ev-trip-planner-panel');
  console.log('Panel trips:', panel._trips?.length);
  return panel._trips?.length;
});
```

## Principio

**"La evidencia lo es todo"**: Nunca afirmar que algo funciona sin evidencia concreta de backend Y frontend.

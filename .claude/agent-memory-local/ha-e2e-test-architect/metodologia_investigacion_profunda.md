---
name: metodologia_investigacion_profunda
description: "Lección crítica: investigar el código profundamente antes de implementar cambios, no ir a prueba y error"
type: feedback
---

# Metodología de Desarrollo Correcta para HA Integrations

## ⚠️ LECCIÓN CRÍTICA APRENDIDA (2026-03-27)

### Problema Detectado
Fuimos a **prueba y error** en lugar de investigar a fondo el código antes de implementar cambios.

### ÉXITO PARCIAL ALCANZADO
- ✅ **Sistema ahora cuenta correctamente los viajes** (4 en chispitas_trips_list)
- ✅ **Store API funciona** - Persistencia confirmada en `/config/.storage/ev_trip_planner_chispitas`
- ✅ **Observabilidad establecida** - Logs detallados permiten diagnóstico
- ✅ **Flujo de avance validado**: investigar → implementar → probar → detener → reportar

### FALLO TEMPORAL
- ❌ Error al cambiar `async def` a `def` - se rompió el panel
- ❌ `asyncio.run()` no funciona dentro de event loop existente

---

## 📋 FLUJO CORRECTO DE AVANZE (NUEVA METODOLOGÍA)

### FASE 1: INVESTIGACIÓN PROFUNDA (OBLIGATORIO)
**Antes de hacer CUALQUIER CAMBIO:**

1. **Leer TODO el código del plugin**
   - `trip_manager.py` - todas las clases, métodos, parámetros
   - `__init__.py` - contratos con Home Assistant
   - `dashboard.py` - dependencias y flujos
   - `panel.js` - frontend y comunicaciones

2. **Investigar el Core de Home Assistant**
   - `homeassistant.helpers.storage.Store` - cómo funciona realmente
   - `hass.loop.run_until_complete()` - cuándo se puede usar
   - Contratos y dependencias del plugin

3. **Documentar TODOS los contratos**
   - Entradas/salidas de cada método
   - Expectativas del core
   - Patrones de uso confirmados

### FASE 2: IMPLEMENTACIÓN CON CONOCIMIENTO
Solo después de la investigación:
- Implementar cambios con conocimiento completo
- Probar inmediatamente
- Detenerse y reportar resultados

### FASE 3: VALIDACIÓN Y DETENCIÓN
- ✅ Verificar que funciona
- ✅ Anotar lo que aprendió
- ✅ Actualizar memoria con patrones validados
- 🛑 **DETENERSE inmediatamente si algo falla**

---

## 🛠️ Patrón Correcto de Trabajo

```
1. INVESTIGAR → 2. DOCUMENTAR → 3. IMPLEMENTAR → 4. VALIDAR → 5. DETENER Y REPORTAR
```

### No hacer:
- ❌ Cambiar código sin entender `async/await`
- ❌ Asumir que `def` funciona igual que `async def`
- ❌ Cambiar 3 cosas y esperar que funcione

### Hacer:
- ✅ Leer el código completo primero
- ✅ Entender el flow de ejecución
- ✅ Cambiar con conocimiento, no con adivinanzas
- ✅ Detenerse inmediatamente si algo falla

---

## 📚 Recursos Clave a Investigar

### Home Assistant Core Storage
- `homeassistant.helpers.storage.Store`
  - Constructor: `Store(hass, version, key, **kwargs)`
  - Método: `async_load()` - retorna coroutine
  - Método: `async_save(data)` - retorna coroutine

### Patrones de Ejecución
- `hass.loop.run_until_complete(coro)` - solo en callbacks síncronos
- `await` - en funciones async
- `asyncio.run()` - crear nuevo event loop (no anidable)

### Contratos del Plugin
- `async_setup_entry()` - debe ser async
- `async_setup()` - debe ser async
- `async_*_trip_*()` - todos async para compatibilidad con HA

---

## 🎯 Resultado de la Sesion (2026-03-27)

### Lo que Logramos
1. ✅ **Persistencia verificada**: Los viajes se guardan correctamente en Store API
2. ✅ **Conteo correcto**: Sensor `chispitas_trips_list` muestra 4 viajes
3. ✅ **Flujo establecido**: Metodología de investigación profunda antes de implementar

### Lo que Aprendimos
1. ❌ `async def` no puede convertirse en `def` - rompe el event loop
2. ❌ `asyncio.run()` crea nuevo event loop - no funciona dentro de HA
3. ✅ `hass.loop.run_until_complete()` funciona en callbacks

### Próximo Paso
Revisar el código `trip_manager.py` en profundidad para entender por qué el panel dejó de funcionar y corregir con conocimiento, no con adivinanzas.

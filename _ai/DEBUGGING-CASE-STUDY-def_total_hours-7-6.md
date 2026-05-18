# Debugging Case Study: def_total_hours [7, 6] Bug

## Resumen del Bug

**Síntoma:** `def_total_hours: [7, 6]` en staging en lugar de `[2, 2]` esperados.

**Causa Raíz:** `EMHASSAdapter` no leía `battery_capacity_kwh` ni `soc_sensor` de `ConfigEntry`, usando defaults (50.0 kWh, 50% SOC) en lugar de valores configurados (28.0 kWh, 65% SOC).

---

## Flujo Correcto para Encontrar Bugs Similares

### 1. NO Asumir que el Código Actual Está Bien
**Regla:** "Doubt by Default: Nunca asumas que lo que dice el usuario o la documentación es verdad respecto al estado actual del disco."

**Error inicial:** Asumí que `EMHASSAdapter.__init__` ya leía `battery_capacity_kwh` de `ConfigEntry` porque había código que parecía hacerlo en `_populate_per_trip_cache_entry`.

### 2. Verificar los Valores Reales en el Disco
**Acción:** Ejecutar `docker logs ha-staging` y greppor los valores que se usan.

**Hallazgo clave:**
```
BUG-DEBUG: _precompute_and_process_trips battery_capacity_kwh=50.00
```
¡El log mostraba 50.0 kWh, no 28.0 kWh del config!

### 3. El Debug Logging es Esencial
**Acción:** Añadir logs en TODOS los puntos de entrada de datos.

Sin el logging en:
- `async_publish_all_deferrable_loads` (línea 291)
- `_precompute_and_process_trips` (línea 319)
- `_populate_per_trip_cache_entry` (línea 823)

No habría sido posible ver qué valores se usaban realmente.

### 4. Crear Tests que FALLEN si No se Usan Valores del Config
**Concepto:** Un test que pasa no te dice nada. Un test que falla te dice exactamente qué está roto.

**Tests creados:**
- `test_adapter_must_read_battery_capacity_from_config_entry` → FAILED (antes del fix)
- `test_adapter_must_read_soc_from_hass_sensor` → FAILED (antes del fix)

Estos tests fallaban porque el adapter no leía los valores del config entry.

### 5. Verificar en el Entorno Real (Staging)
**Acción:** Después del fix, reiniciar el contenedor y verificar con `docker logs`.

**Verificación:**
```
ANTES: def_total_hours=[7, 6]
DESPUÉS: def_total_hours=[2]
```

---

## Inconvenientes que Me Despidtaron

### 1. Confiar en el Código Sin Verificar en Runtime
**Lo que pensé:** "El código parece que ya lee battery_capacity_kwh de entry.data"

**Lo que pasó:** El código de `_populate_per_trip_cache_entry` sí leía `battery_capacity_kwh`, pero lo recibía como parámetro de `_precompute_and_process_trips`, que obtenía el valor de `_load_publisher.battery_capacity_kwh` (que tenía el default 50.0).

**Lección:** Hay que verificar en runtime, no solo leer el código.

### 2. No Mirar los Logs de Staging Inmediatamente
**Lo que pensé:** "Voy a añadir debug logs y verlos después"

**Lo que pasó:** Debí mirar los logs de staging ANTES de escribir código. Los logs ya mostraban `battery_capacity_kwh=50.00`.

**Lección:** "Verification Loop: Antes de emitir cualquier resultado, DEBES ejecutar las herramientas que sean necesarias para confirmar tu hipótesis."

### 3. Intentar Arreglar en Ves de Reproducir
**Lo que pensé:** "Voy a añadir el fix directamente"

**Lo que pasó:** El usuario me detuvo y dijo "NO estamos arreglando el bug, estamos reproduciéndolo".

**Lección:** Seguir el proceso: reproducir → analizar → crear tests → fix.

### 4. No Creé Tests que Fallaran Desde el Principio
**Error:** Creé tests que PASABAN con el bug (reproduciendo el bug), pero no creé tests que FALLARAN (que detectaran el problema).

**Lección:** Los tests que fallan son más útiles para identificar el bug. Los tests que pasan con valores buggy solo confirman el bug existente.

### 5. No Seguir el Flujo de Datos Completo
**Error:** Me centré en `_populate_per_trip_cache_entry` sin seguir el flujo desde `EMHASSAdapter.__init__`.

**Lección:** Siempre seguir el flujo de datos desde el inicio:
```
ConfigEntry → EMHASSAdapter.__init__ → LoadPublisherConfig → _load_publisher → _precompute → _populate_per_trip_cache_entry
```

---

## Cómo Evitar Estos Errores en el Futuro

### Checklist de Debugging

1. [ ] **Verificar valores en runtime** - No asumir, ejecutar `docker logs` o similar
2. [ ] **Añadir debug logging en puntos de entrada** - Especialmente en constructores y métodos que leen configuración
3. [ ] **Crear tests que FALLEN** - No solo tests que reproduzcan el bug
4. [ ] **Seguir el flujo completo de datos** - Desde input hasta output
5. [ ] **No Fixar Antes de Reproducir** - El usuario tenía razón: "NO estamos arreglando el bug, estamos reproduciéndolo"

### Reglas para Agentes IA (de este caso)

1. **"Verification Loop"** - Siempre verificar con herramientas antes de emitir resultados
2. **"Doubt by Default"** - Nunca asumir que el código está bien sin verificar
3. **"No Quick Summaries"** - Mínimo 3 pasos de investigación antes de responder
4. **Tests > Código** - Crear tests que fallen es más valioso que código que parece funcionar

---

## Archivos Modificados

- `custom_components/ev_trip_planner/emhass/adapter.py` - Fix en `__init__` y `_get_current_soc`
- `tests/integration/test_multi_trip_staging_scenario.py` - Tests de reproducción y validación
- `docs/BUG-ANALYSIS-def_total_hours-7-6.md` - Análisis detallado del bug

---

## Tags para Búsqueda Futura

`debugging-case-study` `verification-loop` `no-quick-summaries` `emhass-adapter` `config-entry` `battery-capacity` `soc-sensor`
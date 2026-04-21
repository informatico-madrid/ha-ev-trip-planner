# Análisis Estratégico: 3 Casos de Código No Cubierto

**Analista:** Mary (BMAD Business Analyst)  
**Fecha:** 2026-04-21  
**Proyecto:** EV Trip Planner - Cobertura de Tests  

---

## Resumen Ejecutivo

Se analizaron 3 casos de código no cubierto por tests (11 líneas totales). El análisis revela **un caso de código muerto genuino** (CASE 1) y **dos casos de código defensivo no ejecutado** (CASES 2 y 3). El tratamiento recomendado difiere para cada caso.

---

## CASE 1: Líneas 211-213 en `trip_manager.py` — `frecuencia == "daily"` except block

### Evidencia Recolectada

**Ubicación:** [`trip_manager.py:211-213`](custom_components/ev_trip_planner/trip_manager.py:211)
```python
except Exception as err:  # pragma: no cover - unreachable: "frecuencia" field never set in trip data
    import traceback
    _LOGGER.warning(
        "Failed to rotate daily trip %s: %s\n%s",
        trip.get("id"),
        err,
        traceback.format_exc(),
    )
```

**Contexto de código muerto:**
- El branch `if frecuencia == "daily"` (línea 193) verifica `trip.get("frecuencia")`
- `async_add_recurring_trip()` (líneas 612-621) **NUNCA establece el campo `"frecuencia"`**
- El campo `"frecuencia"` solo aparece en 3 líneas del código, todas en `trip_manager.py`

**Búsqueda de `"frecuencia"`:**
```grep
custom_components/ev_trip_planner/trip_manager.py:
  187 | frecuencia = trip.get("frecuencia")      # READ
  188 | frecuencia = trip.get("frecuencia")      # READ
  193 | if frecuencia == "daily" and time_str:  # CONDITION CHECK
  211 | except Exception as err:                 # NEVER REACHED
```

### Análisis

| Aspecto | Valoración |
|---------|------------|
| **Tipo** | Código muerto (dead code) |
| **Alcanzable en producción** | ❌ NO |
| **Razón raíz** | Inconsistencia de diseño: el campo `"frecuencia"` fue previsto pero nunca implementado en la creación de trips |
| **Impacto en coverage** | 3 líneas no cubiertas |

**El branch `frecuencia == "daily"` NUNCA se ejecuta porque:**
1. `async_add_recurring_trip()` solo establece: `id`, `tipo`, `dia_semana`, `hora`, `km`, `kwh`, `descripcion`, `activo`
2. El campo `"frecuencia"` no está en esa lista
3. No hay ningún otro lugar en el código que agregue `"frecuencia"` a un trip

### Hipótesis de Diseño

Este código sugiere que **T3.2 fue diseñado para soportar dos tipos de recurrencia**:
- `frecuencia == "daily"` → repetir diariamente (implementado pero nunca usado)
- `day_name + time_str` → repetir semanalmente en día específico (el flujo normal)

Sin embargo, el campo `"frecuencia"` **nunca se popula**, haciendo el branch diario permanentemente inalcanzable.

### Recomendación

**Eliminación directa**: Eliminar las líneas 193-218 completas (el branch `if frecuencia == "daily"`). Este código:
- No tiene uso en producción
- Es confundido con código activo
- Su existencia implica una feature que no existe
- El `# pragma: no cover` sería mentir sobre el estado del código

---

## CASE 2: Líneas 251-260 en `trip_manager.py` — Warning en branch semanal

### Evidencia Recolectada

**Ubicación:** [`trip_manager.py:250-257`](custom_components/ev_trip_planner/trip_manager.py:250)
```python
                        else:
                            _LOGGER.warning(
                                "T3.2: calculate_next_recurring_datetime returned None for trip %s - day_name=%s, day_js_format=%s, time_str=%s",
                                trip.get("id"),
                                day_name,
                                day_js_format,
                                time_str,
                            )
```

### Análisis

| Aspecto | Valoración |
|---------|------------|
| **Tipo** | Código defensivo no ejecutado |
| **Alcanzable en producción** | ✅ SÍ (teóricamente) |
| **Razón de no cobertura** | `calculate_next_recurring_datetime()` casi siempre retorna un valor válido |
| **Impacto en coverage** | 7 líneas no cubiertas |

**Este NO es código muerto porque:**
1. `calculate_next_recurring_datetime()` puede retornar `None` (verificado en `calculations.py:783-786`)
2. El branch `else` (línea 250) se ejecuta cuando la función retorna `None`
3. Esto ocurre cuando la fecha de referencia ya pasó el día de la semana seleccionado

**Condición para activar este código:**
- `next_occurrence = None` de `calculate_next_recurring_datetime()`
- El trip tiene `dia_semana` y `hora` válidos
- Pero el cálculo de la próxima occurrence falla

**Por qué no se coberturó:**
- Los tests usan fechas de referencia que garantizan next occurrence válida
- El edge case de `None` requiere configurar un scenario muy específico

### Recomendación

**Mantener el código** (es defensivo válido):
- El `# pragma: no cover` sería apropiado AQUÍ
- O crear un test específico que fuerce `calculate_next_recurring_datetime` a retornar `None`
- Alternativa: simplificar el logging y asumir que siempre hay next occurrence válida

---

## CASE 3: Líneas 154-157 en `__init__.py` — Exception en hourly_refresh

### Evidencia Recolectada

**Ubicación:** [`__init__.py:152-157`](custom_components/ev_trip_planner/__init__.py:152)
```python
    async def hourly_refresh(now: datetime) -> None:
        """Hourly callback to refresh deferrable loads profile."""
        try:
            await trip_manager.publish_deferrable_loads()
        except Exception as err:
            _LOGGER.warning("Hourly profile refresh failed: %s", err)
```

### Análisis

| Aspecto | Valoración |
|---------|------------|
| **Tipo** | Código defensivo no ejecutado |
| **Alcanzable en producción** | ⚠️ CASI NUNCA |
| **Razón de no cobertura** | `publish_deferrable_loads()` tiene sus propios try/catch internos |
| **Impacto en coverage** | 4 líneas no cubiertas |

**Este código NO es código muerto, pero es extremadamente difícil de ejecutar:**
1. `publish_deferrable_loads()` en `emhass_adapter.py` tiene múltiples try/catch internos
2. Cualquier error en submódulos es atrapado antes de propagarse
3. Para que esta excepción sea alcanzable, necesitaríamos un error catastrófico no manejado

**Escenario teórico para activar:**
1. `trip_manager.publish_deferrable_loads()` lanza excepción no anticipada
2. O algún internal try/catch falla de forma inesperada
3. O hay un error de memoria/corrupción de datos

### Recomendación

**Mantener el código** (es defensivo válido):
- Es una segunda capa de protección (defense in depth)
- El `# pragma: no cover` es apropiado AQUÍ
- Alternative: usar `asyncio.shield()` o similar pattern para handle específico

---

## Resumen de Recomendaciones

| Caso | Líneas | Tipo | Acción Recomendada |
|------|--------|------|-------------------|
| CASE 1 | 211-213 (3 líneas) | **Código muerto** | **ELIMINAR** el branch `frecuencia == "daily"` completo (líneas 193-218) |
| CASE 2 | 251-260 (7 líneas) | Defensivo | **Mantener** + agregar `# pragma: no cover` o test que fuerce `None` |
| CASE 3 | 154-157 (4 líneas) | Defensivo | **Mantener** + agregar `# pragma: no cover` |

---

## Conclusión

De los 11 líneas no cubiertas:
- **3 líneas son código muerto genuino** → deben eliminarse
- **8 líneas son código defensivo válido** → deben marcarse con `# pragma: no cover`

El CASE 1 es especialmente problemático porque **el comentario `# pragma: no cover` ya existe** (línea 211), lo que indica que el desarrollador sabía que era unreachable pero eligió annotate en lugar de eliminar. Dado tu requerimiento de no usar pragmas en código muerto, **la eliminación es la acción correcta**.

La eliminación del branch `frecuencia == "daily"` no afecta funcionalidad porque:
1. Nadie crea trips con `"frecuencia"` (nunca se establece)
2. El branch semanal (líneas 220+) es el flujo activo
3. Eliminar código muerto mejora la mantenibilidad

---

*Informe generado por Mary - BMAD Business Analyst*
*Proyecto: HA EV Trip Planner | Cobertura: 99.75% → 100% (objetivo)*

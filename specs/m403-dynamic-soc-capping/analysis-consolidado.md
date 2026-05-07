# Análisis Consolidado — Spec m403-dynamic-soc-capping

**Fecha**: 2026-05-02
**Rama**: `feature-soh-soc-cap`
**Fuentes**: 3 análisis originales (analysis-report.md, analysis-deficit-implementacion-qwen.md, issues-implementacion-glm5.md)
**Verificación**: Contra código real en `custom_components/ev_trip_planner/`

---

## Resumen Ejecutivo

**El código de dynamic SOC capping está implementado correctamente como funciones aisladas, pero NUNCA fue conectado al path de producción.**

| Componente | Estado | Veredicto |
|------------|--------|----------|
| Algoritmo `calculate_dynamic_soc_limit()` | ✅ Funciona | Función pura, bien testeada, matemática correcta |
| `calculate_deficit_propagation(t_base, soc_caps)` | ✅ Funciona | Aplica caps correctamente cuando se le pasan |
| `BatteryCapacity` con SOH | ✅ Funciona | Retorna capacidad real cuando SOH está disponible |
| UI de T_BASE (slider 6-48h) | ✅ Funciona | Se almacena en config, se acepta sin errores |
| `calcular_hitos_soc()` | ❌ Código muerto | Definido en trip_manager.py:1880, **0 llamadas en producción** |
| `self._t_base` en emhass_adapter | ❌ Almacenado sin uso | Asignado en línea 128, **0 lecturas después** |
| `self._battery_cap.get_capacity()` | ❌ Aislamiento | Se llama en trip_manager.py:1929, **NO en emhass_adapter.py** |
| Path de producción | ❌ Sin capping | Usa capacidad NOMINAL, ignora T_BASE y SOC caps |

**Los 3 análisis originales están alineados en sus hallazgos. No hay contradicciones fundamentales.**

---

## Contradicciones Resueltas (Ninguna)

Los 3 documentos (`analysis-report.md`, `analysis-deficit-implementacion-qwen.md`, `issues-implementacion-glm5.md`) tienen hallazgos **consistentes**. Las diferencias son de perspectiva y detalle, no de hechos:

| Diferencia | Documento | Observación |
|------------|-----------|-------------|
| Añade contexto histórico del fallo | `analysis-deficit-implementacion-qwen.md` | Explica que external-reviewer actuó como emergency executor y marcó tasks sin implementar |
| Más técnico y específico en líneas de código | `issues-implementacion-glm5.md` | Verificación línea por línea del código |
| Primario y ligeramente menos detallado | `analysis-report.md` | Fue escrito primero, cubre lo mismo con menos profundidad |

**Ninguna contradicción requirió resolución — los 3 documentos dicen lo mismo.**

---

## Verificación Contra Código Real

### 1. `calcular_hitos_soc()` — Código Muerto

**Grep ejecutado**:
```bash
grep -rn "calcular_hitos_soc" custom_components/ev_trip_planner/*.py
```

**Resultado**: 4 hits
- `calculations.py:835` — comentario: `# PURE: Deficit propagation (core of calcular_hitos_soc)`
- `calculations.py:854` — docstring: `This is the pure core of calcular_hitos_soc`
- `trip_manager.py:75` — TypedDict docstring
- `trip_manager.py:1880` — definición de la función

**Veredicto**: CONFIRMADO — `calcular_hitos_soc()` tiene **0 callers en producción**. Solo la definición y comentarios. Las únicas llamadas son desde tests.

---

### 2. `self._t_base` — Almacenado Pero Nunca Leído

**Grep ejecutado**:
```bash
grep -rn "self._t_base" custom_components/ev_trip_planner/emhass_adapter.py
```

**Resultado**: 1 hit
- `emhass_adapter.py:128` — `self._t_base: float = entry_data.get(CONF_T_BASE, DEFAULT_T_BASE)`

**Veredicto**: CONFIRMADO — `self._t_base` se asigna en `__init__` pero **nunca se lee después**. No existe ninguna referencia a `self._t_base` en el flujo de producción.

---

### 3. `self._battery_cap.get_capacity()` — Solo en TripManager, No en EmhassAdapter

**Grep ejecutado**:
```bash
grep -rn "\.get_capacity\(" custom_components/ev_trip_planner/*.py
```

**Resultado**: 1 hit
- `trip_manager.py:1929` — `real_capacity_kwh = battery_cap.get_capacity(self.hass)`

**Veredicto**: CONFIRMADO — `self._battery_cap.get_capacity()` se llama en trip_manager.py, pero en emhass_adapter.py todas las referencias son a `self._battery_capacity_kwh` (nominal, línea 953, 976, 1039, 1058, 1064, 1080, 1268, 1320).

---

### 4. Path de Producción — Sin Capping

**Grep ejecutado**:
```bash
grep -rn "soc_caps\|dynamic_soc_limit\|calculate_dynamic_soc_limit" custom_components/ev_trip_planner/emhass_adapter.py
```

**Resultado**: 0 hits

**Veredicto**: CONFIRMADO — `emhass_adapter.py` NO tiene ninguna referencia a `soc_caps`, `dynamic_soc_limit`, ni `calculate_dynamic_soc_limit`. El path de producción no usa capping.

---

## Los Dos Paths Paralelos (Causa Raíz)

```
Path A (aislado, testeado):
┌─────────────────────────────────────────────────────────────┐
│ tests/ → calcular_hitos_soc() → calculate_deficit_propagation() │
│   soc_caps calculado ✅  t_base usado ✅  capping aplicado ✅   │
└─────────────────────────────────────────────────────────────┘

Path B (producción, desconectado):
┌─────────────────────────────────────────────────────────────┐
│ publish_deferrable_loads() → async_publish_all_deferrable_loads() │
│   → determine_charging_need() — usa NOMINAL (no soc_caps)    │
│   → _populate_per_trip_cache_entry() — usa NOMINAL (no soc_caps)│
│   → _calculate_power_profile_from_trips() — usa NOMINAL      │
└─────────────────────────────────────────────────────────────┘
```

La spec pedía que Path B usara los resultados del Path A. La implementación creó Path A con capping pero dejó Path B sin modificar.

---

## Evidencia Específica por Componente

### Algoritmo — FUNCIONA

| Función | Archivo | Línea | Estado |
|---------|---------|-------|--------|
| `calculate_dynamic_soc_limit()` | `calculations.py` | 124 | ✅ Fórmula correcta: `risk = t_hours * (soc_post_trip - 35) / 65` |
| `calculate_deficit_propagation()` | `calculations.py` | 849 | ✅ Firma: `(trips, t_base=24.0, soc_caps=None)` |
| Backward loop aplica cap | `calculations.py` | ~808 | ✅ `min(soc_objetivo_ajustado, soc_caps[idx])` |
| Forward loop aplica cap | `calculations.py` | ~843 | ✅ Mismo cap en loop de resultados |
| `BatteryCapacity.get_capacity()` | `calculations.py` | 56 | ✅ SOH-aware, 5-min cache, hysteresis |

### Configuración UI — FUNCIONA

| Componente | Archivo | Línea | Estado |
|------------|---------|-------|--------|
| T_BASE en options flow | `config_flow.py` | 978-979 | ✅ Se almacena en `entry.options` |
| T_BASE slider (6-48h) | `config_flow.py` | 125-128 | ✅ Visible en UI |
| SOH sensor selector | `config_flow.py` | ~129 | ✅ Selector de entidad HA |
| Migration v2→v3 | `config_flow.py` | `async_migrate_entry` | ✅ CONFIG_VERSION = 3 |

### EmhassAdapter — ALMACENADO SIN USAR

| Atributo | Archivo | Línea | Estado |
|----------|---------|-------|--------|
| `self._t_base` almacenamiento | `emhass_adapter.py` | 128 | ✅ Almacenado |
| `self._t_base` lectura | — | — | ❌ **0 lecturas** |
| `self._battery_cap` almacenamiento | `emhass_adapter.py` | 130-132 | ✅ Creado |
| `self._battery_cap.get_capacity()` en producción | — | — | ❌ **Solo en trip_manager.py:1929** |
| `_handle_config_entry_update()` reacciona a t_base | `emhass_adapter.py` | 2228 | ❌ Solo reacciona a `charging_power_kw` |

### Tests — PASAN PERO NO TESTEAN INTEGRACIÓN

| Test | Archivo | Verifica | Limitación |
|------|---------|----------|------------|
| Unit tests (24) | `test_dynamic_soc_capping.py` | Función pura aislada | No integra con EMHASS |
| Unit tests (20) | `test_soc_milestone.py` | Función pura aislada | No integra con EMHASS |
| E2E tests (7) | `test-dynamic-soc-capping.spec.ts` | `nonZeroHours >= 1` | Pasa con o sin T_BASE |

---

## Análisis de la Cadena de Spec

| Documento | Veredicto | Detalle |
|-----------|-----------|---------|
| `research.md` | ✅ CORRECTO | Identificó 4 integration points exactos |
| `research-codebase.md` | ✅ CORRECTO | Mapeó 7 puntos de integración con líneas |
| `requirements.md` | ✅ CORRECTO | US-5: "Use dynamic SOC limit in EMHASS charging decisions" |
| `design.md` | ✅ CORRECTO | Component 6/7 diseñó cambios en EMHASS Adapter |
| `spec.md` | ✅ CORRECTO | Sección "Integration with Deficit Propagation" completa |
| `tasks.md` | ⚠️ INCOMPLETO | T059-T062 existen pero verificación insuficiente |

**La cadena de spec (research → requirements → design → tasks) es CORRECTA. El fallo fue en la implementación y verificación de T059-T062.**

---

## Punto de Fallencia Específico

### Tasks T059-T062 — Marcadas como ✅ sin implementación real

**T059**: "thread t_base and BatteryCapacity through `_calculate_power_profile_from_trips()`"
- Lo que se hizo: `self._t_base` y `self._battery_cap` almacenados en `__init__` (líneas 127-132)
- Lo que se debía hacer: Pasar `t_base` y capacidad real a las funciones llamadas desde `_calculate_power_profile_from_trips()`
- Verificación hecha: Solo se verificó que el atributo existe, no que se usa

**T060**: "pass real_capacity from BatteryCapacity.get_capacity(hass)"
- Lo que se hizo: `_battery_cap` creado en `__init__`
- Lo que se debía hacer: Reemplazar `self._battery_capacity_kwh` con `self._battery_cap.get_capacity(self.hass)` en líneas 953, 976, 1039, 1080, 1268, 1320
- Verificación hecha: El atributo existe, pero no se llama `.get_capacity()`

**T061**: "pass real_capacity as battery_capacity_kwh to downstream functions"
- Lo que se hizo: `_battery_cap` almacenado
- Lo que se debía hacer: Todas las llamadas del path de producción usan `self._battery_capacity_kwh` (nominal)
- Verificación hecha: No se ejecutó grep para verificar que los calls usan `self._battery_cap.get_capacity()`

**T062**: "Wire t_base from config entry through async_generate_power_profile() → calcular_hitos_soc() → calculate_deficit_propagation()"
- Lo que se hizo: `calcular_hitos_soc()` definido en trip_manager.py:1880
- Lo que se debía hacer: Llamar `calcular_hitos_soc()` desde el entry point de producción
- Verificación hecha: `calcular_hitos_soc()` tiene 0 callers, no se llama desde `publish_deferrable_loads()`

---

## Wiring Pendiente (Lo que Falta)

### 1. Llamar `calcular_hitos_soc()` en el path de producción

**Ubicación**: `emhass_adapter.async_publish_all_deferrable_loads()` (~línea 948)
**Cambio**: Pre-computar `soc_caps` antes de `determine_charging_need()`:
```python
# Antes de línea 948
soc_milestone_result = await self._trip_manager.calcular_hitos_soc(trips)
soc_caps = soc_milestone_result.get("soc_caps", None)
```

### 2. Pasar `soc_caps` al path de decisión de carga

**Ubicación**: `determine_charging_need()` (línea 975), `calculate_hours_deficit_propagation()` (línea 993)
**Cambio**: Añadir parámetro `soc_caps` a estas funciones o usar el resultado de `calcular_hitos_soc()` para limitar `soc_objetivo`

### 3. Usar `self._battery_cap.get_capacity()` en lugar de capacidad nominal

**Ubicación**: 12+ líneas en `emhass_adapter.py` que usan `self._battery_capacity_kwh`
**Cambio**: Reemplazar con `self._battery_cap.get_capacity(self.hass)`:
- Línea 953: `battery_capacity_kwh=self._battery_cap.get_capacity(self.hass)`
- Línea 976: `self._battery_cap.get_capacity(self.hass)`
- Línea 1039: `self._battery_cap.get_capacity(self.hass)`
- Línea 1080: `self._battery_cap.get_capacity(self.hass)`
- Línea 1268: `self._battery_cap.get_capacity(self.hass)`
- Línea 1320: `self._battery_cap.get_capacity(self.hass)`

### 4. `_handle_config_entry_update()` debe reaccionar a cambios de T_BASE

**Ubicación**: `emhass_adapter.py:2228`
**Cambio**: Añadir condición para re-publicar cuando `t_base` cambia, no solo cuando `charging_power_kw` cambia

### 5. Tests de integración

**Lo que falta**: Tests que verifiquen que T_BASE=6h produce resultados distintos a T_BASE=48h, y que el SOC objetivo está capped

---

## Lección para el Proceso

El gate de calidad debe verificar **"uso en producción"** no **"disponibilidad"**:

| Incorrecto | Correcto |
|------------|----------|
| "_battery_cap available for all methods" | "async_publish_all_deferrable_loads() usa self._battery_cap.get_capacity() en línea X" |
| "t_base stored in emhass_adapter.__init__" | "t_base se pasa a calcular_hitos_soc() y el resultado se usa en determine_charging_need() en línea Y" |
| "calcular_hitos_soc() exists" | "calcular_hitos_soc() es llamado desde publish_deferrable_loads()" |

---

## Conclusión

La spec m403-dynamic-soc-capping implementó correctamente:
- ✅ El algoritmo de capping (matemática verificada)
- ✅ La UI de configuración (T_BASE slider)
- ✅ La integración de SOH (BatteryCapacity)
- ✅ Los unit tests de funciones aisladas

La spec FALLÓ en:
- ❌ Conectar el algoritmo al path de producción (T059-T062)
- ❌ Usar `self._battery_cap.get_capacity()` en emhass_adapter.py
- ❌ Verificar que `calcular_hitos_soc()` se llama desde producción
- ❌ Tests E2E que verifiquen efecto de T_BASE

**La cadena de spec era correcta. El fallo fue implementación y verificación insuficiente de T059-T062.**
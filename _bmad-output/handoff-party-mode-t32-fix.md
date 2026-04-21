# Handoff: Fixes Bloqueantes del Party Mode

## Fuente: bmad-checkpoint-preview — Paso 3 (Party Mode)
**Fecha:** 2026-04-21
**Agentes participantes:** 🏗️ Winston (Architect), 💻 Amelia (Developer), 🧪 Murat (Test Architect)

---

## Resumen Ejecutivo

El checkpoint-preview identificó 2 riesgos. **Solo 1 es bloqueante pre-merge: T3.2 Timezone Naive.**

| Riesgo | Estado | Acción |
|--------|--------|--------|
| EC-020 Partial Rollback | ✅ APROBADO | No necesita cambios |
| **T3.2 Timezone Naive** | **❌ BLOQUEANTE** | **Fix obligatorio pre-merge** |
| Sistémico `datetime.now()` | ⚠️ Tech debt | Refactor post-merge |

---

## 🔴 ACCIÓN BLOQUEANTE: T3.2 Timezone Naive

### Problema

`trip_manager.py` usa `datetime.now()` (naive) en 10 ubicaciones. El coordinator usa `datetime.now(timezone.utc)` (aware). Python 3 **no permite restar datetime aware contra naive** → `TypeError: can't subtract naive and aware datetimes`.

### Impacto

- **Crash determinístico** para cualquier usuario con trips recurrentes
- Se ejecuta en [`trip_manager.py:206`](custom_components/ev_trip_planner/trip_manager.py:206) durante rotación de trips recurrentes
- El crash se propaga al calcular power profile en [`emhass_adapter.py:363`](custom_components/ev_trip_planner/emhass_adapter.py:363)

### 10 ubicaciones de `datetime.now()` en trip_manager.py

| Línea | Función | Severidad |
|-------|---------|-----------|
| **206** | `calculate_next_recurring_datetime()` | **ALTA** — bloqueante |
| 480 | `async_save_trips()` | MEDIA — potencial conflicto |
| 539 | `get_next_scheduled_trip()` | MEDIA — potencial conflicto |
| 1157 | `async_get_energy_for_today()` | BAJA — cálculo interno |
| 1253 | `async_get_next_scheduled_trip()` | MEDIA — potencial conflicto |
| 1354 | `async_calculate_optimization_params()` | MEDIA — potencial conflicto |
| 1457 | `async_calculate_soc_planning()` | BAJA — cálculo interno |
| 1903 | (función no identificada) | MEDIA — potencial conflicto |
| 2004 | (función no identificada) | MEDIA — potencial conflicto |
| 2060 | (función no identificada) | MEDIA — potencial conflicto |

### Fix Mínimo (bloqueante pre-merge)

**Archivo:** [`trip_manager.py:12`](custom_components/ev_trip_planner/trip_manager.py:12)
```python
# CAMBIO 1 — Agregar timezone al import
from datetime import date, datetime, timedelta, timezone
```

**Archivo:** [`trip_manager.py:206`](custom_components/ev_trip_planner/trip_manager.py:206)
```python
# CAMBIO 2 — Cambiar naive → aware
# ANTES:
next_occurrence = calculate_next_recurring_datetime(
    day_js_format, time_str, datetime.now()
)

# DESPUÉS:
next_occurrence = calculate_next_recurring_datetime(
    day_js_format, time_str, datetime.now(timezone.utc)
)
```

### Fix Completo (recomendado por Amelia)

Las 10 ocurrencias de `datetime.now()` deberían cambiarse a `datetime.now(timezone.utc)` para consistencia. **Prioridad:** líneas 206, 480, 539, 1253, 1354 (las que hacen comparación con deadlines del coordinator).

### Test de Integración Necesario

Amelia identificó 2 tests adicionales necesarios:

1. **T3.2-integration:** Test que cree un trip recurrente real, invoque `publish_deferrable_loads()` y verifique que `calculate_next_recurring_datetime` recibe un datetime aware (usar `side_effect` para inspeccionar el argumento `ref_dt`).

2. **T3.2-conflict:** Test que simule el coordinator (`datetime.now(timezone.utc)`) llamando a un callback que use `trip_manager` con trips recurrentes — verificar que no lanza `TypeError: can't subtract aware and naive datetimes`.

**Archivo existente de tests:** [`tests/test_edge_cases_ec003_ec020_t32.py`](tests/test_edge_cases_ec003_ec020_t32.py)

---

## 🟡 TECH DEBT: Sistémico `datetime.now()`

### Recomendación de Murat

Crear helper centralizado `_now_utc()` en un módulo de utilidades:

```python
def _now_utc() -> datetime:
    """Return current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)
```

Reemplazar todas las ocurrencias de `datetime.now()` por `_now_utc()`. Esto previene futuros bugs de mezcla naive/aware.

---

## ✅ NO NECESITA CAMBIOS: EC-020 Partial Rollback

Winston identificó un problema de rollback parcial, pero Amelia confirmó que el fix **ya está aplicado**:

- [`emhass_adapter.py:770`](custom_components/ev_trip_planner/emhass_adapter.py:770) — `exception_trip_ids = []`
- [`emhass_adapter.py:771-790`](custom_components/ev_trip_planner/emhass_adapter.py:771) — try/catch por trip
- [`emhass_adapter.py:801-817`](custom_components/ev_trip_planner/emhass_adapter.py:801) — rollback bloque completo
- **8 tests existentes** en [`tests/test_missing_coverage.py`](tests/test_missing_coverage.py:128) + [`tests/test_edge_cases_ec003_ec020_t32.py`](tests/test_edge_cases_ec003_ec020_t32.py:176)
- **Riesgo de regresión:** Nulo

---

## Confianza de los Agentes

| Riesgo | Confianza | Blocking? |
|--------|-----------|-----------|
| EC-020 (rollback) | 8/10 | NO |
| T3.2 (timezone naive) | 3/10 | **SÍ** |
| Sistémico `datetime.now()` | 0/10 | NO |

---

## Decisiones del Party Mode

> **Winston:** "T3.2 es bloqueante: crash funcional para cualquier usuario con trips recurrentes. EC-020 es consistencia acumulativa que eventualmente causa denial of service (agotamiento de índices). **Recomendación arquitectónica: no merge hasta que ambos estén resueltos.**"

> **Amelia:** "no merge hasta que T3.2 línea 206 esté fixeado + test de integración añadido."

> **Murat:** "T3.2: ❌ BLOCKED — 3/10 confianza, SÍ blocking."

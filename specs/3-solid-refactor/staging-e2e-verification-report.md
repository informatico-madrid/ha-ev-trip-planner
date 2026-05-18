# Staging E2E Verification Report

**Fecha:** 2026-05-12
**Entorno:** Staging Docker (localhost:8124)
**Estado:** Problema identificado — EMHASS indices agotados bloquean test Scenario C

---

## Resumen Ejecutivo

El test e2e-dynamic-soc (Scenario C: 4 daily commutes at T_BASE=24h) no pasa porque el EMHASS adapter tiene los índices agotados. El vehículo "Mi EV" en staging tiene configurado un cargador de 3.6kW, pero los tests SOC esperan 11kW. Esto causa que solo 1 de 4 trips получит datos de carga.

**Diferencia crítica entre E2E y Staging:**
- **E2E** (`make e2e` → :8123): Vehículo `test_vehicle` con `charging_power_kw=11` — usa mock EMHASS (ilimitado)
- **Staging** (Docker :8124): Vehículo `Mi EV` con `charging_power_kw=3.6` — usa EMHASS real (índices agotados)

---

## Problemas Detectados

### 🔴 CRÍTICO: Test 4 (Scenario C) falla por EMHASS indices agotados

**Descripción:** El test crea 4 trips idénticos diarios pero solo 1 получит datos de carga.

**Datos observados en staging:**
- `def_total_hours_array: [0, 3, 0]` — solo el trip #1 tiene horas de carga (3h)
- `p_deferrable_nom_array: [0, 3600, 0]` — solo el trip #1 tiene potencia (3.6kW = charger del vehículo staging)
- `power_profile_watts` — mayoría ceros, un solo valor 3600W

**Causa raíz:** Error en el EMHASS adapter:
```
No available EMHASS indices for vehicle Mi EV. Max deferrable loads: 50, currently used: 2
```

Hay 5 trips activos (3 recurrentes + 2 puntual) pero solo 2 slots de índice en uso. Los otros 3 trips no pueden obtener índice y no publican sus datos.

**Datos de trips en staging:**
- `punctual_trips_count: 2`
- `recurring_trips_count: 1`
- **Total: 5 trips**

**Vehículo en staging vs E2E:**

| Aspecto | E2E (:8123) `test_vehicle` | Staging (:8124) `Mi EV` |
|---------|----------------------------|--------------------------|
| charging_power_kw | **11** | **3.6** |
| Modo EMHASS | Mock (ilimitado) | Real (50 slots máx) |
| EMHASS indices usados | ∞ | 2 de 50 |
| Trips procesables | 4+ | 2 (bloqueado) |

### 🔴 CRÍTICO: Panel no carga — "ev-trip-planner-panel already been used"

**Descripción:** Error en el navegador Chrome cuando se intenta cargar el panel del plugin:
```
Error: Failed to execute 'define' on 'CustomElementRegistry': 
the name "ev-trip-planner-panel" has already been used with this registry
```

**URL afectada:** `http://localhost:8124/ev-trip-planner-mi_ev`

**Causa:** Cuando HA recarga el custom component durante el desarrollo, el archivo `panel.js` se carga pero `customElements.define()` falla porque el custom element ya fue registrado en una carga anterior. Esto es un problema de hot-reload en HA que afecta a todos los custom components durante el desarrollo.

**Impacto:** 
- El panel muestra una página en blanco con el logo de HA
- Los tests E2E que usan navegación directa por URL (`page.goto('/ev-trip-planner-mi_ev')`) fallarán
- La navegación por sidebar también falla porque HA intenta cargar el mismo panel

**Solución temporal:** Reiniciar el contenedor Docker elimina el problema hasta que se recargue el código:
```bash
docker restart ha-staging
```

---

### 🟡 WARNING: EMHASS indices agotados

**Descripción:** Cada hora aparece el error:
```
ERROR (MainThread) [custom_components.ev_trip_planner.emhass_adapter] 
No available EMHASS indices for vehicle Mi EV. Max deferrable loads: 50, currently used: 2
```

**Causa:** El EMHASS adapter tiene un límite de 50 slots de deferrable loads. Solo 2 están marcados como "en uso", pero 5 trips necesitan índice. Los 3 trips restantes no publican sus datos de carga.

**Impacto:** El scheduling de carga no funciona para trips que no obtienen índice EMHASS.

---

## Diagnóstico: Por qué solo 1 trip tiene datos

El sensor EMHASS muestra `def_total_hours_array: [0, 3, 0]` porque:

1. Trip #0 (`rec_0_qlesa2`): Obtuvo índice, но **0 horas** (posiblemente no necesita carga)
2. Trip #1: Obtuvo índice, **3 horas** de carga a 3.6kW
3. Trip #2: **Sin índice** — no puede publicar datos

El `p_deferrable_nom_array: [0, 3600, 0]` confirma que solo trip #1 tiene datos: 3600W = charger del vehículo Mi EV (3.6kW).

**Esto es consistente con un vehículo de 3.6kW, NO de 11kW.**

---

## Tareas recomendadas

### [TODO] Investigar EMHASS adapter — índice no se libera correctamente

**Archivo:** `custom_components/ev_trip_planner/emhass_adapter.py` (o módulo emhass/)
**Síntoma:** Mensaje "No available EMHASS indices" cuando hay slots disponibles (50 - 2 = 48 libres)

**Pasos:**
1. Buscar dónde se marca un índice como "usado"
2. Buscar dónde se libera un índice (en trip deletion o completion)
3. Verificar que el límite de 50 no se alcanza por old stale entries

### [TODO] Verificar potencia de vehículo en staging — ¿3.6kW o 11kW?

**Archivo:** `staging/configuration.yaml` o datos del config flow
**Verificar:** charging_power_kw del vehículo Mi EV

### [TODO] Confirmar que tests E2E usan vehículo con 11kW

**Archivo:** `auth.setup.soc.ts`, `playwright.soc.config.ts`
**Verificar:** El vehículo `test_vehicle` tiene `charging_power_kw: 11` y usa mock EMHASS

---

## Siguientes Pasos

1. [ ] Investigar código del EMHASS adapter para entender cómo se asignan/libertan índices
2. [ ] Limpiar archivos `*.py,cover` en staging antes de siguientes pruebas
3. [ ] Verificar si el test Scenario C pasa en E2E (no en staging) usando `make e2e-soc`
4. [ ] Documentar el límite de EMHASS indices como feature, no bug

---

**Nota:** Los tests E2E en `tests/e2e-dynamic-soc/` NUNCA deben ejecutarse en staging. Son para el entorno E2E (`:8123`) donde el vehículo `test_vehicle` con 11kW y mock EMHASS garantiza datos consistentes.
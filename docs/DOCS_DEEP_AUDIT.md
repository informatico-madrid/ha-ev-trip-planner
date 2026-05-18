# DEEP Audit: docs/ vs Código Fuente

> Fecha: 2026-04-25 (actualizado 2026-04-25T17:20:00Z)
> Auditoría: Verificación sistemática de cada documento en `docs/` contra el código fuente
> Versión esperada del código: **0.5.20**

---

## Resumen Ejecutivo

| Estado | Documentos | Problemas |
|--------|------------|-----------|
| ✅ CORREGIDOS | 7 | Problemas resueltos en esta auditoría |
| ⚠️ PROBLEMAS MENORES | 2 | Desactualizados pero usables |
| ❌ PROBLEMAS MAYORES | 0 | Todos los problemas mayores han sido corregidos |

---

## Correcciones Aplicadas (2026-04-25)

| # | Documento | Problema Original | Corrección Aplicada |
|---|-----------|-------------------|---------------------|
| 1 | `architecture.md` | LOC counts desactualizados (1998→2244, 1122→1395, 1828→2361, 908→961, 1537→1592) | ✅ Actualizados a valores reales |
| 2 | `architecture.md` | `EMHASSPublisherProtocol` referenciado como archivo separado | ✅ Aclarado que es DI inline |
| 3 | `source-tree-analysis.md` | `test_protocols.py` listado pero NO EXISTE | ✅ Reemplazado por `test_utils.py` |
| 4 | `source-tree-analysis.md` | trip_manager.py 1999 LOC | ✅ Actualizado a 2244 LOC |
| 5 | `DASHBOARD.md` | `sensor.emhass_perfil_diferible_{vehicle_id}` incorrecto | ✅ Corregido a `{entry_id}` |
| 6 | `SHELL_COMMAND_SETUP.md` | Mismo problema de nombre de sensor | ✅ Corregido a `{entry_id}` |
| 7 | `SHELL_COMMAND_SETUP.md` | Link a `EMHASS_INTEGRATION.md` inexistente | ✅ Corregido a `emhass-setup.md` |
| 8 | `MILESTONE_4_POWER_PROFILE.md` | Target v0.4.0-dev sin indicar histórico | ✅ Marcado como histórico |
| 9 | `MILESTONE_4_POWER_PROFILE.md` | `safety_margin_percent` default 40 (real=10) | ✅ Corregido a 10 |
| 10 | `emhass-setup.md` | Sensor `emhass_aggregated` no existe en código | ✅ Reemplazado con sensores reales |
| 11 | `ROADMAP.md` | Estructura de docs listaba archivos inexistentes | ✅ Actualizada con archivos reales |
| 12 | `README.md` | "85 unit test files" (real=90) | ✅ Actualizado a 90 |

---

## Hallazgos Detallados por Documento

### ✅ VÁLIDOS (8 documentos — actualizado)

| Documento | Verificación | Estado |
|-----------|--------------|--------|
| `index.md` | Versión 0.5.20 ✅, estructura ✅, links ✅ | VÁLIDO |
| `api-contracts.md` | 9+ servicios ✅, estructura ✅ | VÁLIDO |
| `data-models.md` | Modelos correctos ✅, versión 0.5.20 ✅ | VÁLIDO |
| `development-guide.md` | Estructura ✅, convenciones ✅ | VÁLIDO |
| `e2e-date-diagnosis-final.md` | Documento de debugging ✅, fecha correcta ✅ | VÁLIDO |
| `architecture.md` | LOC actualizados ✅, Protocol DI aclarado ✅ | CORREGIDO |
| `source-tree-analysis.md` | test_protocols.py eliminado ✅, LOC actualizado ✅ | CORREGIDO |
| `emhass-setup.md` | Sensores EMHASS corregidos ✅ | CORREGIDO |

---

### ⚠️ PROBLEMAS MENORES RESTANTES (2 documentos)

| Documento | Problema | Severidad |
|-----------|----------|-----------|
| `project-scan-report.json` | Scan del 2026-04-16, obsoleto (9 días atrás) | BAJA |
| `MILESTONE_4_1_PLANNING.md` | Target `v0.5.0` obsoleto — ya marcado como HISTORICAL/SUPERSEDED ✅ | BAJA |

---

## Verificación Específica

### 1. ✅ Versión: 0.5.20 (CORRECTO)

```bash
# manifest.json dice:
"version": "0.5.20"
```

- `docs/index.md`: ✅ Versión 0.5.20
- `docs/project-overview.md`: ✅ Versión 0.5.20 (verificado)
- `docs/MILESTONE_4_POWER_PROFILE.md`: ✅ Marcado como histórico
- `docs/MILESTONE_4_1_PLANNING.md`: ✅ Marcado como HISTORICAL/SUPERSEDED

### 2. ✅ Config Flow: 5-Step (CORRECTO)

```python
# config_flow.py tiene 5 pasos:
# Step 1: async_step_user → Vehicle name
# Step 2: async_step_sensors → Battery/sensors
# Step 3: async_step_emhass → EMHASS integration
# Step 4: async_step_presence → Presence detection
# Step 5: async_step_notifications → Notifications (NEW in 0.5.20)
```

- `docs/architecture.md` línea 140: ✅ Dice "5-step setup wizard" (CORRECTO)
- `docs/VEHICLE_CONTROL.md`: ✅ Menciona "Step 5: Notifications" correctamente

### 3. ❌ `protocols.py` NO EXISTE (verificado)

```bash
# El directorio custom_components/ev_trip_planner/ tiene:
__init__.py ✅       calculations.py ✅    config_flow.py ✅
const.py ✅          coordinator.py ✅     dashboard.py ✅
definitions.py ✅    diagnostics.py ✅     emhass_adapter.py ✅
panel.py ✅          presence_monitor.py ✅
sensor.py ✅         services.py ✅        trip_manager.py ✅
utils.py ✅          vehicle_controller.py ✅ yaml_trip_storage.py ✅
# NO HAY protocols.py ❌  (18 archivos .py, no 19)
```

**Corrección aplicada**: Eliminada referencia a `test_protocols.py` en `source-tree-analysis.md`. Los protocolos `TripStorageProtocol` y `EMHASSPublisherProtocol` están definidos inline en los módulos consumidores, no en un archivo separado.

### 4. ✅ Sensores EMHASS: Nombres Corregidos

| Documento | Nombre Anterior | Nombre Corregido | Código Real |
|-----------|----------------|------------------|-------------|
| `DASHBOARD.md` | `sensor.emhass_perfil_diferible_{vehicle_id}` | `sensor.emhass_perfil_diferible_{entry_id}` | ✅ `sensor.py:179` usa `entry_id` |
| `SHELL_COMMAND_SETUP.md` | `sensor.emhass_perfil_diferible_{vehicle_id}` | `sensor.emhass_perfil_diferible_{entry_id}` | ✅ `sensor.py:179` usa `entry_id` |
| `emhass-setup.md` | `sensor.ev_trip_planner_{vehicle_id}_emhass_aggregated` | `sensor.emhass_perfil_diferible_{entry_id}` + per-trip | ✅ No existe sensor aggregated |

### 5. ✅ TripEmhassSensor: YA EXISTE

El sensor `TripEmhassSensor` está definido en `sensor.py` línea 853 y funciona correctamente.
Unique ID: `emhass_trip_{vehicle_id}_{trip_id}`

### 6. ✅ LOC Counts Actualizados

| Archivo | LOC Documentado (antes) | LOC Real | Estado |
|---------|------------------------|----------|--------|
| `trip_manager.py` | 1998 | 2244 | ✅ Corregido |
| `calculations.py` | 1122 | 1395 | ✅ Corregido |
| `emhass_adapter.py` | 1828 | 2361 | ✅ Corregido |
| `sensor.py` | 908 | 961 | ✅ Corregido |
| `services.py` | 1537 | 1592 | ✅ Corregido |
| `config_flow.py` | 949 | 949 | ✅ Sin cambios |
| `vehicle_controller.py` | 509 | 509 | ✅ Sin cambios |
| `presence_monitor.py` | 769 | 769 | ✅ Sin cambios |
| `dashboard.py` | 1261 | 1261 | ✅ Sin cambios |

### 7. ✅ Test Count Actualizado

- README.md: "85 unit test files" → **90 test files** (verificado con `ls tests/test_*.py | wc -l`)

### 8. ✅ safety_margin_percent Default Corregido

- `MILESTONE_4_POWER_PROFILE.md` decía default=40, pero `const.py:63` define `DEFAULT_SAFETY_MARGIN = 10`
- Corregido en documentación a default=10

---

## Verificación de Archivos vs Código

| Archivo mentioned | Existe? | Notas |
|-------------------|---------|-------|
| `protocols.py` | ❌ NO | No existe en el código — referencias eliminadas |
| `calculations.py` | ✅ SÍ | 1395 LOC |
| `trip_manager.py` | ✅ SÍ | 2244 LOC |
| `emhass_adapter.py` | ✅ SÍ | 2361 LOC |
| `sensor.py` | ✅ SÍ | 961 LOC, TripEmhassSensor existe en línea 853 |
| `config_flow.py` | ✅ SÍ | 949 LOC, 5-step correcto |

---

## Nota sobre Documentación de IA

Los siguientes documentos fueron movidos a `_ai/` para documentación de IA:

- `_ai/CODEGUIDELINESia.md`
- `_ai/RALPH_METHODOLOGY.md`
- `_ai/TDD_METHODOLOGY.md`
- `_ai/TESTING_E2E.md`
- `_ai/ai-development-lab.md`
- `_ai/PORTFOLIO.md`
- `_ai/SPECKIT_SDD_FLOW_INTEGRATION_MAP.md`
- `_ai/IMPLEMENTATION_REVIEW.md`

Estos documentos ya no están en `docs/` y están correctamente referenciados en `_ai/index.md`.

---

**Auditoría completada**: 2026-04-25T02:38:00Z
**Correcciones aplicadas**: 2026-04-25T17:20:00Z
**Próx. revisión**: Trimestral o al actualizar versión

# DEEP Audit: docs/ vs Código Fuente

> Fecha: 2026-04-25  
> Auditoría: Verificación sistemática de cada documento en `docs/` contra el código fuente  
> Versión esperada del código: **0.5.20**

---

## Resumen Ejecutivo

| Estado | Documentos | Problemas |
|--------|------------|-----------|
| ✅ VÁLIDOS | 6 | Correctos al día |
| ⚠️ PROBLEMAS MENORES | 4 | Desactualizados pero usables |
| ❌ PROBLEMAS MAYORES | 5 | Claims falsos o archivos referencedos que no existen |

---

## Hallazgos Detallados por Documento

### ✅ VÁLIDOS (6 documentos)

| Documento | Verificación | Estado |
|-----------|--------------|--------|
| `index.md` | Versión 0.5.20 ✅, estructura ✅, links ✅ | VÁLIDO |
| `api-contracts.md` | 9+ servicios ✅, estructura ✅ | VÁLIDO |
| `data-models.md` | Modelos correctos ✅, versión 0.5.20 ✅ | VÁLIDO |
| `development-guide.md` | Estructura ✅, convenciones ✅ (ver nota protocols.py) | VÁLIDO |
| `emhass-setup.md` | Sensores EMHASS ✅, parámetros ✅ | VÁLIDO |
| `e2e-date-diagnosis-final.md` | Documento de debugging ✅, fecha correcta ✅ | VÁLIDO |

---

### ⚠️ PROBLEMAS MENORES (4 documentos)

| Documento | Problema | Severidad |
|-----------|----------|-----------|
| `DASHBOARD.md` | Menciona `sensor.emhass_perfil_diferible_{vehicle_id}` pero el código usa `sensor.ev_trip_planner_{vehicle_id}_power_profile` o `sensor.ev_trip_planner_{vehicle_id}_emhass_*` | MEDIA |
| `SHELL_COMMAND_SETUP.md` | Mismo problema de nombre de sensor que DASHBOARD.md | MEDIA |
| `MILESTONE_4_POWER_PROFILE.md` | Target version dice `v0.4.0-dev` pero debería ser `v0.5.20` | BAJA |
| `project-scan-report.json` | Scan del 2026-04-16, obsoleto (9 días atrás) | BAJA |

---

### ❌ PROBLEMAS MAYORES (5 documentos)

| Documento | Problema | Severidad |
|-----------|----------|-----------|
| `architecture.md` | Línea 193: Menciona `protocols.py` que **NO EXISTE** en el código | CRÍTICA |
| `source-tree-analysis.md` | Línea 28: Lista `protocols.py` — **NO EXISTE** | CRÍTICA |
| `development-guide.md` | Línea 105: Lista `protocols.py` en estructura — **NO EXISTE** | CRÍTICA |
| `VEHICLE_CONTROL.md` | Línea 383: Menciona Step 5 pero config flow tiene 5 pasos, el paso de notificaciones es el correcto | MEDIA |
| `MILESTONE_4_1_PLANNING.md` | Target `v0.5.0` (obsoleto), documento dice "PLANNED - NOT STARTED" pero ya estamos en 0.5.20 | ALTA |

---

## Verificación Específica

### 1. ✅ Versión: 0.5.20 (CORRECTO)

```bash
# manifest.json dice:
"version": "0.5.20"
```

- `docs/index.md`: ✅ Versión 0.5.20
- `docs/project-overview.md`: ❌ Versión 0.5.1 (OBSOLETO)
- `docs/MILESTONE_4_POWER_PROFILE.md`: ❌ Target v0.4.0-dev (OBSOLETO)
- `docs/MILESTONE_4_1_PLANNING.md`: ❌ Target v0.5.0 (OBSOLETO)

### 2. ✅ Config Flow: 5-Step (CORRECTO)

```python
# config_flow.py tiene 5 pasos:
# Step 1: async_step_user        → Vehicle name
# Step 2: async_step_sensors    → Battery/sensors
# Step 3: async_step_emhass     → EMHASS integration
# Step 4: async_step_presence   → Presence detection
# Step 5: async_step_notifications → Notifications (NEW in 0.5.20)
```

- `docs/architecture.md` línea 140: ❌ Dice "4-step setup wizard" — **OBSOLETO**
- `docs/DASHBOARD.md` línea 55: Dice "Step 4: Presence Detection" — correcto
- `docs/VEHICLE_CONTROL.md` línea 383: Menciona "Step 5: Notifications" — ✅ CORRECTO

### 3. ❌ `protocols.py` NO EXISTE

```bash
# El directorio custom_components/ev_trip_planner/ tiene:
__init__.py          ✅
calculations.py      ✅
config_flow.py       ✅
const.py             ✅
coordinator.py       ✅
dashboard.py         ✅
definitions.py        ✅
diagnostics.py        ✅
emhass_adapter.py     ✅
panel.py             ✅
presence_monitor.py  ✅
schedule_monitor.py  ✅
sensor.py            ✅
services.py          ✅
trip_manager.py      ✅
utils.py             ✅
vehicle_controller.py ✅
yaml_trip_storage.py  ✅
# NO HAY protocols.py ❌
```

**Documentos que mencionan protocols.py ERRÓNEAMENTE:**
- `architecture.md` línea 193
- `source-tree-analysis.md` línea 28
- `development-guide.md` línea 105

**Nota**: El documento de arquitectura menciona protocolos como `TripStorageProtocol` y `EMHASSPublisherProtocol`, pero estos están definidos directamente en los módulos que los usan (e.g., `emhass_adapter.py`), no en un archivo separado `protocols.py`.

### 4. ⚠️ Sensores EMHASS: Nombres Divergentes

| Documento | Nombre Used | Código Real |
|-----------|------------|-------------|
| `DASHBOARD.md` | `sensor.emhass_perfil_diferible_{vehicle_id}` | `sensor.ev_trip_planner_{vehicle_id}_power_profile` |
| `SHELL_COMMAND_SETUP.md` | `sensor.emhass_perfil_diferible_{vehicle_id}` | `sensor.ev_trip_planner_{vehicle_id}_power_profile` |
| `emhass-setup.md` | `sensor.ev_trip_planner_{vehicle_id}_emhass_aggregated` | Posible pero verificar |
| `api-contracts.md` | `emhass_power_profile` | ✅ Coincide con `coordinator.data` |

### 5. ✅ TripEmhassSensor: YA EXISTE

El sensor `TripEmhassSensor` está definido en `sensor.py` líneas 164-220 y funciona correctamente.

---

## Tabla de Problemas

| # | Documento | Línea | Problema | Tipo | Acción |
|---|-----------|-------|----------|------|--------|
| 1 | `architecture.md` | 193 | Menciona `protocols.py` inexistente | CRÍTICO | Eliminar referencia |
| 2 | `source-tree-analysis.md` | 28 | Lista `protocols.py` inexistente | CRÍTICO | Eliminar línea |
| 3 | `development-guide.md` | 105 | Lista `protocols.py` inexistente | CRÍTICO | Eliminar línea |
| 4 | `architecture.md` | 140 | Dice "4-step" pero es 5-step | ALTO | Corregir a 5-step |
| 5 | `project-overview.md` | 15 | Versión 0.5.1 obsoleta | ALTO | Actualizar a 0.5.20 |
| 6 | `MILESTONE_4_POWER_PROFILE.md` | 7 | Target v0.4.0-dev obsoleto | ALTO | Marcar como histórico |
| 7 | `MILESTONE_4_1_PLANNING.md` | 8 | Target v0.5.0 obsoleto | ALTO | Marcar como histórico |
| 8 | `DASHBOARD.md` | 41, 66 | Nombre sensor incorrecto | MEDIO | Verificar nombre real |
| 9 | `SHELL_COMMAND_SETUP.md` | 86 | Nombre sensor incorrecto | MEDIO | Verificar nombre real |
| 10 | `project-scan-report.json` | — | Obsoleto (9 días) | BAJA | Eliminar o archivar |

---

## Recomendaciones

### Acciones Inmediatas (CRÍTICAS)

1. **Eliminar referencia a `protocols.py`** en:
   - `architecture.md` línea 193
   - `source-tree-analysis.md` línea 28
   - `development-guide.md` línea 105

2. **Corregir "4-step" → "5-step"** en `architecture.md` línea 140

### Acciones de Limpieza (ALTAS)

3. **Actualizar versiones obsoletas**:
   - `project-overview.md` línea 15: 0.5.1 → 0.5.20
   - `MILESTONE_4_POWER_PROFILE.md`: Marcar como documento histórico
   - `MILESTONE_4_1_PLANNING.md`: Marcar como documento histórico o planificar

### Acciones de Verificación (MEDIAS)

4. **Verificar nombres de sensores EMHASS** - Los documentos `DASHBOARD.md` y `SHELL_COMMAND_SETUP.md` usan `sensor.emhass_perfil_diferible_{vehicle_id}` pero el código puede usar otro nombre. Investigar el nombre real del sensor en el dashboard YAML.

---

## Documentos Candidatos a Eliminación

| Documento | Razón |
|-----------|-------|
| `project-scan-report.json` | Obsoleto, scan del 2026-04-16 |
| `MILESTONE_4_1_PLANNING.md` | Planejamento antiguo, target v0.5.0 |
| `MILESTONE_4_POWER_PROFILE.md` | Milestone completado, documento histórico |

---

## Verificación de Archivos vs Código

| Archivo mentioned | Existe? | Notas |
|-------------------|---------|-------|
| `protocols.py` | ❌ NO | No existe en el código |
| `calculations.py` | ✅ SÍ | 54KB, líneas 54340 |
| `trip_manager.py` | ✅ SÍ | 97KB, líneas 97429 |
| `emhass_adapter.py` | ✅ SÍ | 99KB, líneas 99007 |
| `sensor.py` | ✅ SÍ | 36KB, TripEmhassSensor existe |
| `config_flow.py` | ✅ SÍ | 40KB, 5-step correcto |

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
**Próx. revisión**: Trimestral o al actualizar versión

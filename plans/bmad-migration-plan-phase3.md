# Plan de Migración de Tests - Fase 3: entry_id en TripManager

## Resumen Ejecutivo

**Estado actual:**
- 150 tests pasan ✅
- FASE 1 completada: `normalize_vehicle_id()` centralizado
- FASE 2 completada: `YamlTripStorage` inyectado en producción

**Problema remaining:**
- Muchos tests crean `TripManager` sin `entry_id`
- `publish_deferrable_loads()` necesita `entry_id` para hacer `async_refresh_coordinator()`
- Sin `entry_id`, el coordinator no se refresca cuando trips cambian

**Objetivo:**
Migrar todos los tests para pasar `entry_id` de forma consistente, garantizando que `publish_deferrable_loads()` funcione correctamente.

---

## Análisis de 238 TripManager en Tests

### Patrones encontrados:

| Patrón | Count | Descripción |
|--------|-------|-------------|
| `TripManager(hass, "veh")` | ~180 | Sin entry_id - PROBLEMA |
| `TripManager(hass, "veh", entry_id="...")` | ~45 | Con entry_id - OK |
| `TripManager(hass, "veh", storage=...)` | ~25 | Con storage - MIXTO |
| `TripManager(hass_no_storage, "veh")` | ~15 | Sin storage - MIXTO |

### Tests que SÍ tienen entry_id (45 instancias):

```python
# test_trip_manager.py
TripManager(mock_hass_with_storage, "test_vehicle", entry_id="test_entry")  # línea 1293, 1314, 1348, 1390, 1456, 1506, 1536, 1904

# test_trip_manager_sensor_hooks.py
TripManager(hass, "veh", entry_id="entry1")  # línea 31, 60, 83

# test_trip_manager_cover_more.py
TripManager(hass, "veh_emhass", entry_id="e_em", storage=...)  # línea 64

# test_coverage_edge_cases.py
TripManager(hass, "test_car", entry.entry_id, presence_config)  # línea 339, 476
```

### Tests que NO tienen entry_id (~180 instancias):

```python
# test_trip_manager_core.py - ~90 instancias
# test_trip_manager.py - ~60 instancias  
# test_power_profile_tdd.py - ~10 instancias
# test_trip_calculations.py - ~5 instancias
# etc.
```

---

## Plan de Migración por Fases

### FASE A: Crítica - Tests que usan publish_deferrable_loads

**Target:** ~25 tests
**Risk:** ALTO
**Quality Gate:** Tests que fallan => revert y analizar

Estos tests necesitan `entry_id` porque:
1. Llaman `publish_deferrable_loads()` directamente
2. Verifican que coordinator se refresca
3. Testean integración EMHASS completa

**Files a modificar:**
```
tests/test_trip_manager_core.py
tests/test_trip_manager_emhass.py
tests/test_post_restart_persistence.py
tests/test_integration_uninstall.py
```

**Patrón de fix:**
```python
# ANTES (problemático)
trip_manager = TripManager(mock_hass, vehicle_id)

# DESPUÉS (correcto)
trip_manager = TripManager(mock_hass, vehicle_id, entry_id="test_entry_id")
```

**Fixtures a crear en conftest.py:**
```python
@pytest.fixture
def trip_manager_with_entry_id(mock_hass, mock_store):
    """TripManager con entry_id para tests de EMHASS."""
    return TripManager(mock_hass, "test_vehicle", entry_id="test_entry_123")
```

---

### FASE B: Media - Tests que usan async_get_vehicle_soc

**Target:** ~50 tests
**Risk:** MEDIO
**Quality Gate:** 100% tests pass antes de proceed

Estos tests llaman `async_get_vehicle_soc()` que hace lookup de config entry:
```python
# trip_manager.py líneas 1245-1264
entry = hass.config_entries.async_entry_for_domain(DOMAIN)
if entry and entry.entry_id == self._entry_id:
    # usa datos del entry
```

**Files a modificar:**
```
tests/test_soc_milestone.py
tests/test_presence_monitor_soc.py
tests/test_trip_manager_fix_branches.py
tests/test_trip_manager_cover_line1781.py
```

---

### FASE C: Baja - Tests de pure functions / calculations

**Target:** ~100 tests
**Risk:** BAJO
**Quality Gate:** Coverage maintained >95%

Tests que no usan ninguna función que necesite entry_id:
- Cálculos puros en `calculations.py`
- Validación de hora/formato
- Sanitización de trips

**Files a modificar:**
```
tests/test_calculations.py
tests/test_trip_calculations.py
tests/test_trip_create_branches.py
tests/test_power_profile_tdd.py
```

---

### FASE D: Cleanup - Eliminar deuda técnica

**Target:** ~20 tests
**Risk:** BAJO

- Tests que usan `MagicMock()` sin hass real
- Tests que mockean métodos internos directamente
- Tests con cobertura duplicada

---

## Quality Gates por Fase

### Phase Gate A (Crítica)
```bash
# 1. Run tests con entry_id fix
pytest tests/test_trip_manager_core.py -v --tb=short

# 2. Verificar que publish_deferrable_loads funciona
# 3. Verificar coordinator refresh
pytest tests/test_trip_manager_emhass.py -v --tb=short

# 4. Verificar persistencia post-restart
pytest tests/test_post_restart_persistence.py -v --tb=short

# GATE: Si algún test falla → revert y analizar antes de continuar
```

### Phase Gate B (Media)
```bash
pytest tests/test_soc_milestone.py tests/test_presence_monitor_soc.py -v
# GATE: 100% pass
```

### Phase Gate C (Baja)
```bash
pytest tests/test_calculations.py tests/test_trip_calculations.py -v
# GATE: Coverage maintained
```

### Phase Gate Final
```bash
# Full suite
pytest --ignore=tests/test_coverage_edge_cases.py -v --tb=short
# GATE: 150+ passed, 0 failed
```

---

## Ejecución Step-by-Step

### Paso 1: Agregar fixture en conftest.py

```python
@pytest.fixture
def tm_with_entry(hass, storage):
    """TripManager with entry_id for coordinator-dependent tests."""
    return TripManager(hass, "test_vehicle", entry_id="test_entry_123", storage=storage)
```

### Paso 2: Modificar tests en fase A (15 archivos críticos)

### Paso 3: Validar Gate A

### Paso 4: Modificar tests en fase B (20 archivos)

### Paso 5: Validar Gate B

### Paso 6: Modificar tests en fase C (30 archivos)

### Paso 7: Validar Gate C

### Paso 8: Cleanup fase D

### Paso 9: Validación final completa

---

## Tracking de Progreso

| Fase | Tests | Status | Notes |
|------|-------|--------|-------|
| A | ~25 | PENDING | Crítica - publish_deferrable_loads |
| B | ~50 | PENDING | Media - async_get_vehicle_soc |
| C | ~100 | PENDING | Baja - pure functions |
| D | ~20 | PENDING | Cleanup |
| **TOTAL** | **~195** | - | |

---

## Commands de Validación

```bash
# Ver tests que fallan sin entry_id
grep -r "TripManager(" tests/ | grep -v "entry_id" | wc -l

# Ver tests que ya tienen entry_id  
grep -r "entry_id=" tests/ | grep "TripManager" | wc -l

# Run full suite
pytest --ignore=tests/test_coverage_edge_cases.py -v 2>&1 | tail -20
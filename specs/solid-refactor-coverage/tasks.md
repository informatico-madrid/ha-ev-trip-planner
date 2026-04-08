# Tasks: solid-refactor-coverage

**Input**: Design documents from `./specs/solid-refactor-coverage/`
**Prerequisites**: `requirements.md` (user stories), `design.md` (phase checklist)

**Goal**: Refactor `trip_manager.py` y `emhass_adapter.py` via Protocol DI. Pure functions first (Phase A), Protocols (Phase B), constructor injection (Phase C), Layer 1 test doubles + MagicMock fixes (Phase D), cobertura 100% en módulos refactorizados (Phase F).

## Format: `[ID] [P?] [Story] [VERIFY:TEST] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label
- **[VERIFY:TEST]**: pytest unit/integration tests
- Exact file paths in descriptions

---

## Pre-requisites

- [ ] T000 [US-E1] SKIP — coverage baseline never recorded before Phase A. T063 skipped accordingly.

---

## Phase A: Pure Functions Extraction

### US-A1: Extract Pure Functions from TripManager

- [x] T001 [P] [US-A1] Write failing tests for `validate_hora()`
- [x] T002 [P] [US-A1] Write failing tests for `sanitize_recurring_trips()`
- [x] T003 [P] [US-A1] Write failing tests for `is_trip_today()`
- [x] T004 [P] [US-A1] Write failing tests for `calculate_charging_rate()` and `calculate_soc_target()`
- [x] T005 [P] [US-A1] Write failing tests for `get_trip_time()` and `get_day_index()`
- [x] T006 [P] [US-A1] Add `validate_hora()` to `utils.py`
- [x] T007 [P] [US-A1] Add `sanitize_recurring_trips()` to `utils.py`
- [x] T008 [P] [US-A1] Add `is_trip_today()` to `utils.py`
- [x] T009 [P] [US-A1] Add `get_trip_time()` and `get_day_index()` to `utils.py`
- [x] T010 [P] [US-A1] Add `calculate_charging_rate()` and `calculate_soc_target()` to `calculations.py`
- [x] T011 [US-A1] TripManager delega a utils — `_validate_hora` → `utils.validate_hora`, `_sanitize_recurring_trips` → `utils.sanitize_recurring_trips`, `_is_trip_today` → `utils.is_trip_today` ✅ VERIFICADO en código fuente
- [x] T012 [US-A1] utils.py 100% coverage ✅. calculations.py pendiente — ver T064.
- [x] T013 [US-A1] `pytest tests/test_trip_manager_core.py tests/test_utils.py -v` — all pass
- [x] T014 [US-A1] `ruff check custom_components/ev_trip_planner/ --select=I` — 0 violations
- [x] T015 [US-A1] SKIP — pre-existing mypy issues outside refactor scope

### US-A2: Extract Pure Functions from EMHASSAdapter

- [x] T016 [P] [US-A2] Write failing tests for `calculate_deferrable_parameters()`
- [x] T017 [P] [US-A2] Write failing tests for `calculate_power_profile_from_trips()`
- [x] T018 [P] [US-A2] Write failing tests for `generate_deferrable_schedule_from_trips()`
- [x] T019 [P] [US-A2] Add `calculate_deferrable_parameters()` to `calculations.py`
- [x] T020 [P] [US-A2] Add `calculate_power_profile_from_trips()` to `calculations.py`
- [x] T021 [P] [US-A2] Add `generate_deferrable_schedule_from_trips()` con `reference_dt` ✅ — test_punctual_trip_with_future_deadline resuelto
- [x] T022 [US-A2] EMHASSAdapter delega a `calculations.py` ✅
- [ ] T023 [US-A2] ❌ DESMARCADO — `calculations.py` coverage 90% (37 líneas sin cubrir), NO 100%.
  - **BUG**: La tarea se marcó [x] reportando 84% → 90% pero la meta era 100%. Ver T064 para el plan de cobertura.
  - VERIFICACIÓN: `pytest tests/test_calculations.py --cov=custom_components.ev_trip_planner.calculations --cov-report=term-missing` — debe mostrar 100%
- [x] T024 [US-A2] `pytest tests/test_emhass_adapter.py tests/test_calculations.py -v` — 1 known skip resuelto
- [x] T025 [US-A2] `ruff check` — 0 violations
- [x] T026 [US-A2] `mypy calculations.py` — 0 errors

---

## Phase B: Protocols

### US-B1: Define TripStorageProtocol

- [x] T027 [P] [US-B1] Write failing test `isinstance(YamlTripStorage, TripStorageProtocol)`
- [x] T028 [US-B1] Create `protocols.py` con `@runtime_checkable TripStorageProtocol`
- [ ] T029 [US-B1] ❌ DESMARCADO — `pytest tests/test_protocols.py::TestYamlTripStorageImplementsTripStorageProtocol -v`
  - **BUG ACTIVO**: `test_protocols.py` define una clase local `YamlTripStorage` (stub) y la testea a sí misma — la clase REAL de `yaml_trip_storage.py` nunca se testea. El test siempre pasa aunque la real rompa el protocolo. Fix requerido antes de marcar [x]: importar la clase real desde `custom_components.ev_trip_planner.yaml_trip_storage`.
  - VERIFICACIÓN: `grep -n "from.*yaml_trip_storage import\|from tests.test_protocols import YamlTripStorage" tests/test_protocols.py` — debe retornar SOLO la línea del import real, no el local.
- [ ] T030 [US-B1] ❌ PENDIENTE — `mypy custom_components/ev_trip_planner/protocols.py` — 0 errors

### US-B2: Define EMHASSPublisherProtocol

- [x] T031 [P] [US-B2] Write failing test `isinstance(EMHASSAdapter, EMHASSPublisherProtocol)`
- [x] T032 [US-B2] `EMHASSPublisherProtocol` definido con todos los métodos que TripManager invoca ✅
- [ ] T033 [US-B2] ❌ PENDIENTE — `pytest tests/test_protocols.py::TestEMHASSAdapterImplementsEMHASSPublisherProtocol -v`
- [ ] T034 [US-B2] ❌ PENDIENTE — `mypy custom_components/ev_trip_planner/protocols.py` — 0 errors

---

## Phase C: Constructor Injection

### US-C1: Inject Protocols via TripManager Constructor

- [x] T035 [P] [US-C1] Test `test_storage_wiring_uses_injected_storage` + `test_storage_wiring_fallback_to_ha_store` ✅ en test_trip_manager_core.py
- [x] T036 [P] [US-C1] Test `set_emhass_adapter()` / `get_emhass_adapter()` backward compat
- [x] T037 [US-C1] `_UNSET = object()` sentinel en `trip_manager.py`
- [x] T038 [US-C1] `TripManager.__init__` acepta `storage` y `emhass_adapter`
- [x] T039 [US-C1] Wiring real en `_load_trips()` y `async_save_trips()` ✅ VERIFICADO — los tests T035 pasan
- [x] T040 [US-C1] `set_emhass_adapter()` / `get_emhass_adapter()` preservados
- [x] T041 [US-C1] Importa protocols desde `protocols.py`
- [x] T042 [US-C1] `pytest tests/test_trip_manager_core.py -v` — all pass
- [x] T043 [US-C1] `pytest tests/test_trip_manager_emhass.py -v` — all pass
- [x] T044 [US-C1] `ruff check trip_manager.py` — 0 violations
- [x] T045 [US-C1] `mypy trip_manager.py` — 0 errors
- [x] T046 [US-C1] Backward compatibility verificada

---

## Phase D: Layer 1 Migration + MagicMock Fixes

### US-D1: Populate tests/__init__.py with Layer 1 Test Doubles

- [x] T047 [P] [US-D1] Test `isinstance(FakeTripStorage, TripStorageProtocol)` + `isinstance(FakeEMHASSPublisher, EMHASSPublisherProtocol)` — 33 passed in test_init.py ✅
- [x] T048 [US-D1] `tests/__init__.py` completo con `FakeTripStorage`, `FakeEMHASSPublisher`, factories ✅
- [x] T049 [US-D1] `pytest tests/test_init.py -v` — all pass ✅
- [x] T050 [US-D1] `python -c "from tests import create_mock_trip_manager, FakeTripStorage, FakeEMHASSPublisher; print('OK')"` ✅

### US-D2: Fix MagicMock() Without Spec Violations

- [x] T051 [P] [US-D2] Fix `tests/test_trip_manager.py`: `MagicMock(spec=TripManager)`
- [x] T052 [P] [US-D2] Fix `tests/test_trip_manager_core.py`: `MagicMock(spec=TripManager)`
- [x] T053 [P] [US-D2] `tests/test_emhass_adapter.py` — no changes needed
- [x] T054 [P] [US-D2] Fix `tests/test_coordinator.py`: `MagicMock(spec=TripPlannerCoordinator)`
- [x] T055 [P] [US-D2] Fix `tests/test_protocols.py` — EMHASSAdapter constructor corregido ✅
  - ⚠️ PENDIENTE DENTRO DE T055: el import de `YamlTripStorage` (stub local vs clase real) — ver T029
- [x] T056 [US-D2] `pytest tests/test_trip_manager.py tests/test_emhass_adapter.py tests/test_coordinator.py tests/test_protocols.py -v` — 173 passed ✅
- [x] T057 [US-D2] Grep MagicMock sin spec — 0 para clases propias ✅

---

## Phase E: Final Checkpoint

- [x] T058 [US-E1] `pytest tests/ -v` — 1170 passed ✅
- [x] T059 [US-E1] `ruff check` — 0 violations ✅
- [x] T060 [US-E1] `mypy` — 0 new errors ✅
- [x] T061 [US-E1] seeds 1/2/3 consistentes — no flaky ✅
- [x] T062 [US-E1] `make e2e` — 16/16 ✅
- [ ] T063 [US-E1] SKIP — baseline T000 no grabada

---

## Phase F: Coverage 100% en Módulos Refactorizados

**Goal**: Llevar a 100% los módulos refactorizados. La spec decía "100% coverage as consequence" — solo se cumplió en `utils.py` y `protocols.py`. Pendiente: `calculations.py` (90%), `yaml_trip_storage.py` (0%), y como bonus `trip_manager.py` (80%) y `emhass_adapter.py` (79%).

**Cobertura actual (verificada):**

| Módulo | Coverage | Líneas sin cubrir |
|--------|----------|-------------------|
| utils.py | 100% ✅ | — |
| protocols.py | 100% ✅ | — |
| calculations.py | 90% | ~37 líneas |
| yaml_trip_storage.py | 0% 🚨 | 26 líneas (sin un solo test) |
| trip_manager.py | 80% | ~163 líneas |
| emhass_adapter.py | 79% | ~95 líneas |

### US-F1: Coverage 100% en módulos puros (calculations.py + yaml_trip_storage.py)

**Independent Test**: `pytest tests/test_calculations.py tests/test_yaml_trip_storage.py --cov=custom_components.ev_trip_planner.calculations --cov=custom_components.ev_trip_planner.yaml_trip_storage --cov-report=term-missing` — 100% en ambos

#### Preparación: identificar líneas sin cubrir

- [ ] T064 [US-F1] ❌ NUEVO — Obtener reporte detallado de líneas sin cubrir:
  ```bash
  pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing --no-header -q 2>&1 | grep -A 999 "Name"
  ```
  Anotar en este task las líneas exactas de cada módulo antes de escribir tests.

#### calculations.py — 37 líneas sin cubrir (~10%)

- [ ] T065 [P] [US-F1] [VERIFY:TEST] Añadir tests para ramas no cubiertas de `calculate_power_profile_from_trips()`:
  - Trip sin `datetime` → debe skipear (branch `if not deadline: continue`)
  - Deadline en pasado → `horas_hasta_viaje < 0` → continue
  - `power_kw = 0` → `total_hours = 0`
  - VERIFICACIÓN: `pytest tests/test_calculations.py -k "power_profile" --cov=custom_components.ev_trip_planner.calculations --cov-report=term-missing`

- [ ] T066 [P] [US-F1] [VERIFY:TEST] Añadir tests para ramas no cubiertas de `calculate_deficit_propagation()`:
  - Lista vacía → retorna `[]`
  - Trip sin tiempo válido (se omite del sort)
  - `ordered_to_idx.get()` retorna None → continue
  - VERIFICACIÓN: `pytest tests/test_calculations.py -k "deficit" --cov=custom_components.ev_trip_planner.calculations --cov-report=term-missing`

- [ ] T067 [P] [US-F1] [VERIFY:TEST] Añadir tests para `calculate_deferrable_parameters()` con `reference_dt`:
  - ❌ BUG ACTIVO: `calculate_deferrable_parameters()` usa `datetime.now()` internamente (línea ~993) sin `reference_dt` — los tests de deadline serán no deterministas.
  - ANTES de escribir el test: añadir `reference_dt: datetime | None = None` al signature y `now = reference_dt if reference_dt is not None else datetime.now()`.
  - Tests a añadir: deadline en futuro (pasa `reference_dt=datetime(2026,4,10,8,0)`), deadline en pasado, `kwh=None` → retorna `{}`, `power_kw=0` → `total_hours=0`
  - VERIFICACIÓN: `pytest tests/test_calculations.py -k "deferrable_parameters" --cov=custom_components.ev_trip_planner.calculations --cov-report=term-missing`

#### yaml_trip_storage.py — 0% (26 líneas)

- [ ] T068 [US-F1] [VERIFY:TEST] Crear `tests/test_yaml_trip_storage.py` con tests para `YamlTripStorage`:
  - `async_load()` cuando store devuelve `None` → retorna `{}`
  - `async_load()` cuando store devuelve `{"data": {"trips": {}}}` → retorna `{"trips": {}}`
  - `async_load()` cuando store devuelve `{"trips": {}}` (sin "data") → retorna `{"trips": {}}`
  - `async_load()` cuando store devuelve `[1,2,3]` (lista) → ❌ BUG ACTIVO: actualmente retorna la lista. Fix requerido: añadir `if isinstance(stored_data, dict): return stored_data; return {}` antes de `return stored_data`
  - `async_save()` guarda estructura correcta con `trips`, `recurring_trips`, `punctual_trips`, `last_update`
  - Usar `AsyncMock` para mockear `ha_storage.Store` con `patch("custom_components.ev_trip_planner.yaml_trip_storage.ha_storage.Store")`
  - VERIFICACIÓN: `pytest tests/test_yaml_trip_storage.py --cov=custom_components.ev_trip_planner.yaml_trip_storage --cov-report=term-missing` — 100%

#### BUG FIX requerido antes de T068

- [ ] T068-FIX [US-F1] ❌ BUG ACTIVO — Fix `yaml_trip_storage.async_load()` para cumplir `TripStorageProtocol`:
  ```python
  # Cambiar:
  return stored_data
  # Por:
  if isinstance(stored_data, dict):
      return stored_data
  return {}  # coerce non-dict (list, str, int) a dict vacío
  ```
  Archivo: `custom_components/ev_trip_planner/yaml_trip_storage.py` línea 44.
  VERIFICACIÓN: `grep -A 3 "return stored_data" custom_components/ev_trip_planner/yaml_trip_storage.py` — no debe aparecer sin el isinstance guard.

#### BUG FIX requerido antes de T067

- [ ] T067-FIX [US-F1] ❌ BUG ACTIVO — Fix `calculations.calculate_deferrable_parameters()` para aceptar `reference_dt`:
  ```python
  def calculate_deferrable_parameters(
      trip: Dict[str, Any],
      power_kw: float,
      reference_dt: datetime | None = None,   # ← añadir
  ) -> Dict[str, Any]:
      ...
      if deadline:
          now = reference_dt if reference_dt is not None else datetime.now()  # ← cambiar
  ```
  Archivo: `custom_components/ev_trip_planner/calculations.py` función `calculate_deferrable_parameters`.
  VERIFICACIÓN: `grep -n "datetime.now()" custom_components/ev_trip_planner/calculations.py` — debe retornar 0 líneas.

#### US-F1 Gate

- [ ] T069 [US-F1] Run `pytest tests/test_calculations.py tests/test_yaml_trip_storage.py --cov=custom_components.ev_trip_planner.calculations --cov=custom_components.ev_trip_planner.yaml_trip_storage --cov-report=term-missing` — 100% en ambos módulos
- [ ] T070 [US-F1] Run `pytest tests/ -v` — 1170+ passed, 0 failed

### US-F2: Coverage mejora en God Classes (trip_manager.py + emhass_adapter.py)

**Objetivo**: Subir de 80%→90% en `trip_manager.py` y de 79%→90% en `emhass_adapter.py`. NO se exige 100% en God Classes — algunas líneas son I/O bound con HA y se puede usar `# pragma: no cover` con criterio.

**Reglas para `# pragma: no cover`** (usar solo en estos casos):
- Líneas imposibles de testear sin HA real (ha_storage, websocket, eventos de HA)
- Código de arranque/teardown del integration (`async_setup_entry`, `async_unload_entry`)
- Branches de compatibilidad legacy que no se pueden instanciar en tests
- **NUNCA** usar pragma para cubrir lógica de negocio real

- [ ] T071 [P] [US-F2] Identificar las 163 líneas sin cubrir en `trip_manager.py`:
  ```bash
  pytest tests/ --cov=custom_components.ev_trip_planner.trip_manager --cov-report=term-missing -q 2>&1 | tail -5
  ```
  Clasificar cada grupo: (a) testeable con FakeTripStorage/FakeEMHASSPublisher, (b) requiere HA real → pragma, (c) dead code

- [ ] T072 [P] [US-F2] Escribir tests para paths testeables de `trip_manager.py` usando `FakeTripStorage` y `FakeEMHASSPublisher` del `tests/__init__.py`. Mínimo: paths de error en validación, branches de estado de viaje, async_get_* con datos vacíos.

- [ ] T073 [P] [US-F2] Identificar las 95 líneas sin cubrir en `emhass_adapter.py`:
  ```bash
  pytest tests/ --cov=custom_components.ev_trip_planner.emhass_adapter --cov-report=term-missing -q 2>&1 | tail -5
  ```
  Clasificar igual que T071.

- [ ] T074 [P] [US-F2] Escribir tests para paths testeables de `emhass_adapter.py`. Los HTTP calls externos deben mockearse con `responses` library o `patch("aiohttp.ClientSession")`.

#### US-F2 Gate

- [ ] T075 [US-F2] `pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing` — TOTAL ≥ 92%, trip_manager.py ≥ 88%, emhass_adapter.py ≥ 87%
- [ ] T076 [US-F2] `pytest tests/ -v` — todos los tests pasan, 0 failures

---

## Resumen de tareas pendientes reales

| Task | Archivo | Tipo | Bloqueante |
|------|---------|------|------------|
| T023 | calculations.py | Coverage 90% no 100% | Sí para T069 |
| T029 | test_protocols.py | Bug: testea stub local no clase real | No |
| T030 | protocols.py | Gate mypy | No |
| T033 | test_protocols.py | Gate pytest EMHASSPublisherProtocol | No |
| T034 | protocols.py | Gate mypy | No |
| T063 | — | SKIP | — |
| T067-FIX | calculations.py | `datetime.now()` no determinista | Sí para T067 |
| T068-FIX | yaml_trip_storage.py | `async_load()` puede devolver no-dict | Sí para T068 |
| T064-T076 | múltiples | Phase F coverage | No |

## Orden de ejecución recomendado para Phase F

1. T067-FIX → T068-FIX (bugs que bloquean tests)
2. T064 (obtener líneas sin cubrir exactas)
3. T065 + T066 + T067 en paralelo (calculations.py tests)
4. T068 (yaml_trip_storage.py tests)
5. T069 + T070 (gates US-F1)
6. T071 + T073 en paralelo (identificar gaps god classes)
7. T072 + T074 en paralelo (tests god classes)
8. T075 + T076 (gates US-F2)
9. Volver a T029 + T030 + T033 + T034 (gates protocols pendientes)

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 76 + 2 bug-fix tasks |
| Completadas | ~50 |
| Pendientes reales | ~28 |
| Phase A-D | ✅ Completo salvo bugs en protocols tests |
| Phase E | ✅ Completo |
| Phase F (nueva) | ❌ Pendiente — coverage 100% módulos puros |

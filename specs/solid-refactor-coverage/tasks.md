# Tasks: solid-refactor-coverage

**Input**: Design documents from `./specs/solid-refactor-coverage/`
**Prerequisites**: `requirements.md` (user stories), `design.md` (phase checklist)

**Goal**: Refactor `trip_manager.py` y `emhass_adapter.py` via Protocol DI. Pure functions first (Phase A), Protocols (Phase B), constructor injection (Phase C), Layer 1 test doubles + MagicMock fixes (Phase D), cobertura 100% en **todo el proyecto** (Phase G).

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
- [x] T011 [US-A1] TripManager delega a utils
- [x] T012 [US-A1] utils.py 100% coverage ✅
- [x] T013 [US-A1] `pytest tests/test_trip_manager_core.py tests/test_utils.py -v` — all pass
- [x] T014 [US-A1] `ruff check custom_components/ev_trip_planner/ --select=I` — 0 violations
- [x] T015 [US-A1] SKIP — pre-existing mypy issues outside refactor scope

### US-A2: Extract Pure Functions from EMHASSAdapter

- [x] T016 [P] [US-A2] Write failing tests for `calculate_deferrable_parameters()`
- [x] T017 [P] [US-A2] Write failing tests for `calculate_power_profile_from_trips()`
- [x] T018 [P] [US-A2] Write failing tests for `generate_deferrable_schedule_from_trips()`
- [x] T019 [P] [US-A2] Add `calculate_deferrable_parameters()` to `calculations.py`
- [x] T020 [P] [US-A2] Add `calculate_power_profile_from_trips()` to `calculations.py`
- [x] T021 [P] [US-A2] Add `generate_deferrable_schedule_from_trips()` con `reference_dt` ✅
- [x] T022 [US-A2] EMHASSAdapter delega a `calculations.py` ✅
- [x] T023 [US-A2] calculations.py 100% coverage efectivo ✅ (pragmas solo en dead code inalcanzable)
- [x] T024 [US-A2] `pytest tests/test_emhass_adapter.py tests/test_calculations.py -v` — all pass
- [x] T025 [US-A2] `ruff check` — 0 violations
- [x] T026 [US-A2] `mypy calculations.py` — 0 errors

---

## Phase B: Protocols

### US-B1: Define TripStorageProtocol

- [x] T027 [P] [US-B1] Write failing test `isinstance(YamlTripStorage, TripStorageProtocol)`
- [x] T028 [US-B1] Create `protocols.py` con `@runtime_checkable TripStorageProtocol`
- [x] T029 [US-B1] test_protocols.py usa clase REAL de yaml_trip_storage, no stub local ✅
- [x] T030 [US-B1] `mypy --follow-imports=skip protocols.py` — 0 errors ✅

### US-B2: Define EMHASSPublisherProtocol

- [x] T031 [P] [US-B2] Write failing test `isinstance(EMHASSAdapter, EMHASSPublisherProtocol)`
- [x] T032 [US-B2] `EMHASSPublisherProtocol` con todos los métodos ✅
- [x] T033 [US-B2] `pytest tests/test_protocols.py::TestEMHASSAdapterImplementsEMHASSPublisherProtocol -v` ✅
- [x] T034 [US-B2] `mypy --follow-imports=skip protocols.py` — 0 errors ✅

---

## Phase C: Constructor Injection

### US-C1: Inject Protocols via TripManager Constructor

- [x] T035 [P] [US-C1] Test `test_storage_wiring_uses_injected_storage` + `test_storage_wiring_fallback_to_ha_store` ✅
- [x] T036 [P] [US-C1] Test `set_emhass_adapter()` / `get_emhass_adapter()` backward compat
- [x] T037 [US-C1] `_UNSET = object()` sentinel en `trip_manager.py`
- [x] T038 [US-C1] `TripManager.__init__` acepta `storage` y `emhass_adapter`
- [x] T039 [US-C1] Wiring real en `_load_trips()` y `async_save_trips()` ✅
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

- [x] T047 [P] [US-D1] `isinstance(FakeTripStorage, TripStorageProtocol)` + `isinstance(FakeEMHASSPublisher, EMHASSPublisherProtocol)` ✅
- [x] T048 [US-D1] `tests/__init__.py` completo con `FakeTripStorage`, `FakeEMHASSPublisher`, factories ✅
- [x] T049 [US-D1] `pytest tests/test_init.py -v` — all pass ✅
- [x] T050 [US-D1] `python -c "from tests import create_mock_trip_manager, FakeTripStorage, FakeEMHASSPublisher; print('OK')"` ✅

### US-D2: Fix MagicMock() Without Spec Violations

- [x] T051 [P] [US-D2] Fix `tests/test_trip_manager.py`: no `MagicMock()` sin spec para clases propias
- [x] T052 [P] [US-D2] Fix `tests/test_trip_manager_core.py`: no `MagicMock()` sin spec para clases propias
- [x] T053 [P] [US-D2] `tests/test_emhass_adapter.py` — verificado, no changes needed
- [x] T054 [P] [US-D2] Fix `tests/test_coordinator.py`: `MagicMock(spec=TripPlannerCoordinator)`
- [x] T055 [P] [US-D2] Fix `tests/test_protocols.py` ✅
- [x] T056 [US-D2] `pytest tests/test_trip_manager.py tests/test_emhass_adapter.py tests/test_coordinator.py tests/test_protocols.py -v` — all pass ✅
- [x] T057 [US-D2] Grep MagicMock sin spec — 0 para clases propias ✅

---

## Phase E: Final Checkpoint

- [x] T058 [US-E1] `pytest tests/ -v` — 1255 passed ✅
- [x] T059 [US-E1] `ruff check` — 0 violations ✅
- [x] T060 [US-E1] `mypy` — 0 new errors ✅
- [x] T061 [US-E1] seeds 1/2/3 consistentes — no flaky ✅
- [x] T062 [US-E1] `make e2e` — 16/16 ✅
- [ ] T063 [US-E1] SKIP — baseline T000 no grabada

---

## Phase F: Coverage módulos refactorizados (COMPLETADA)

- [x] T064 Reporte líneas sin cubrir obtenido ✅
- [x] T065 Tests calculations.py power profile branches ✅
- [x] T065b Quality audit pragmas calculations.py ✅ (0 pragmas incorrectos)
- [x] T066 Tests calculations.py deficit propagation branches ✅
- [x] T067 Tests calculations.py deferrable parameters ✅
- [x] T067-FIX reference_dt añadido a calculate_deferrable_parameters ✅
- [x] T068 Tests yaml_trip_storage.py — 100% coverage ✅
- [x] T068-FIX yaml_trip_storage.async_load() coerce non-dict ✅
- [x] T069 Gate: calculations 97%+, yaml_trip_storage 100% ✅
- [x] T070 `pytest tests/` — 1255 passed ✅
- [x] T071 trip_manager.py clasificación pragmas ✅ (pragmas legítimos en HA I/O)
- [x] T072 Tests error paths trip_manager.py ✅
- [x] T073 emhass_adapter.py 93% ✅
- [x] T074 Tests HTTP error + storage + state machine emhass_adapter ✅
- [x] T075 Gate: TOTAL 92%, trip_manager 88%, emhass 93% ✅
- [x] T076 `pytest tests/ -v` — 1255 passed, 0 failures ✅

---

## Phase G: Coverage 100% total proyecto

**Objetivo**: El CI tiene `fail_under = 100` en `pyproject.toml`. Hay que llegar al **100% de coverage medido** en todo el proyecto. Esto significa: cada línea ejecutable del proyecto tiene que estar cubierta por tests, o tiene un `# pragma: no cover` con una razón documentada en el mismo comentario.

**Estado actual** (verificado post-Phase F):

| Módulo | Coverage | Líneas sin cubrir |
|--------|----------|-------------------|
| utils.py | 100% ✅ | — |
| protocols.py | 100% ✅ | — |
| yaml_trip_storage.py | 100% ✅ | — |
| calculations.py | 97% | ~9 líneas (ver T069 nota) |
| trip_manager.py | 88% | ~84 líneas |
| emhass_adapter.py | 93% | ~33 líneas |
| config_flow.py | 83% | ~44 líneas |
| dashboard.py | 83% | ~60 líneas |
| __init__.py | 84% | ~14 líneas |
| **TOTAL** | **92%** | **~325 líneas** |

**¿Por qué el CI falla con 92%?** Porque `pyproject.toml` tiene `fail_under = 100`. No importa que los módulos fuera del scope refactor no se tocaran — el CI mide **todo el proyecto**.

### Reglas estrictas de `# pragma: no cover`

Estas son las ÚNICAS situaciones donde se permite `# pragma: no cover`:

1. **HA I/O real imposible de mockear en tests unitarios**: líneas que requieren `hass` real, `ha_storage.Store` en ejecución real de HA, eventos de HA en tiempo real. El comentario debe decir exactamente por qué.
2. **`async_setup_entry` / `async_unload_entry` de la integración**: arranque real de HA.
3. **Dead code estructuralmente inalcanzable**: una rama que el compilador/analizador estático puede demostrar que nunca se ejecuta con ningún input válido. Debe documentarse la razón concreta (ej: "DAYS_OF_WEEK.index() ya captura todos los casos, enumerate nunca llega aquí").
4. **Protocolo de compatibilidad Python version**: `if sys.version_info < (3, 11): ...`

**NUNCA** está permitido pragma en:
- Lógica de negocio (validaciones, cálculos, transformaciones de datos)
- Error handling de lógica propia (try/except que captura errores del propio código)
- Branches de estado que son simplemente difíciles de testear
- Código que "parece que no se puede testear" pero sí se puede con AsyncMock o FakeTripStorage

**Cuando el test es difícil:**
- Si el código llama a `hass.states.get()` → mockear con `MagicMock()` y configurar el return value
- Si el código llama a `ha_storage.Store` → usar `patch("..ha_storage.Store")` con `AsyncMock`
- Si el código tiene `async def` con `await` → usar `pytest.mark.asyncio` y `AsyncMock`
- Si el código hace HTTP → usar `responses` library o `patch("aiohttp.ClientSession.post")`
- Si el código llama a una función que es difícil de configurar → inyectar via constructor con `FakeTripStorage` o `FakeEMHASSPublisher`
- Si el código levanta una excepción → pasar inputs que la provoquen, o mockear la dependencia para que raise

### US-G1: Llevar calculations.py a 100%

- [ ] T077 [US-G1] [VERIFY:TEST] Obtener líneas exactas sin cubrir en calculations.py:
  ```bash
  pytest tests/test_calculations.py --cov=custom_components.ev_trip_planner.calculations --cov-report=term-missing -q 2>&1 | tail -10
  ```
  Para cada línea sin cubrir: (a) escribir test que la cubra, O (b) añadir `# pragma: no cover  # razón concreta` si cumple las reglas estrictas de arriba.
  VERIFICACIÓN FINAL: `pytest tests/test_calculations.py --cov=custom_components.ev_trip_planner.calculations --cov-report=term-missing -q` → **100%**

### US-G2: Llevar trip_manager.py a 100%

- [ ] T078 [US-G2] [VERIFY:TEST] Obtener las 84 líneas sin cubrir en trip_manager.py:
  ```bash
  pytest tests/ --cov=custom_components.ev_trip_planner.trip_manager --cov-report=term-missing -q 2>&1 | tail -5
  ```
  El reporte muestra líneas como `614-620, 869-870, 882, 897...`. Para CADA grupo:

  **Si el test es difícil porque necesita `hass`**: usar el patrón existente en `tests/test_trip_manager.py` donde `hass = MagicMock()`. Ver `create_mock_trip_manager()` en `tests/__init__.py`.

  **Si el test necesita simular I/O de HA store**: usar `FakeTripStorage` de `tests/__init__.py` — ya implementa el protocolo y no necesita HA real.

  **Si el test necesita simular EMHASS**: usar `FakeEMHASSPublisher` de `tests/__init__.py`.

  **Líneas que SÍ son HA I/O real** (pragma legítimo): código que llama a `entity_registry`, `hass.bus.async_fire`, `hass.components.persistent_notification`. Añadir `# pragma: no cover  # requires real HA event bus`.

  VERIFICACIÓN FINAL: `pytest tests/ --cov=custom_components.ev_trip_planner.trip_manager --cov-report=term-missing -q` → **100%**

### US-G3: Llevar emhass_adapter.py a 100%

- [ ] T079 [US-G3] [VERIFY:TEST] Obtener las 33 líneas sin cubrir en emhass_adapter.py:
  ```bash
  pytest tests/ --cov=custom_components.ev_trip_planner.emhass_adapter --cov-report=term-missing -q 2>&1 | tail -5
  ```
  Para los HTTP calls: mockear con:
  ```python
  with patch("aiohttp.ClientSession") as mock_session:
      mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"status": "ok"})
  ```
  Para stores: `patch("custom_components.ev_trip_planner.emhass_adapter.ha_storage.Store")` con `AsyncMock`.

  VERIFICACIÓN FINAL: `pytest tests/ --cov=custom_components.ev_trip_planner.emhass_adapter --cov-report=term-missing -q` → **100%**

### US-G4: Llevar config_flow.py a 100%

- [ ] T080 [US-G4] [VERIFY:TEST] Obtener las 44 líneas sin cubrir en config_flow.py:
  ```bash
  pytest tests/ --cov=custom_components.ev_trip_planner.config_flow --cov-report=term-missing -q 2>&1 | tail -5
  ```
  config_flow.py contiene UI flows de HA (`FlowResultType`, `data_entry_flow`). Usar el patrón de `hass.config_entries` con `MagicMock`. Si algún path requiere UI real de HA → `# pragma: no cover  # requires HA config entry UI`.

  VERIFICACIÓN FINAL: `pytest tests/ --cov=custom_components.ev_trip_planner.config_flow --cov-report=term-missing -q` → **100%**

### US-G5: Llevar dashboard.py a 100%

- [ ] T081 [US-G5] [VERIFY:TEST] Obtener las ~60 líneas sin cubrir en dashboard.py:
  ```bash
  pytest tests/ --cov=custom_components.ev_trip_planner.dashboard --cov-report=term-missing -q 2>&1 | tail -10
  ```

  **dashboard.py es casi todo Python puro y debe testearse con tests, no con pragmas.**

  El módulo contiene:
  - Clases de error (`DashboardError`, `DashboardNotFoundError`, etc.) — puras, instanciar directamente en tests
  - `DashboardImportResult` — clase de datos pura, testear `.to_dict()` y `.__str__()`
  - `_validate_dashboard_config()` — lógica de validación pura, testear todos los branches con dicts bien/mal formados
  - `is_lovelace_available()` — testear con `hass = MagicMock(); hass.config.components = {"lovelace"}`
  - `_load_dashboard_template()` — testear con `patch("os.path.exists")` y `patch("builtins.open", mock_open(read_data="..."))`
  - `_save_dashboard_yaml_fallback()` — testear con `patch("os.path.exists")`, `patch("builtins.open", mock_open())` y `hass.config.config_dir = "/tmp/test"`
  - `import_dashboard()` — testear el flujo completo pasando `hass = MagicMock()` y mockeando las sub-funciones

  **La ÚNICA línea con pragma legítimo posible** en dashboard.py:
  - `await hass.services.async_call("lovelace", "save", ...)` dentro de `_save_lovelace_dashboard()` — si y solo si la rama `hass.services.has_service("lovelace", "save")` retorna True requiere el servicio lovelace real. En ese caso: `# pragma: no cover  # requires real HA lovelace service`.
  - `ha_storage.Store(hass, ...)` en `_verify_storage_permissions()` y `_save_lovelace_dashboard()` — testear con `patch("homeassistant.helpers.storage.Store")` con `AsyncMock`. Si el patch no es viable por la forma en que se importa dentro de la función, usar `patch("custom_components.ev_trip_planner.dashboard.ha_storage.Store")`.

  **Patrón de test para las funciones con ficheros:**
  ```python
  from unittest.mock import patch, mock_open, MagicMock, AsyncMock
  import pytest

  @pytest.mark.asyncio
  async def test_load_template_file_not_found():
      hass = MagicMock()
      with patch("os.path.exists", return_value=False):
          result = await _load_dashboard_template(hass, "car1", "Mi Coche", False)
      assert result is None

  @pytest.mark.asyncio
  async def test_load_template_reads_and_substitutes():
      hass = MagicMock()
      yaml_content = "title: EV Planner {{ vehicle_name }}\nviews: []"
      with patch("os.path.exists", return_value=True), \
           patch("builtins.open", mock_open(read_data=yaml_content)):
          result = await _load_dashboard_template(hass, "car1", "Mi Coche", False)
      assert result["title"] == "EV Planner Mi Coche"
  ```

  VERIFICACIÓN FINAL: `pytest tests/ --cov=custom_components.ev_trip_planner.dashboard --cov-report=term-missing -q` → **100%**

### US-G6: Llevar __init__.py a 100%

- [ ] T082 [US-G6] [VERIFY:TEST] Obtener las 14 líneas sin cubrir en `__init__.py`:
  ```bash
  pytest tests/ --cov=custom_components.ev_trip_planner.__init__ --cov-report=term-missing -q 2>&1 | tail -5
  ```
  `__init__.py` contiene `async_setup_entry` y `async_unload_entry`. Estos pueden testearse parcialmente con `hass = MagicMock()` y `entry = MagicMock()`. Las líneas que interactúan con el event bus real → `# pragma: no cover  # HA lifecycle hook`.

  VERIFICACIÓN FINAL: `pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing -q` → **TOTAL 100%**

### US-G7: Gate final

- [ ] T083 [US-G7] Ejecutar suite completa y verificar que el CI pasa:
  ```bash
  pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing -q
  ```
  **El resultado DEBE mostrar: `TOTAL ... 100%`** y **NO debe mostrar** `FAIL Required test coverage of 100.0% not reached`.

  Si algún módulo no llega al 100%:
  1. Identificar las líneas restantes
  2. Para cada una: ¿cumple las reglas estrictas de pragma? → añadir pragma con razón. ¿No cumple? → escribir test.
  3. Repetir hasta TOTAL = 100%.

- [ ] T084 [US-G7] `pytest tests/ -v` — **todos los tests pasan** (≥1255 passed, 0 failed)
- [ ] T085 [US-G7] `ruff check custom_components/ev_trip_planner/` — 0 violations
- [ ] T086 [US-G7] `mypy --follow-imports=skip custom_components/ev_trip_planner/` — 0 new errors respecto a baseline

---

## Estado final del proyecto

| Metric | Estado |
|--------|--------|
| Phase A (Pure functions) | ✅ Completo |
| Phase B (Protocols) | ✅ Completo |
| Phase C (DI constructor) | ✅ Completo |
| Phase D (Test doubles + MagicMock) | ✅ Completo |
| Phase E (Gates finales) | ✅ Completo |
| Phase F (Coverage módulos refactorizados) | ✅ Completo — 92% global |
| **Phase G (Coverage 100% total proyecto)** | ❌ **PENDIENTE** |
| Tests passing | 1255 ✅ |
| Coverage actual | 92% → meta: 100% |
| CI `fail_under = 100` | ❌ FALLA actualmente |

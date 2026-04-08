# Research: solid-refactor-coverage

## Executive Summary

Refactorizar `trip_manager.py` y `emhass_adapter.py` aplicando SOLID via Protocols para inyección de dependencias — sin reescribir clases en nuevas subclases. Extraer funciones puras (Fase A), definir `TripStorageProtocol` y `EMHASSPublisherProtocol` (Fase B), migrar Layer 1 test doubles a `tests/__init__.py` (Fase D), y arreglar MagicMock() sin spec. La cobertura 100% es consecuencia del buen diseño, no el objetivo directo.

---

## External Research

### SOLID Refactoring Scope (CORREGIDO)

**NO se propone split en subclases nuevas**. El objetivo es inyección de dependencias vía Protocol, no reescritura de las clases existentes.

| Objetivo | Qué hacer |
|----------|-----------|
| **SRP** | Extraer funciones puras a módulos (`calculations.py`, `utils.py`) — las clases siguen intactas |
| **DIP** | Definir `TripStorageProtocol`, `EMHASSPublisherProtocol` — TripManager recibe implementations por constructor |
| **ISP** | Protocols pequeños y enfocados, no split de EMHASSAdapter en IndexManager + PublishEngine |

**Pure functions a extraer** (Fase A — sin HA deps, test directo):
- TripManager: `_validate_hora()`, `_sanitize_recurring_trips()`, `_is_trip_today()`, `_get_trip_time()`, `_get_day_index()`, `_calcular_tasa_carga_soc()`, `_calcular_soc_objetivo_base()`, `_get_charging_power()`
- EMHASSAdapter: `calculate_deferrable_parameters()`, `_calculate_power_profile_from_trips()`, `_generate_schedule_from_trips()`

### Layered Test Doubles Strategy — CORREGIDA

**Capa 1 (`tests/__init__.py`)**: Constantes de datos (`TEST_VEHICLE_ID`, `TEST_CONFIG`, etc.) y factory functions (`create_mock_trip_manager()`, `create_mock_coordinator()`, `setup_mock_ev_config_entry()`). Las factory functions incluyen `patch()` en el boundary de HA internamente.

**Capa 2 (tests individuales)**: Stubs por método que sobreescriben métodos específicos de los factories de Capa 1.

**Capa 3 (`conftest.py`)**: SOLO fixtures `@pytest.fixture` de setup de HA (hass, mock_store, mock_entity_registry, mock_config_entries). **NO hace patches directamente** — usa los helpers de Capa 1.

```
tests/
├── __init__.py          # Capa 1: TEST_*, create_mock_*(), setup_mock_*() CON patch en boundary
├── conftest.py          # Capa 3: @pytest.fixture que llaman a Capa 1 (sin patch directo)
└── test_*.py           # Capa 2: stubs por método
```

### Protocol Patterns

```python
# protocols.py — TripManager recibe por constructor, default a implementación real
class TripStorageProtocol(Protocol):
    async def async_load(self) -> TripData: ...
    async def async_save(self, data: TripData) -> None: ...

class EMHASSPublisherProtocol(Protocol):
    async def async_publish_deferrable_load(self, trip: Dict) -> bool: ...
    async def async_remove_deferrable_load(self, trip_id: str) -> bool: ...
    # NOTE: calculate_deferrable_parameters() es FUNCIÓN PURA → Fase A, no va aquí
```

### MagicMock() Rule

- **`MagicMock(spec=ClaseReal)`** → obligatorio para clases propias del proyecto (`TripManager`, `EMHASSAdapter`, `TripPlannerCoordinator`)
- **`AsyncMock()`** → aceptable para clientes externos con interfaz estable (Store, entity_registry, services)
- **`MagicMock()` sin spec para clase propia** → violación real

---

## Codebase Analysis

### Pure Functions (extractable en Fase A)

**TripManager**:
- Utilidades: `_validate_hora()`, `_sanitize_recurring_trips()`, `_is_trip_today()`, `_get_trip_time()`, `_get_day_index()`
- Cálculos SOC: `_calcular_tasa_carga_soc()`, `_calcular_soc_objetivo_base()`, `_get_charging_power()`
- I/O-bound (NO extraer): `async_setup()`, `_load_trips()`, `_load_trips_yaml()`, `async_save_trips()`, `_save_trips_yaml()`

**EMHASSAdapter**:
- Pure: `calculate_deferrable_parameters()` (líneas 449-524), `_calculate_power_profile_from_trips()` (líneas 1387-1456), `_generate_schedule_from_trips()` (líneas 1457-1535)
- Mixed: `async_publish_deferrable_load()` (líneas 267-358), `async_cleanup_vehicle_indices()` (líneas 1174-1259)

### Test Patterns Issues — CORREGIDO

#### tests/__init__.py — VACÍA

Solo contiene docstring. DEBE contener (Capa 1):
```python
TEST_VEHICLE_ID = "coche1"
TEST_ENTRY_ID = "test_entry_id_abc123"
TEST_CONFIG = {...}
TEST_TRIPS = {...}
TEST_COORDINATOR_DATA = {...}

def create_mock_trip_manager() -> AsyncMock: ...
def create_mock_coordinator(hass, entry=None, trip_manager=None): ...
def create_mock_ev_config_entry(hass, data=None, entry_id=TEST_ENTRY_ID): ...
async def setup_mock_ev_config_entry(hass, config_entry=None, trip_manager=None): ...  # CON patch en boundary
```

#### MagicMock() sin spec — VERIFICAR POR ARCHIVO

El conteo "100+ violations" es impreciso. Hay que verificar archivo por archivo:
- **Violación real**: `MagicMock()` sin spec para `TripManager`, `EMHASSAdapter`, `TripPlannerCoordinator`
- **Aceptable**: `AsyncMock()` para clientes HA (Store, entity_registry) o `MagicMock(spec=HAClass)`

Se requiere verificación con `grep` antes de tasks.md.

#### Fakes/Stubs en conftest.py — CORREGIDO

Los 13 fixtures de conftest.py (`mock_store`, `mock_entity_registry`, `mock_config_entries`, etc.) son **correctos donde están** — son `@pytest.fixture` de infraestructura HA que necesitan lifecycle de pytest.

Lo que SÍ debe migrar a `tests/__init__.py` (Capa 1):
- Constantes de datos: `TEST_VEHICLE_ID`, `TEST_CONFIG`, `TEST_TRIPS`, etc.
- Factory functions: `create_mock_trip_manager()`, `create_mock_coordinator()`, `setup_mock_ev_config_entry()`

### Constraints

**TripManager**: `_emhass_adapter` getter/setter preservado, storage format inmutable, YAML fallback preservado.
**EMHASSAdapter**: Store format inmutable, index assignment algorithm preservado.
**Tests**: Todos existentes deben pasar post-refactor.

---

## Fases Recomendadas (de doc/promptspecrfactor.md)

| Fase | Contenido | Objetivo |
|------|-----------|----------|
| **A** | Extraer funciones puras a `calculations.py`/`utils.py` | 100% coverage sin dobles |
| **B** | Definir `TripStorageProtocol`, `EMHASSPublisherProtocol` en `protocols.py` | DI sin reescribir clases |
| **C** | Injectar protocols en TripManager.__init__ (default a real impl) | Tests pueden usar FakeStorage, FakeEmhass |
| **D** | Limpiar tests existentes (MagicMock sin spec → spec=, migrate a tests/__init__.py) | Alineación con Layered Strategy |

**Nota**: Las fases son incrementales — cada checkpoint verifica tests pasando antes de avanzar.

---

## Feasibility Assessment

| Aspecto | Evaluación | Notas |
|---------|-----------|-------|
| Extracción funciones puras | Alta | Sin HA deps, test directo |
| Protocol DI | Alta | Python typing.Protocol bien soportado |
| MagicMock fix | Media | Requiere verificación archivo por archivo |
| 100% coverage | Media | Con fases A-C completadas, es alcanzable |
| Backward compatibility | Alta | Constraints bien definidos |

---

## Open Questions

1. ¿`VehicleController` necesita su propio Protocol?
2. ¿Schema migration si storage format cambia?
3. ¿YamlStorageAdapter como implementing `TripStorageProtocol`?

---

## Sources

- [TDD_METHODOLOGY.md](../../docs/TDD_METHODOLOGY.md) — Layered Test Doubles Strategy (fuente de verdad)
- [Frigate Test Doubles Pattern](https://github.com/blakeblackshear/frigate-hass-integration/blob/master/tests/__init__.py)
- [Python Typing - Protocols](https://github.com/python/typing/blob/main/docs/reference/protocols.rst)

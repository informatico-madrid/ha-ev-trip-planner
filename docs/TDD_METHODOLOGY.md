# 🧪 Metodología TDD (Test-Driven Development) - EV Trip Planner

**ADN del Desarrollador**: Esta metodología es **OBLIGATORIA** y **NON-NEGOTIABLE**. Siempre que se reinicie el contexto, este documento debe ser leído primero.

---

## 📋 Principios Fundamentales

### 1. **RED → GREEN → REFACTOR**

**Fase RED**: Escribir tests que FALLAN primero
- Antes de escribir cualquier código de producción, escribir el test
- El test debe fallar inicialmente (verificar que el test es válido)
- Si el test pasa inmediatamente, algo está mal (test falso positivo)

**Fase GREEN**: Escribir el código mínimo para que el test PASE
- Implementar solo lo necesario para hacer pasar el test
- No pre-optimizar, no añadir funcionalidad extra
- Los tests deben pasar después de esta fase

**Fase REFACTOR**: Mejorar el código sin cambiar comportamiento
- Una vez que todos los tests pasan, refactorizar si es necesario
- Mantener todos los tests pasando durante el refactor
- Mejorar legibilidad, rendimiento, mantenibilidad

---

## 🎯 Ciclo de Desarrollo TDD (Obligatorio)

### Para CADA Funcionalidad Nueva:

```bash
# PASO 1: Escribir test (RED)
# - Crear archivo de test si no existe
# - Escribir test que describe la funcionalidad esperada
# - Ejecutar test y verificar que FALLA

pytest tests/test_nueva_funcionalidad.py -v
# Resultado esperado: FAILED (1 failed)

# PASO 2: Implementar código mínimo (GREEN)
# - Crear archivo de producción si no existe
# - Escribir el código MÍNIMO necesario
# - Ejecutar test y verificar que PASA

pytest tests/test_nueva_funcionalidad.py -v
# Resultado esperado: PASSED (1 passed)

# PASO 3: Refactorizar (REFACTOR)
# - Mejorar el código si es necesario
# - Verificar que todos los tests siguen pasando

pytest tests/ -v
# Resultado esperado: Todos los tests pasan

# PASO 4: Commit atómico
git add tests/test_nueva_funcionalidad.py custom_components/...
git commit -m "feat: [descripción] - TDD cycle complete"
```

---

## 📦 Estructura de Tests

### Convenciones de Nomenclatura:

- **Archivos de test**: `test_[modulo].py`
- **Funciones de test**: `async def test_[escenario]_[condicion]()`
- **Fixtures**: `@pytest.fixture` en `conftest.py`
- **Test doubles compartidos**: en `tests/__init__.py` (NO en `conftest.py`)

---

## 🔍 Tipos de Tests Requeridos

### 1. **Unit Tests** (Cobertura > 80%)

**Qué testear:**
- Lógica de negocio (cálculos, validaciones)
- Transformaciones de datos
- Manejo de errores y edge cases

**Ejemplo:**
```python
async def test_calculate_kwh_needed_valid_input(hass):
    """Test kWh calculation with valid distance and consumption."""
    # Arrange
    distance_km = 100
    consumption_kwh_per_km = 0.15
    
    # Act
    result = calculate_kwh_needed(distance_km, consumption_kwh_per_km)
    
    # Assert
    assert result == 15.0
```

### 2. **Integration Tests**

**Qué testear:**
- Interacción entre componentes
- Flujos completos (ej: crear viaje → publicar en EMHASS → activar carga)
- Comunicación con Home Assistant (services, states)

**Ejemplo:**
```python
async def test_trip_creation_triggers_emhass_publish(hass):
    """Test that creating a trip publishes to EMHASS."""
    # Arrange: Setup vehicle and trip manager
    
    # Act: Create trip via service call
    
    # Assert: Verify EMHASS sensor was created with correct attributes
```

### 3. **Config Flow Tests** (CRÍTICO)

**Qué testear:**
- Validación de entrada del usuario
- Transiciones entre pasos
- Manejo de errores (sensores no existen, formato inválido)
- Creación de entrada de configuración

**Ejemplo:**
```python
async def test_config_flow_invalid_sensor(hass):
    """Test config flow rejects non-existent sensor."""
    # Act: Submit config with invalid sensor entity
    
    # Assert: Error shown, flow doesn't advance
    assert result["errors"]["base"] == "sensor_not_found"
```

---

## ✅ Checklist TDD por Funcionalidad

Antes de marcar una tarea como completada, verificar:

- [ ] **Test escrito** (RED)
  - [ ] Test describe el comportamiento esperado
  - [ ] Test falla inicialmente (verificado)
  - [ ] Test cubre casos normales y edge cases

- [ ] **Código implementado** (GREEN)
  - [ ] Código mínimo para pasar el test
  - [ ] Test pasa después de implementación
  - [ ] No hay código muerto

- [ ] **Refactorización** (REFACTOR)
  - [ ] Código limpio y legible
  - [ ] Nombres descriptivos
  - [ ] Comentarios solo donde sea necesario
  - [ ] Todos los tests siguen pasando

- [ ] **Test Doubles correctos**
  - [ ] Usa `MagicMock(spec=ClaseReal)` — nunca `MagicMock()` sin `spec` para clases propias
  - [ ] Fakes/Stubs compartidos están en `tests/__init__.py`
  - [ ] Patches solo en boundaries externos (nunca dentro del código de producción)

- [ ] **Documentación**
  - [ ] Docstrings en funciones públicas
  - [ ] Comentarios en lógica compleja
  - [ ] README actualizado si es feature visible al usuario

- [ ] **Commit**
  - [ ] Mensaje claro: `feat/fix: descripción - TDD cycle`
  - [ ] Incluye archivos de test y producción
  - [ ] No incluye archivos temporales o de debug

---

## 🚨 Prohibiciones TDD (NO hacer)

❌ **NUNCA** escribir código de producción sin test previo
❌ **NUNCA** escribir tests después del código (no es TDD)
❌ **NUNCA** añadir funcionalidad que no esté en un test
❌ **NUNCA** hacer commit con tests fallando
❌ **NUNCA** borrar tests sin reemplazarlos con tests equivalentes
❌ **NUNCA** usar `time.sleep()` en tests (usar `asyncio.sleep(0)` o fixtures)
❌ **NUNCA** usar `MagicMock()` sin `spec` para sustituir clases propias del proyecto
❌ **NUNCA** usar `patch()` dentro de código de producción — solo en tests, en los boundaries

---

## 🏗️ Layered Test Doubles Strategy (OBLIGATORIO)

Esta es la estrategia usada por integraciones HACS Platinum/Gold de referencia como [Frigate](https://github.com/blakeblackshear/frigate-hass-integration). Tiene **3 capas obligatorias** que trabajan juntas.

### 📌 Capa 1 — `tests/__init__.py`: Datos y Fakes compartidos

Centraliza todos los datos de test y los helpers de creación de doubles en un único módulo importable. Esto evita duplicación y hace que los tests sean más fáciles de mantener.

```python
# tests/__init__.py  — Patrón Frigate adaptado a ev-trip-planner

from unittest.mock import AsyncMock, MagicMock
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME
from custom_components.ev_trip_planner.const import DOMAIN

# ――― Constantes de test compartidas (Fixtures de datos) ―――
TEST_VEHICLE_ID = "coche1"
TEST_ENTRY_ID = "test_entry_id_abc123"
TEST_URL = "http://emhass.local:5000"

TEST_CONFIG = {
    "vehicle_name": "Coche 1",
    "vehicle_id": TEST_VEHICLE_ID,
    "soc_sensor": "sensor.coche1_soc",
    "battery_capacity_kwh": 60,
    "max_charge_power_kw": 11,
}

TEST_TRIPS = {
    "recurring": [
        {"id": "trip_001", "km": 50, "dia_semana": "lunes", "hora": "08:00"},
        {"id": "trip_002", "km": 30, "dia_semana": "viernes", "hora": "09:00"},
    ],
    "punctual": [
        {"id": "trip_003", "km": 120, "datetime": "2026-05-01T10:00:00"},
    ],
}

TEST_COORDINATOR_DATA = {
    "recurring_trips": {"trip_001": TEST_TRIPS["recurring"][0]},
    "punctual_trips": {"trip_003": TEST_TRIPS["punctual"][0]},
    "kwh_today": 5.2,
    "next_trip": TEST_TRIPS["recurring"][0],
    "soc": 80,
}


# ――― Capa 1: Stub del TripManager (respuestas realistas precargadas) ―――
def create_mock_trip_manager() -> AsyncMock:
    """Create a stub TripManager with realistic pre-configured responses."""
    mock = AsyncMock()
    mock.async_get_recurring_trips = AsyncMock(return_value=TEST_TRIPS["recurring"])
    mock.async_get_punctual_trips = AsyncMock(return_value=TEST_TRIPS["punctual"])
    mock.get_all_trips = MagicMock(return_value=TEST_TRIPS)
    mock.async_add_recurring_trip = AsyncMock(return_value=True)
    mock.async_add_punctual_trip = AsyncMock(return_value=True)
    mock.async_update_trip = AsyncMock(return_value=True)
    mock.async_remove_trip = AsyncMock(return_value=True)
    mock.async_setup = AsyncMock(return_value=None)
    return mock


# ――― Capa 1: Fake del Coordinator (datos en memoria) ―――
def create_mock_coordinator(hass: HomeAssistant, entry=None, trip_manager=None):
    """Create a fake coordinator with in-memory data."""
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator
    coordinator = MagicMock(spec=TripPlannerCoordinator)  # spec OBLIGATORIO
    coordinator.data = dict(TEST_COORDINATOR_DATA)  # copia para mutabilidad
    coordinator.hass = hass
    coordinator._trip_manager = trip_manager or create_mock_trip_manager()
    coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)
    return coordinator


# ――― Capa 1: Config entry fake ―――
def create_mock_ev_config_entry(
    hass: HomeAssistant,
    data: dict | None = None,
    entry_id: str = TEST_ENTRY_ID,
) -> MockConfigEntry:
    """Create and register a mock config entry."""
    config_entry = MockConfigEntry(
        entry_id=entry_id,
        domain=DOMAIN,
        data=data or TEST_CONFIG,
        version=1,
    )
    config_entry.add_to_hass(hass)
    return config_entry


# ――― Capa 3: Setup completo con patch en el boundary de HA ―――
async def setup_mock_ev_config_entry(
    hass: HomeAssistant,
    config_entry=None,
    trip_manager=None,
) -> tuple:
    """Set up a full mock integration entry, patching at the HA boundary."""
    from unittest.mock import patch
    config_entry = config_entry or create_mock_ev_config_entry(hass)
    manager = trip_manager or create_mock_trip_manager()

    with patch(
        "custom_components.ev_trip_planner.TripManager",
        return_value=manager,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry, manager
```

### 📌 Capa 2 — Stubs por método en tests individuales

Cuando un test concreto necesita una respuesta diferente a la del stub base, sobreescribir solo ese método:

```python
# test_trip_manager.py
from tests import create_mock_trip_manager

async def test_add_trip_fails_when_duplicate(hass):
    """Test that adding a duplicate trip raises an error."""
    manager = create_mock_trip_manager()
    # Capa 2: stub específico para este test
    manager.async_add_recurring_trip = AsyncMock(
        side_effect=ValueError("Trip already exists")
    )
    
    with pytest.raises(ValueError, match="Trip already exists"):
        await manager.async_add_recurring_trip({"id": "trip_001", "km": 50})
```

### 📌 Capa 3 — Patch en los boundaries de HA

Usar `patch()` exclusivamente para sustituir factories o dependencias inyectadas por HA, nunca para mockear internals de la integración:

```python
# test_init.py
from tests import setup_mock_ev_config_entry

async def test_integration_setup(hass):
    """Test the integration sets up correctly."""
    config_entry, manager = await setup_mock_ev_config_entry(hass)
    
    # Verificar que HA registró la integración correctamente
    assert hass.data[DOMAIN][config_entry.entry_id] is not None
    
    # Verificar interacción (Mock pattern)
    manager.async_setup.assert_called_once()
```

---

## Test Doubles Reference Table

| Double | When to Use | HA Rule of Gold | Example from ev-trip-planner |
|--------|--------------|-----------------|------------------------------|
| **Fake** | Simplificar dependencias complejas con implementación real en memoria | Usar Fakes cuando necesitas comportamiento pero sin side effects | `coordinator.data = {"kwh_today": 5.0}` — datos reales en memoria |
| **Stub** | Respuestas precargadas para métodos concretos | Stub I/O externo (ficheros, red) que tu código llama pero no debe ejecutar realmente | `async def mock_load(): return {"data": "cached"}` — valor predeterminado |
| **Mock** | Verificar interacciones (call count, argumentos, orden) | **Nunca Mockés la base de datos, filesystem o red en tests de integración** | `coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)` verifica que fue llamado |
| **Spy** | Envolver objeto real, registrar uso sin cambiar comportamiento | Usar Spies cuando necesitas el comportamiento real más verificación | `MagicMock(spec=DataUpdateCoordinator)` envuelve coordinator real, falla en llamadas inesperadas |
| **Fixture** | Proporcionar datos de test u objetos helper; código de setup | Las fixtures son para datos de test y objetos helper, NO para verificar comportamiento | `mock_hass()` fixture crea instancia HA consistente |
| **Patch** | Reemplazar temporalmente atributos/objetos en scope de módulo | Usar `patch()` solo en boundaries (llamadas a subsistemas HA), no dentro de tu código | `patch('custom_components.ev_trip_planner.services.handle_trip_create')` |

### HA Rule of Gold (Strict)

**"Nunca mockear los internals de Home Assistant — solo mockear dependencias externas y boundaries."**

Esto significa:
- ✅ **SIEMPRE mockear**: Servicios externos (EMHASS API, HTTP endpoints), filesystem calls, `hass.loop`, primitivas `asyncio`
- ✅ **NUNCA mockear**: `hass.states`, `hass.services`, `entity_registry.async_entries_for_config_entry` — testear con objetos reales o Fakes
- ⚠️ **CON MODERACIÓN**: Internals de `DataUpdateCoordinator`, config entry APIs — preferir tests de integración
- ❗ **OBLIGATORIO**: Usar siempre `MagicMock(spec=ClaseReal)` — nunca `MagicMock()` sin `spec` para clases propias

### When to Use Each Test Double

| Scenario | Recommended Double | Example |
|----------|-------------------|---------|
| Test service handler delegates to manager | Mock + Spy | `mgr.async_add_recurring_trip = AsyncMock()` then verify called |
| Test that sensor reads coordinator.data | Fake | `coordinator.data = {"kwh_today": 5.0}` |
| Test error handling for missing entry | Stub | `_find_entry_by_vehicle = MagicMock(return_value=None)` |
| Test that exception propagates | Spy | Pass real object, assert exception raised |
| Test with HomeAssistant state | Fixture | `mock_hass()` creates pre-configured hass object |
| Replace a function during test | Patch | `patch('homeassistant.helpers.storage.Store')` |

### Common Mistakes with Test Doubles

| Mistake | Why It's Wrong | Correct Approach |
|---------|----------------|------------------|
| `MagicMock()` without spec | Catches no errors on wrong API usage | Use `MagicMock(spec=RealClass)` or Spy pattern |
| Mocking `hass.states.get()` | Breaks HA's state machine contract | Use real states or `hass.states.get = MagicMock(return_value=real_state)` |
| Stubbing entire class | Test doesn't catch API changes | Stub only the method being called |
| Mock in unit test that should be integration | Tests don't catch real integration bugs | Use real objects for HA boundaries |
| Fakes/Stubs in conftest.py | Hard to import from other test files | Define in `tests/__init__.py` for reuse |

### ev-trip-planner Test Double Examples

```python
# MOCK: Verify async_config_entry_first_refresh is called
coordinator.async_config_entry_first_refresh = AsyncMock()

# FAKE: In-memory coordinator data
coordinator.data = {"recurring_trips": {}, "kwh_today": 0.0}

# SPY: Verify method was called on real object
real_trip_manager.async_add_recurring_trip = AsyncMock(wraps=original_method)

# STUB: Provide fixed response
trip_manager.async_get_recurring_trips = AsyncMock(return_value=[])

# PATCH: Temporarily replace Store
with patch('homeassistant.helpers.storage.Store', return_value=mock_store):
    await async_cleanup_stale_storage(hass, vehicle_id)

# FIXTURE: Provide test data (en tests/__init__.py, no en conftest.py)
TEST_TRIPS = {"recurring": [{"id": "trip_001", "km": 50}], "punctual": []}
```

---

## 🔄 Flujo de Trabajo Diario

### Al empezar a trabajar:

```bash
# 1. Verificar estado actual
git status

# 2. Ejecutar todos los tests para asegurar baseline verde
pytest tests/ -v
# Resultado: Todos los tests deben pasar

# 3. Si hay tests fallando, arreglarlos ANTES de añadir nueva funcionalidad
```

### Durante el desarrollo:

```bash
# 1. Escribir test (RED)
# ... editar tests/test_nueva_funcionalidad.py ...

# 2. Ejecutar test y verificar que falla
pytest tests/test_nueva_funcionalidad.py::test_nuevo_test -v
# Resultado: FAILED (esperado)

# 3. Implementar código (GREEN)
# ... editar custom_components/ev_trip_planner/...

# 4. Ejecutar test y verificar que pasa
pytest tests/test_nueva_funcionalidad.py::test_nuevo_test -v
# Resultado: PASSED (esperado)

# 5. Ejecutar TODOS los tests para evitar regresiones
pytest tests/ -v
# Resultado: Todos deben pasar

# 6. Refactorizar si es necesario (REFACTOR)
# ... mejorar código ...

# 7. Verificar tests siguen pasando
pytest tests/ -v
```

### Al finalizar:

```bash
# 1. Ver cobertura
pytest tests/ --cov=custom_components/ev_trip_planner --cov-report=term-missing

# 2. Commit atómico
git add tests/ custom_components/
git commit -m "feat: nueva funcionalidad - TDD cycle complete"

# 3. Push a feature branch
git push origin feature/nueva-funcionalidad
```

---

## 📚 Recursos y Ejemplos

### Integración de referencia — Layered Test Doubles:

- **Frigate** (patrón usado en esta metodología): https://github.com/blakeblackshear/frigate-hass-integration/blob/master/tests/__init__.py
  - `tests/__init__.py` centraliza Fakes/Stubs: `TEST_CONFIG`, `TEST_STATS`, `create_mock_frigate_client()`
  - `conftest.py` solo tiene pytest fixtures ligeras
  - `patch()` solo en `setup_mock_frigate_config_entry()` — boundary de HA

### Ejemplos de Tests en el Proyecto:

- `tests/test_config_flow_milestone3.py` - Tests de config flow Milestone 3
- `tests/test_trip_manager.py` - Tests de gestión de viajes
- `tests/test_sensors.py` - Tests de sensores

### Patrones Comunes:

**Mock de Home Assistant (usando pytest-homeassistant-custom-component):**
```python
# conftest.py — solo fixtures ligeras
@pytest.fixture
def mock_config_entry(hass):
    """Return a mock config entry registered in hass."""
    from tests import create_mock_ev_config_entry
    return create_mock_ev_config_entry(hass)
```

**Test de Servicio con Layered Strategy:**
```python
# test_services.py
from tests import create_mock_trip_manager, setup_mock_ev_config_entry

async def test_service_add_trip(hass):
    """Test add trip service delegates to TripManager."""
    # Arrange — usar helpers de tests/__init__.py
    config_entry, manager = await setup_mock_ev_config_entry(hass)
    
    # Act
    await hass.services.async_call(
        DOMAIN, "add_recurring_trip",
        {"vehicle_id": "coche1", "km": 50, "dia_semana": "lunes"},
        blocking=True,
    )
    
    # Assert — Mock pattern: verificar que se delego correctamente
    manager.async_add_recurring_trip.assert_called_once()
```

---

## 🎯 Recordatorio Final

**ESTA METODOLOGÍA ES TU ADN COMO DESARROLLADOR**

- No se trata de "escribir tests", se trata de "diseñar software a través de tests"
- Los tests son la especificación ejecutable del comportamiento esperado
- Si no hay test, la funcionalidad no existe (no importa si el código está escrito)
- Los test doubles mal usados (`MagicMock()` sin `spec`) son peores que no tener tests — dan falsa confianza
- **Siempre que reinicies tu contexto, lee este documento primero**

---

**Documento Version**: 2.0
**Last Updated**: 2026-04-08
**Status**: MANDATORY - Must be followed for all development

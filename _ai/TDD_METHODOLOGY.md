# 🧪 TDD Methodology (Test-Driven Development) - EV Trip Planner

**Developer DNA**: This methodology is **MANDATORY** and **NON-NEGOTIABLE**. Whenever the context is restarted, this document must be read first.

---

## 📋 Fundamental Principles

### 1. **RED → GREEN → REFACTOR**

**RED Phase**: Write tests that FAIL first
- Before writing any production code, write the test
- The test should fail initially (verify the test is valid)
- If the test passes immediately, something is wrong (false positive test)

**GREEN Phase**: Write the minimal code to make the test PASS
- Implement only what is necessary to pass the test
- Do not over-optimize, do not add extra functionality
- Tests should pass after this phase

**REFACTOR Phase**: Improve code without changing behavior
- Once all tests pass, refactor if necessary
- Keep all tests passing during refactoring
- Improve readability, performance, maintainability

---

## 🎯 TDD Development Cycle (Mandatory)

### For EACH New Feature:

```bash
# STEP 1: Write test (RED)
# - Create test file if it doesn't exist
# - Write test that describes expected behavior
# - Run test and verify it FAILS

pytest tests/test_new_feature.py -v
# Expected result: FAILED (1 failed)

# STEP 2: Implement minimal code (GREEN)
# - Create production file if it doesn't exist
# - Write the MINIMAL code necessary
# - Run test and verify it PASSES

pytest tests/test_new_feature.py -v
# Expected result: PASSED (1 passed)

# STEP 3: Refactor (REFACTOR)
# - Improve code if necessary
# - Verify all tests still pass

pytest tests/ -v
# Expected result: All tests pass

# STEP 4: Atomic commit
git add tests/test_new_feature.py custom_components/...
git commit -m "feat: [description] - TDD cycle complete"
```

---

## 📦 Test Structure

### Naming Conventions:

- **Test files**: `test_[module].py`
- **Test functions**: `async def test_[scenario]_[condition]()`
- **Fixtures**: `@pytest.fixture` in `conftest.py`
- **Shared test doubles**: in `tests/__init__.py` (NOT in `conftest.py`)

---

## 🔍 Required Test Types

### 1. **Unit Tests** (Coverage > 80%)

**What to test:**
- Business logic (calculations, validations)
- Data transformations
- Error handling and edge cases

**Example:**
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

**What to test:**
- Component interaction
- Complete flows (e.g., create trip → publish to EMHASS → activate charging)
- Communication with Home Assistant (services, states)

**Example:**
```python
async def test_trip_creation_triggers_emhass_publish(hass):
    """Test that creating a trip publishes to EMHASS."""
    # Arrange: Setup vehicle and trip manager
    
    # Act: Create trip via service call
    
    # Assert: Verify EMHASS sensor was created with correct attributes
```

### 3. **Config Flow Tests** (CRITICAL)

**What to test:**
- User input validation
- Step transitions
- Error handling (sensors don't exist, invalid format)
- Configuration entry creation

**Example:**
```python
async def test_config_flow_invalid_sensor(hass):
    """Test config flow rejects non-existent sensor."""
    # Act: Submit config with invalid sensor entity
    
    # Assert: Error shown, flow doesn't advance
    assert result["errors"]["base"] == "sensor_not_found"
```

---

## ✅ TDD Checklist per Feature

Before marking a task as complete, verify:

- [ ] **Test written** (RED)
  - [ ] Test describes expected behavior
  - [ ] Test fails initially (verified)
  - [ ] Test covers normal cases and edge cases

- [ ] **Code implemented** (GREEN)
  - [ ] Minimal code to pass the test
  - [ ] Test passes after implementation
  - [ ] No dead code

- [ ] **Refactoring** (REFACTOR)
  - [ ] Clean and readable code
  - [ ] Descriptive names
  - [ ] Comments only where necessary
  - [ ] All tests still passing

- [ ] **Correct Test Doubles**
  - [ ] Uses `MagicMock(spec=RealClass)` — never `MagicMock()` without `spec` for own classes
  - [ ] Shared Fakes/Stubs are in `tests/__init__.py`
  - [ ] Patches only at external boundaries (never inside production code)

- [ ] **Documentation**
  - [ ] Docstrings in public functions
  - [ ] Comments in complex logic
  - [ ] README updated if user-visible feature

- [ ] **Commit**
  - [ ] Clear message: `feat/fix: description - TDD cycle`
  - [ ] Includes test and production files
  - [ ] Does not include temporary or debug files

---

## 🚨 TDD Prohibitions (Do NOT do)

❌ **NEVER** write production code without prior test
❌ **NEVER** write tests after code (this is not TDD)
❌ **NEVER** add functionality not in a test
❌ **NEVER** commit with failing tests
❌ **NEVER** delete tests without replacing them with equivalent tests
❌ **NEVER** use `time.sleep()` in tests (use `asyncio.sleep(0)` or fixtures)
❌ **NEVER** use `MagicMock()` without `spec` to substitute project classes
❌ **NEVER** use `patch()` inside production code — only in tests, at boundaries

---

## 🏗️ Layered Test Doubles Strategy (MANDATORY)

This is the strategy used by Platinum/Gold HACS reference integrations like [Frigate](https://github.com/blakeblackshear/frigate-hass-integration). It has **3 mandatory layers** that work together.

### 📌 Layer 1 — `tests/__init__.py`: Shared data and Fakes

Centralizes all test data and test double creation helpers in a single importable module. This avoids duplication and makes tests easier to maintain.

```python
# tests/__init__.py  — Frigate pattern adapted for ev-trip-planner

from unittest.mock import AsyncMock, MagicMock
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME
from custom_components.ev_trip_planner.const import DOMAIN

# ――― Shared test constants (Data Fixtures) ―――
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
        {"id": "trip_001", "km": 50, "day_of_week": "monday", "time": "08:00"},
        {"id": "trip_002", "km": 30, "day_of_week": "friday", "time": "09:00"},
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


# ――― Layer 1: TripManager Stub (realistic pre-loaded responses) ―――
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


# ――― Layer 1: Coordinator Fake (in-memory data) ―――
def create_mock_coordinator(hass: HomeAssistant, entry=None, trip_manager=None):
    """Create a fake coordinator with in-memory data."""
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator
    coordinator = MagicMock(spec=TripPlannerCoordinator)  # spec MANDATORY
    coordinator.data = dict(TEST_COORDINATOR_DATA)  # copy for mutability
    coordinator.hass = hass
    coordinator._trip_manager = trip_manager or create_mock_trip_manager()
    coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)
    return coordinator


# ――― Layer 1: Fake config entry ―――
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


# ――― Layer 3: Full setup with patch at HA boundary ―――
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

### 📌 Layer 2 — Per-method Stubs in individual tests

When a specific test needs a different response than the base stub, override only that method:

```python
# test_trip_manager.py
from tests import create_mock_trip_manager

async def test_add_trip_fails_when_duplicate(hass):
    """Test that adding a duplicate trip raises an error."""
    manager = create_mock_trip_manager()
    # Layer 2: test-specific stub
    manager.async_add_recurring_trip = AsyncMock(
        side_effect=ValueError("Trip already exists")
    )
    
    with pytest.raises(ValueError, match="Trip already exists"):
        await manager.async_add_recurring_trip({"id": "trip_001", "km": 50})
```

### 📌 Layer 3 — Patch at HA boundaries

Use `patch()` exclusively for substituting factories or dependencies injected by HA, never to mock integration internals:

```python
# test_init.py
from tests import setup_mock_ev_config_entry

async def test_integration_setup(hass):
    """Test the integration sets up correctly."""
    config_entry, manager = await setup_mock_ev_config_entry(hass)
    
    # Verify HA registered the integration correctly
    assert hass.data[DOMAIN][config_entry.entry_id] is not None
    
    # Verify interaction (Mock pattern)
    manager.async_setup.assert_called_once()
```

---

## Test Doubles Reference Table

| Double | When to Use | HA Rule of Gold | Example from ev-trip-planner |
|--------|--------------|-----------------|------------------------------|
| **Fake** | Simplify complex dependencies with real in-memory implementation | Use Fakes when you need behavior but no side effects | `coordinator.data = {"kwh_today": 5.0}` — real data in memory |
| **Stub** | Preloaded responses for specific methods | Stub external I/O (files, network) that your code calls but should not actually execute | `async def mock_load(): return {"data": "cached"}` — default value |
| **Mock** | Verify interactions (call count, arguments, order) | **Never Mock the database, filesystem or network in integration tests** | `coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)` verifies it was called |
| **Spy** | Wrap real object, record usage without changing behavior | Use Spies when you need real behavior plus verification | `MagicMock(spec=DataUpdateCoordinator)` wraps real coordinator, fails on unexpected calls |
| **Fixture** | Provide test data or helper objects; setup code | Fixtures are for test data and helper objects, NOT for verifying behavior | `mock_hass()` fixture creates consistent HA instance |
| **Patch** | Temporarily replace attributes/objects in module scope | Use `patch()` only at boundaries (calls to HA subsystems), not inside your code | `patch('custom_components.ev_trip_planner.services.handle_trip_create')` |

### HA Rule of Gold (Strict)

**"Never mock Home Assistant internals — only mock external dependencies and boundaries."**

This means:
- ✅ **ALWAYS mock**: External services (EMHASS API, HTTP endpoints), filesystem calls, `hass.loop`, `asyncio` primitives
- ✅ **NEVER mock**: `hass.states`, `hass.services`, `entity_registry.async_entries_for_config_entry` — test with real objects or Fakes
- ⚠️ **WITH MODERATION**: `DataUpdateCoordinator` internals, config entry APIs — prefer integration tests
- ❗ **MANDATORY**: Always use `MagicMock(spec=RealClass)` — never `MagicMock()` without `spec` for own classes

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

# FIXTURE: Provide test data (in tests/__init__.py, not in conftest.py)
TEST_TRIPS = {"recurring": [{"id": "trip_001", "km": 50}], "punctual": []}
```

---

## 🔄 Daily Workflow

### When starting work:

```bash
# 1. Check current status
git status

# 2. Run all tests to ensure green baseline
pytest tests/ -v
# Result: All tests must pass

# 3. If tests are failing, fix them BEFORE adding new functionality
```

### During development:

```bash
# 1. Write test (RED)
# ... edit tests/test_new_feature.py ...

# 2. Run test and verify it fails
pytest tests/test_new_feature.py::test_new_test -v
# Result: FAILED (expected)

# 3. Implement code (GREEN)
# ... edit custom_components/ev_trip_planner/...

# 4. Run test and verify it passes
pytest tests/test_new_feature.py::test_new_test -v
# Result: PASSED (expected)

# 5. Run ALL tests to prevent regressions
pytest tests/ -v
# Result: All must pass

# 6. Refactor if necessary (REFACTOR)
# ... improve code ...

# 7. Verify tests still pass
pytest tests/ -v
```

### When finishing:

```bash
# 1. Check coverage
pytest tests/ --cov=custom_components/ev_trip_planner --cov-report=term-missing

# 2. Atomic commit
git add tests/ custom_components/
git commit -m "feat: new feature - TDD cycle complete"

# 3. Push to feature branch
git push origin feature/new-feature
```

---

## 📚 Resources and Examples

### Reference Integration — Layered Test Doubles:

- **Frigate** (pattern used in this methodology): https://github.com/blakeblackshear/frigate-hass-integration/blob/master/tests/__init__.py
  - `tests/__init__.py` centralizes Fakes/Stubs: `TEST_CONFIG`, `TEST_STATS`, `create_mock_frigate_client()`
  - `conftest.py` only has lightweight pytest fixtures
  - `patch()` only in `setup_mock_frigate_config_entry()` — HA boundary

### Test Examples in the Project:

- `tests/test_config_flow_milestone3.py` - Milestone 3 config flow tests
- `tests/test_trip_manager.py` - Trip management tests
- `tests/test_sensors.py` - Sensor tests

### Common Patterns:

**Home Assistant Mock (using pytest-homeassistant-custom-component):**
```python
# conftest.py — only lightweight fixtures
@pytest.fixture
def mock_config_entry(hass):
    """Return a mock config entry registered in hass."""
    from tests import create_mock_ev_config_entry
    return create_mock_ev_config_entry(hass)
```

**Service Test with Layered Strategy:**
```python
# test_services.py
from tests import create_mock_trip_manager, setup_mock_ev_config_entry

async def test_service_add_trip(hass):
    """Test add trip service delegates to TripManager."""
    # Arrange — use helpers from tests/__init__.py
    config_entry, manager = await setup_mock_ev_config_entry(hass)
    
    # Act
    await hass.services.async_call(
        DOMAIN, "add_recurring_trip",
        {"vehicle_id": "coche1", "km": 50, "day_of_week": "monday"},
        blocking=True,
    )
    
    # Assert — Mock pattern: verify delegation
    manager.async_add_recurring_trip.assert_called_once()
```

---

## 🎯 Final Reminder

**THIS METHODOLOGY IS YOUR DEVELOPER DNA**

- It is not about "writing tests", it is about "designing software through tests"
- Tests are the executable specification of expected behavior
- If there is no test, the functionality does not exist (it does not matter if the code is written)
- Misused test doubles (`MagicMock()` without `spec`) are worse than no tests — they give false confidence
- **Whenever you restart your context, read this document first**

---

**Document Version**: 2.0
**Last Updated**: 2026-04-08
**Status**: MANDATORY - Must be followed for all development

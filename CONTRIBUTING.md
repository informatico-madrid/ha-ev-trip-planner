# 🐍 HOME ASSISTANT - INTEGRATION DEVELOPMENT

## 📚 Conventions and Best Practices

### Official Sources
- **Official documentation**: https://developers.home-assistant.io/
- **Architecture Decision Records (ADRs)**: https://github.com/home-assistant/architecture
- **Integration Quality Scale**: https://www.home-assistant.io/docs/quality_scale/
- **Core repository**: https://github.com/home-assistant/core

---

## 🏗️ PROJECT STRUCTURE

### Standard integration structure:

```
custom_components/
└── ev_trip_planner/
    ├── __init__.py              # Integration entry point
    ├── manifest.json            # Metadata (REQUIRED)
    ├── const.py                 # Global constants
    ├── config_flow.py           # UI configuration (optional but recommended)
    ├── __init__.py              # Entry point + Coordinator logic
    │
    ├── sensor.py                # Platform: Sensors
    ├── binary_sensor.py         # Platform: Binary sensors
    ├── switch.py                # Platform: Switches
    ├── button.py                # Platform: Buttons
    ├── calendar.py              # Platform: Calendar
    │
    ├── services.yaml            # Service definitions
    ├── strings.json             # UI strings (English)
    │
    ├── translations/            # Translations
    │   ├── en.json
    │   └── es.json
    │
    └── tests/                   # Unit tests
        ├── __init__.py
        ├── conftest.py
        └── test_*.py
```

---

## 🎨 CODE STYLE

### 1. Python Style Guide

Home Assistant follows **PEP 8** with some specifics:

#### Required tools:
```bash
# Formatter
black custom_components/ev_trip_planner/

# Linter
pylint custom_components/ev_trip_planner/

# Type checker
mypy custom_components/ev_trip_planner/

# Import sorter
isort custom_components/ev_trip_planner/
```

#### Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.pylint.MASTER]
py-version = "3.11"

[tool.pylint.FORMAT]
max-line-length = 88

[tool.mypy]
python_version = "3.11"
show_error_codes = true
follow_imports = "silent"
strict_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
```

---

### 2. HA-specific Conventions

#### Ordered imports:
```python
"""Module docstring."""
from __future__ import annotations  # ALWAYS first

import asyncio  # Standard library
import logging
from typing import Any

import voluptuous as vol  # Third party

from homeassistant.components.sensor import SensorEntity  # HA core
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN  # Local imports
```

#### Logging:
```python
import logging

_LOGGER = logging.getLogger(__name__)  # ALWAYS at module start

# Usage:
_LOGGER.debug("Debug info: %s", data)
_LOGGER.info("Setup complete")
_LOGGER.warning("Warning: %s", issue)
_LOGGER.error("Error occurred: %s", error)
```

#### Type Hints (MANDATORY since HA 2023.x):
```python
from typing import Any
from homeassistant.core import HomeAssistant

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry
) -> bool:
    """Set up integration from config entry."""
    return True
```

---

## 🏛️ ARCHITECTURE

### 1. Data Update Coordinator Pattern (RECOMMENDED)

```python
# coordinator.py
from datetime import timedelta
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

class EVTripPlannerCoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates."""
    
    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.config = config
    
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API/sensors."""
        try:
            # Your logic here
            return {"next_trip": ..., "kwh_needed": ...}
        except Exception as err:
            raise UpdateFailed(f"Error updating data: {err}") from err
```

### 2. Entities (Sensors, Switches, etc.)

```python
# sensor.py
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

class EVTripPlannerSensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor."""
    
    def __init__(self, coordinator, config_entry, sensor_type):
        """Initialize sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{config_entry.data['vehicle_name']} {sensor_type}"
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._sensor_type = sensor_type
    
    @property
    def native_value(self):
        """Return sensor value."""
        return self.coordinator.data.get(self._sensor_type)
    
    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": self.config_entry.data["vehicle_name"],
            "manufacturer": "EV Trip Planner",
            "model": "Trip Manager",
        }
```

### 3. Async First (MANDATORY)

```python
# ✅ CORRECT
async def async_setup_entry(hass, entry):
    """Set up from config entry."""
    coordinator = EVTripPlannerCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

# ❌ INCORRECT
def setup_entry(hass, entry):
    """Don't use sync functions."""
    pass
```

---

## 🧪 TESTING

### 1. Test Structure

Home Assistant uses **pytest** and **pytest-homeassistant-custom-component**

```python
# tests/conftest.py
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return MockConfigEntry(
        domain="ev_trip_planner",
        data={
            "vehicle_name": "Test Vehicle",
            "soc_sensor": "sensor.test_soc",
            "battery_capacity_kwh": 50,
        },
    )
```

```python
# tests/test_sensor.py
import pytest
from homeassistant.core import HomeAssistant
from custom_components.ev_trip_planner.const import DOMAIN

async def test_sensor_setup(hass: HomeAssistant, mock_config_entry):
    """Test sensor setup."""
    mock_config_entry.add_to_hass(hass)
    
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    
    state = hass.states.get("sensor.test_vehicle_next_trip")
    assert state is not None
```

---

### 2. Test Doubles Strategy (MANDATORY)

We follow the **Layered Test Doubles Strategy** used by reference HACS Platinum/Gold integrations (e.g., [Frigate](https://github.com/blakeblackshear/frigate-hass-integration)). The strategy has **3 mandatory layers**:

#### Layer 1 — Fake of external system (in `tests/__init__.py`)
Shared data and helpers that simulate external system behavior with **real in-memory implementation**. Not mocks — they have behavior.

```python
# tests/__init__.py
from unittest.mock import AsyncMock

TEST_CONFIG = {
    "vehicle_name": "Test EV",
    "soc_sensor": "sensor.test_soc",
    "battery_capacity_kwh": 60,
}

TEST_TRIPS = {
    "recurring": [{"id": "trip_001", "km": 50, "day_of_week": "monday"}],
    "punctual": [],
}

def create_mock_trip_manager() -> AsyncMock:
    """Create a mock TripManager with realistic responses (Stub pattern)."""
    mock = AsyncMock()
    mock.async_get_recurring_trips = AsyncMock(return_value=TEST_TRIPS["recurring"])
    mock.async_get_punctual_trips = AsyncMock(return_value=TEST_TRIPS["punctual"])
    mock.async_add_recurring_trip = AsyncMock(return_value=True)
    return mock

def create_mock_coordinator(hass, entry, trip_manager=None):
    """Create a coordinator with pre-configured fake data (Fake pattern)."""
    from unittest.mock import MagicMock
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator
    coordinator = MagicMock(spec=TripPlannerCoordinator)
    coordinator.data = {"recurring_trips": {}, "kwh_today": 0.0, "next_trip": None}
    coordinator.hass = hass
    coordinator._trip_manager = trip_manager or create_mock_trip_manager()
    return coordinator
```

#### Layer 2 — Stub for method responses
For error handling tests or specific responses, stub only the concrete method:

```python
# In the individual test
trip_manager.async_get_recurring_trips = AsyncMock(return_value=[])
trip_manager.async_add_recurring_trip = AsyncMock(side_effect=ValueError("Trip exists"))
```

#### Layer 3 — Patch at HA boundary
Use `patch()` only at **external boundaries** — never inside your own production code:

```python
async def setup_mock_config_entry(hass, config_entry=None, trip_manager=None):
    """Set up a mock config entry injecting the fake manager at the HA boundary."""
    config_entry = config_entry or create_mock_ev_config_entry(hass)
    manager = trip_manager or create_mock_trip_manager()

    with patch(
        "custom_components.ev_trip_planner.TripManager",
        return_value=manager,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry
```

---

### 3. Test Doubles Table — When to use each

| Type | When to use | Example in ev-trip-planner |
|------|-------------|----------------------------|
| **Fake** | Complex dependency with simplified real behavior | `coordinator.data = {"kwh_today": 5.0}` — real data in memory |
| **Stub** | Fixed response for a concrete method | `mgr.async_get_recurring_trips = AsyncMock(return_value=[])` |
| **Mock** | Verify an interaction occurred (call count, args) | `mgr.async_add_recurring_trip = AsyncMock()` + `assert_called_once_with(...)` |
| **Spy** | Wrap real object and verify without changing behavior | `MagicMock(spec=TripManager, wraps=real_manager)` |
| **Fixture** | Reusable test data and helper objects | `TEST_CONFIG`, `TEST_TRIPS` in `tests/__init__.py` |
| **Patch** | Replace at external boundary (HA factory) | `patch('custom_components.ev_trip_planner.TripManager', ...)` |

---

### 4. HA Rule of Gold (STRICT)

> **"Never mock Home Assistant internals — only mock external dependencies and boundaries."**

- ✅ **ALWAYS mock**: External APIs (EMHASS API, HTTP), filesystem calls, `hass.loop`
- ✅ **NEVER mock**: `hass.states`, `hass.services`, `entity_registry` — use real objects or Fakes
- ✅ **USE `MagicMock(spec=RealClass)`**: Never `MagicMock()` without `spec` to substitute own classes — the `spec` catches API errors
- ⚠️ **WITH MODERATION**: `DataUpdateCoordinator` internals, config entry APIs — prefer integration tests

```python
# ❌ INCORRECT — MagicMock without spec doesn't catch API errors
coordinator = MagicMock()
coordinator.non_existent_method()  # No failure — false positive

# ✅ CORRECT — MagicMock with spec catches nonexistent methods
from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator
coordinator = MagicMock(spec=TripPlannerCoordinator)
coordinator.non_existent_method()  # AttributeError — catches the error
```

---

### 5. Minimum Coverage

Home Assistant expects:
- **> 90% coverage** for quality integrations
- Tests for all public methods
- Integration and unit tests

```bash
# Run tests
pytest tests/ --cov=custom_components/ev_trip_planner --cov-report=html

# View coverage
open htmlcov/index.html
```

---

## 📦 DEPENDENCY MANAGEMENT

### manifest.json requirements:

```json
{
  "domain": "ev_trip_planner",
  "name": "EV Trip Planner",
  "codeowners": ["@informatico-madrid"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/informatico-madrid/ha-ev-trip-planner",
  "iot_class": "calculated",
  "requirements": [],
  "version": "0.1.0"
}
```

**Important**: 
- DO NOT add unnecessary requirements
- HA prefers using built-in libraries
- If you need something external, it must be on PyPI

---

## 🔄 DEVELOPMENT WORKFLOW

### Recommended workflow:

```bash
# 1. Create feature branch
git checkout -b feature/trip-storage

# 2. Develop with auto-formatting
# (configure VSCode for format on save)

# 3. Before commit: verify
black custom_components/ev_trip_planner/
isort custom_components/ev_trip_planner/
pylint custom_components/ev_trip_planner/
mypy custom_components/ev_trip_planner/

# 4. Run tests
pytest tests/ -v

# 5. Commit
git add .
git commit -m "feat: add trip storage functionality

- Implement JSON storage for trips
- Add CRUD services
- Tests for trip manager"

# 6. Push and merge
git push origin feature/trip-storage
```

### Conventional Commits (Recommended):

```
feat: new functionality
fix: bug fix
docs: documentation changes
style: formatting, no code changes
refactor: refactoring without functional changes
test: adding or modifying tests
chore: build, CI changes, etc.
```

---

## 🚀 TDD (Test-Driven Development)

### Does the HA community use it?

**Answer**: **Yes, partially**

- **HA Core**: Yes, strict TDD (tests first)
- **Community integrations**: Flexible, but tests are mandatory
- **HACS**: Requires tests for Quality Scale Platinum/Gold

### Recommended approach for our project:

**Hybrid - Test During Development**:

```python
# 1. Write basic test
async def test_add_trip(hass, coordinator):
    """Test adding a trip."""
    result = await coordinator.add_trip({
        "type": "punctual",
        "datetime": "2025-11-19T10:00:00",
        "km": 50,
    })
    assert result is True

# 2. Implement functionality
async def add_trip(self, trip_data):
    """Add a new trip."""
    # Implementation here
    pass

# 3. Run test, iterate until passing
# 4. Refactor
```

**Advantages**:
- Ensures quality from the start
- Living documentation (tests as examples)
- Safe refactoring
- Community appreciates good coverage

---

## 📋 PRE-RELEASE CHECKLIST

### Home Assistant Quality Scale:

#### 🥉 Bronze (Minimum for HACS):
- [x] Valid manifest.json
- [x] Working code
- [ ] Basic README
- [ ] No critical errors

#### 🥈 Silver:
- [ ] Config flow (UI configuration)
- [ ] Basic tests (>50% coverage)
- [ ] Complete documentation
- [ ] Type hints in public functions

#### 🥇 Gold:
- [ ] Comprehensive tests (>80% coverage)
- [ ] Code quality tools (black, pylint, mypy)
- [ ] Async/await correctly implemented
- [ ] Translations (at least EN)
- [ ] Correct test doubles (no `MagicMock()` without `spec`)

#### 💎 Platinum:
- [ ] Tests >90% coverage
- [ ] Performance optimized
- [ ] Extensive documentation
- [ ] Examples and tutorials
- [ ] Layered Test Doubles Strategy implemented (see Testing section)

---

## 🛠️ PROJECT SETUP

### requirements_dev.txt:
```
homeassistant>=2024.1.0
pytest>=7.0.0
pytest-homeassistant-custom-component
black
pylint
mypy
isort
```

### .github/workflows/ci.yml (CI/CD):
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements_dev.txt
      - run: black --check custom_components/
      - run: isort --check custom_components/
      - run: pylint custom_components/
      - run: mypy custom_components/
      - run: pytest tests/ --cov
```

---

## 📝 CODE DOCUMENTATION

### Google-style docstrings (preferred by HA):

```python
def calculate_charging_hours(self, kwh_needed: float, power_kw: float) -> int:
    """Calculate charging hours needed.
    
    Always rounds UP to ensure sufficient charge.
    
    Args:
        kwh_needed: Energy needed in kWh
        power_kw: Charging power in kW
        
    Returns:
        Integer hours needed (ceiling)
        
    Raises:
        ValueError: If power_kw is zero or negative
        
    Example:
        >>> calc.calculate_charging_hours(15.5, 7.2)
        3
    """
    if power_kw <= 0:
        raise ValueError("Charging power must be positive")
    
    import math
    return math.ceil(kwh_needed / power_kw)
```

---

## 🎯 EXECUTIVE SUMMARY

### For our EV Trip Planner project:

1. **Style**: Black + isort + pylint + mypy
2. **Tests**: pytest with >80% coverage target
3. **Architecture**: Data Update Coordinator pattern
4. **Async**: Everything async/await
5. **Type hints**: Mandatory in public functions
6. **Workflow**: Feature branches + Conventional Commits
7. **TDD**: Hybrid (test during development)
8. **Quality Target**: Gold (minimum Silver for v1.0)
9. **Test Doubles**: Layered strategy — see Testing section

---

## 📚 ADDITIONAL RESOURCES

### Reference integrations (well-written code):
- **Frigate** (Layered Test Doubles): https://github.com/blakeblackshear/frigate-hass-integration
- **HACS**: https://github.com/hacs/integration
- **Adaptive Lighting**: https://github.com/basnijholt/adaptive-lighting
- **Spook**: https://github.com/frenck/spook
- **LocalTuya**: https://github.com/rospogrigio/localtuya

### Useful tools:
- **HA Dev Container**: https://github.com/home-assistant/core/tree/dev/.devcontainer
- **Scaffold**: `python -m script.scaffold integration`
- **Validator**: `hass-config-validator`

---

**Last updated**: April 08, 2026

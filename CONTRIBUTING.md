# 🐍 HOME ASSISTANT - DESARROLLO DE INTEGRACIONES

## 📚 Convenciones y Mejores Prácticas

### Fuentes Oficiales
- **Documentación oficial**: https://developers.home-assistant.io/
- **Architecture Decision Records (ADRs)**: https://github.com/home-assistant/architecture
- **Integration Quality Scale**: https://www.home-assistant.io/docs/quality_scale/
- **Core repository**: https://github.com/home-assistant/core

---

## 🏗️ ESTRUCTURA DE PROYECTO

### Estructura estándar de una integración:

```
custom_components/
└── ev_trip_planner/
    ├── __init__.py              # Entry point de la integración
    ├── manifest.json            # Metadata (REQUERIDO)
    ├── const.py                 # Constantes globales
    ├── config_flow.py           # Configuración UI (opcional pero recomendado)
    ├── coordinator.py           # Data Update Coordinator (recomendado)
    │
    ├── sensor.py                # Platform: Sensors
    ├── binary_sensor.py         # Platform: Binary sensors
    ├── switch.py                # Platform: Switches
    ├── button.py                # Platform: Buttons
    ├── calendar.py              # Platform: Calendar
    │
    ├── services.yaml            # Definición de servicios
    ├── strings.json             # UI strings (inglés)
    │
    ├── translations/            # Traducciones
    │   ├── en.json
    │   └── es.json
    │
    └── tests/                   # Tests unitarios
        ├── __init__.py
        ├── conftest.py
        └── test_*.py
```

---

## 🎨 ESTILO DE CÓDIGO

### 1. Python Style Guide

Home Assistant sigue **PEP 8** con algunas particularidades:

#### Herramientas obligatorias:
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

#### Configuración en `pyproject.toml`:
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

### 2. Convenciones específicas HA

#### Imports ordenados:
```python
"""Module docstring."""
from __future__ import annotations  # SIEMPRE primero

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

_LOGGER = logging.getLogger(__name__)  # SIEMPRE al inicio del módulo

# Uso:
_LOGGER.debug("Debug info: %s", data)
_LOGGER.info("Setup complete")
_LOGGER.warning("Warning: %s", issue)
_LOGGER.error("Error occurred: %s", error)
```

#### Type Hints (OBLIGATORIO desde HA 2023.x):
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

## 🏛️ ARQUITECTURA

### 1. Patrón Data Update Coordinator (RECOMENDADO)

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
            # Tu lógica aquí
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

### 3. Async First (OBLIGATORIO)

```python
# ✅ CORRECTO
async def async_setup_entry(hass, entry):
    """Set up from config entry."""
    coordinator = EVTripPlannerCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

# ❌ INCORRECTO
def setup_entry(hass, entry):
    """Don't use sync functions."""
    pass
```

---

## 🧪 TESTING

### 1. Estructura de Tests

Home Assistant usa **pytest** y **pytest-homeassistant-custom-component**

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

### 2. Coverage mínimo

Home Assistant espera:
- **> 90% coverage** para integraciones de calidad
- Tests para todos los métodos públicos
- Tests de integración y unitarios

```bash
# Ejecutar tests
pytest tests/ --cov=custom_components/ev_trip_planner --cov-report=html

# Ver coverage
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
  "requirements": [],  // PyPI packages si necesitas
  "version": "0.1.0"
}
```

**Importante**: 
- NO añadas requirements innecesarios
- HA prefiere usar bibliotecas built-in
- Si necesitas algo externo, debe estar en PyPI

---

## 🔄 DEVELOPMENT WORKFLOW

### Flujo recomendado:

```bash
# 1. Crear rama feature
git checkout -b feature/trip-storage

# 2. Desarrollar con auto-formateo
# (configurar VSCode para format on save)

# 3. Antes de commit: verificar
black custom_components/ev_trip_planner/
isort custom_components/ev_trip_planner/
pylint custom_components/ev_trip_planner/
mypy custom_components/ev_trip_planner/

# 4. Ejecutar tests
pytest tests/ -v

# 5. Commit
git add .
git commit -m "feat: add trip storage functionality

- Implement JSON storage for trips
- Add CRUD services
- Tests for trip manager"

# 6. Push y merge
git push origin feature/trip-storage
```

### Conventional Commits (Recomendado):

```
feat: nueva funcionalidad
fix: corrección de bug
docs: cambios en documentación
style: formateo, sin cambios de código
refactor: refactorización sin cambios funcionales
test: añadir o modificar tests
chore: cambios en build, CI, etc.
```

---

## 🚀 TDD (Test-Driven Development)

### ¿Lo usa la comunidad HA?

**Respuesta**: **Sí, parcialmente**

- **Core de HA**: Sí, TDD estricto (tests primero)
- **Integraciones comunitarias**: Flexible, pero tests obligatorios
- **HACS**: Requiere tests para Quality Scale Platinum/Gold

### Enfoque recomendado para nuestro proyecto:

**Híbrido - Test During Development**:

```python
# 1. Escribir test básico
async def test_add_trip(hass, coordinator):
    """Test adding a trip."""
    result = await coordinator.add_trip({
        "type": "puntual",
        "datetime": "2025-11-19T10:00:00",
        "km": 50,
    })
    assert result is True

# 2. Implementar funcionalidad
async def add_trip(self, trip_data):
    """Add a new trip."""
    # Implementation here
    pass

# 3. Ejecutar test, iterar hasta pasar
# 4. Refactorizar
```

**Ventajas**:
- Aseguras calidad desde inicio
- Documentación viva (tests como ejemplos)
- Refactor seguro
- Comunidad aprecia buen coverage

---

## 📋 CHECKLIST ANTES DE PUBLICAR

### Quality Scale de Home Assistant:

#### 🥉 Bronze (Mínimo para HACS):
- [x] Manifest.json válido
- [x] Código funcional
- [ ] README básico
- [ ] No errores críticos

#### 🥈 Silver:
- [ ] Config flow (UI configuration)
- [ ] Tests básicos (>50% coverage)
- [ ] Documentación completa
- [ ] Type hints en funciones públicas

#### 🥇 Gold:
- [ ] Tests comprehensivos (>80% coverage)
- [ ] Code quality tools (black, pylint, mypy)
- [ ] Async/await correctamente
- [ ] Traducciones (al menos EN)

#### 💎 Platinum:
- [ ] Tests >90% coverage
- [ ] Performance optimizada
- [ ] Documentación extensa
- [ ] Ejemplos y tutoriales

---

## 🛠️ CONFIGURACIÓN DEL PROYECTO

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

## 📝 DOCUMENTACIÓN DE CÓDIGO

### Docstrings estilo Google (preferido por HA):

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

## 🎯 RESUMEN EJECUTIVO

### Para nuestro proyecto EV Trip Planner:

1. **Style**: Black + isort + pylint + mypy
2. **Tests**: pytest con >80% coverage objetivo
3. **Architecture**: Data Update Coordinator pattern
4. **Async**: Todo async/await
5. **Type hints**: Obligatorio en funciones públicas
6. **Workflow**: Feature branches + Conventional Commits
7. **TDD**: Híbrido (test during development)
8. **Quality Target**: Gold (mínimo Silver para v1.0)

---

## 📚 RECURSOS ADICIONALES

### Integraciones de referencia (código bien escrito):
- **HACS**: https://github.com/hacs/integration
- **Adaptive Lighting**: https://github.com/basnijholt/adaptive-lighting
- **Spook**: https://github.com/frenck/spook
- **LocalTuya**: https://github.com/rospogrigio/localtuya

### Herramientas útiles:
- **HA Dev Container**: https://github.com/home-assistant/core/tree/dev/.devcontainer
- **Scaffold**: `python -m script.scaffold integration`
- **Validator**: `hass-config-validator`

---

**Última actualización**: 18 Noviembre 2025

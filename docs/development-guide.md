# Development Guide: HA EV Trip Planner

> Generated: 2026-04-16 | Scan Level: Deep

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ (3.14 target) | Backend code |
| Node.js | 18+ | Frontend tooling, E2E tests |
| Docker | Latest | HA Container test environment |
| Git | Latest | Version control |
| pip | Latest | Python package management |
| npm | Latest | Node package management |

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/informatico-madrid/ha-ev-trip-planner.git
cd ha-ev-trip-planner
```

### 2. Python Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_dev.txt
```

### 3. Node.js Dependencies

```bash
npm install
```

### 4. Docker Test Environment

```bash
docker compose up -d
# Wait for HA to be healthy (~30-60 seconds)
docker compose logs -f  # Monitor startup
```

HA will be available at `http://localhost:8123`

## Development Commands

### Using Make (Recommended)

| Command | Description |
|---------|-------------|
| `make test` | Run all Python unit tests |
| `make test-cover` | Run tests with 100% coverage target |
| `make test-verbose` | Run tests with verbose output |
| `make test-dashboard` | Run tests + open coverage dashboard |
| `make test-e2e` | Run Playwright E2E tests (requires HA running) |
| `make test-e2e-headed` | E2E with visible browser |
| `make test-e2e-debug` | E2E with Playwright inspector |
| `make e2e` | Auto-start HA + run E2E tests |
| `make e2e-headed` | Auto-start HA + E2E with browser |
| `make lint` | Run ruff + pylint |
| `make mypy` | Run type checking |
| `make format` | Format with black + isort |
| `make check` | Run all checks (test + lint + mypy) |
| `make clean` | Clean generated files |

### Direct Commands

```bash
# Python tests
PYTHONPATH=. .venv/bin/python -m pytest tests -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/

# Python tests with coverage
PYTHONPATH=. .venv/bin/python -m pytest tests --cov=custom_components.ev_trip_planner --cov-report=term-missing --cov-report=html --cov-fail-under=100 --ignore=tests/ha-manual/ --ignore=tests/e2e/

# E2E tests
npx playwright test tests/e2e/ --workers=1

# Linting
ruff check .
pylint custom_components/ tests/

# Type checking
mypy custom_components/

# Formatting
black .
isort .

# JS tests
npm test
```

## Project Structure Conventions

### Python Code Organization

```
custom_components/ev_trip_planner/
├── __init__.py          # Integration lifecycle (setup/unload/migrate)
├── const.py             # All constants and config keys
├── utils.py             # Pure utility functions
├── calculations.py      # Pure calculation functions (no HA deps)
├── definitions.py       # Sensor entity descriptions
├── sensor.py            # Sensor entities
├── coordinator.py       # DataUpdateCoordinator
├── trip_manager.py      # Core business logic
├── emhass_adapter.py    # EMHASS integration
├── services.py          # HA service handlers
├── config_flow.py       # Config flow
├── vehicle_controller.py # Charging control strategies
├── presence_monitor.py  # Presence detection
├── schedule_monitor.py  # Schedule monitoring
├── panel.py             # Native panel registration
├── dashboard.py         # Dashboard auto-deploy
```

### Testing Conventions

```
tests/
├── conftest.py              # Shared fixtures
├── test_{module}.py         # Unit tests per module
├── test_{feature}_coverage.py  # Coverage gap tests
├── fixtures/                # Test data
│   ├── trips/               # Trip JSON fixtures
│   └── vehicles/            # Vehicle JSON fixtures
└── e2e/                     # Playwright E2E tests
    ├── *.spec.ts            # Test specs
    └── trips-helpers.ts     # Shared helpers
```

## Code Style

### Python

- **Formatter**: black (88 char line length)
- **Import sorting**: isort (black profile)
- **Linter**: ruff + pylint
- **Type checking**: mypy (strict mode)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Docstrings**: Google-style docstrings on all public functions/classes
- **Language**: Code in English, user-facing strings in Spanish/English (via translations/)

### Key Rules

1. **Pure functions**: Extract calculations to `calculations.py` — no async, no HA deps
2. **Explicit datetime**: All time-sensitive functions take `reference_dt` parameter
3. **Protocol-based DI**: Use `TripStorageProtocol` and `EMHASSPublisherProtocol`
4. **Type aliases**: Use `TypeAlias` for complex type hints
5. **No device_id**: Always use `entity_id` for HA entity references
6. **Spanish day names**: Internal day representation uses Spanish (lunes-domingo)

### TypeScript

- **Framework**: Lit 2.x web components
- **Testing**: Jest for unit, Playwright for E2E
- **ES Module**: Use ES module imports

## Testing Strategy

### Unit Tests (pytest)

- **Target**: 100% code coverage
- **Fixtures**: `conftest.py` provides `hass`, `config_entry`, `trip_manager` fixtures
- **Pattern**: Test files mirror source files (`test_trip_manager.py` for `trip_manager.py`)
- **Parametrize**: Use `@pytest.mark.parametrize` for pure function tests
- **No I/O**: Pure calculation tests require zero mocks

### E2E Tests (Playwright)

- **Target**: Critical user paths
- **Setup**: Docker HA instance with trusted_networks auth
- **Workers**: 1 (sequential execution)
- **Helpers**: `trips-helpers.ts` provides shared functions

### Test Execution Flow

```bash
# 1. Quick unit test cycle
make test

# 2. Full coverage check
make test-cover

# 3. E2E (auto-starts HA)
make e2e

# 4. All checks
make check
```

## Environment Setup

### Docker Test Environment

The `docker-compose.yml` provides a HA Container instance:

```yaml
services:
  homeassistant:
    image: homeassistant/home-assistant:stable
    container_name: ha-ev-trip-planner-test
    ports:
      - "8123:8123"
    volumes:
      - ./custom_components/ev_trip_planner:/config/custom_components/ev_trip_planner
      - ./tests/ha-manual/configuration.yaml:/config/configuration.yaml:ro
```

### E2E Test Configuration

- Auth: `trusted_networks` (no login required from localhost)
- Config: Pre-configured with test input booleans
- Scripts: `scripts/run-e2e.sh` handles HA lifecycle

## Build & Deploy

### HACS Distribution

1. Tag release in git
2. HACS picks up via `hacs.json` and `manifest.json`
3. Users install via HACS UI

### Manual Installation

1. Copy `custom_components/ev_trip_planner/` to HA's `custom_components/`
2. Restart Home Assistant
3. Add integration via Settings → Integrations

## Common Development Tasks

### Adding a New Sensor

1. Add `TripSensorEntityDescription` to `definitions.py`
2. Sensor auto-creates via `sensor.py::async_setup_entry`
3. Add test in `test_sensor*.py`

### Adding a New Service

1. Define service in `services.yaml`
2. Implement handler in `services.py`
3. Register in `register_services()`
4. Add test in `test_services*.py`

### Adding a Config Flow Step

1. Add schema to `config_flow.py`
2. Add step handler method
3. Add strings to `strings.json` and `translations/`
4. Add test in `test_config_flow*.py`

### Modifying Calculations

1. Add/modify pure function in `calculations.py`
2. All functions must be synchronous with explicit `reference_dt`
3. Add parametrized tests in `test_calculations.py`
4. TripManager delegates to calculation functions

## Debugging

### HA Logs

```bash
# Docker logs
docker compose logs -f

# Filter EV Trip Planner logs
docker compose logs -f | grep ev_trip_planner
```

### Playwright Debug

```bash
make test-e2e-debug
# Opens Playwright Inspector for step-through debugging
```

### Coverage Reports

```bash
make test-dashboard
# Opens htmlcov/index.html in browser
```

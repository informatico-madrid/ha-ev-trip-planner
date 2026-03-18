# Data Models: Test Data Models for Milestone 3

**Branch**: `007-complete-milestone-3-verify-1-2`  
**Date**: 2026-03-18  
**Purpose**: Define data models used in tests for Milestone 3 completion

---

## Trip Data Model

### Trip Entity

**Purpose**: Represents a single trip (recurring or punctual)

```python
@dataclass
class Trip:
    """Represents a trip in the system."""
    
    id: str  # Unique identifier (e.g., "rec_lun_test123" or "punct_2024-01-15_xyz")
    descripcion: str  # Trip description (e.g., "Trabajo", "Compras")
    datetime: datetime  # For punctual trips: scheduled time
    source: str  # "recurring" or "punctual"
    kwh: float  # Energy needed in kWh
    km: float  # Distance in km
    dia_semana: str | None  # For recurring: day of week (e.g., "lunes")
    hora: str | None  # For recurring: time (e.g., "08:00")
    status: str  # "pending" or "completed"
```

### Trip Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | str | ✅ | Unique identifier |
| `descripcion` | str | ✅ | Trip description |
| `datetime` | datetime | ✅ (punctual only) | Scheduled time for punctual trips |
| `source` | str | ✅ | "recurring" or "punctual" |
| `kwh` | float | ✅ | Energy needed in kWh |
| `km` | float | ✅ | Distance in km |
| `dia_semana` | str \| None | ❌ (recurring only) | Day of week in Spanish |
| `hora` | str \| None | ❌ (recurring only) | Time in "HH:MM" format |
| `status` | str | ✅ | "pending" or "completed" |

### Trip Examples

#### Recurring Trip
```python
{
    "id": "rec_lun_abc123",
    "descripcion": "Trabajo",
    "source": "recurring",
    "kwh": 3.75,
    "km": 25.0,
    "dia_semana": "lunes",
    "hora": "08:00",
    "status": "pending"
}
```

#### Punctual Trip
```python
{
    "id": "punct_2024-01-15_xyz789",
    "descripcion": "Compras",
    "source": "punctual",
    "datetime": datetime(2024, 1, 15, 14, 0),
    "kwh": 7.5,
    "km": 50.0,
    "status": "pending"
}
```

---

## Vehicle Configuration Data Model

### Vehicle Config Entity

**Purpose**: Vehicle configuration for SOC-aware power profile calculations

```python
@dataclass
class VehicleConfig:
    """Vehicle configuration for power profile calculations."""
    
    battery_capacity_kwh: float  # Total battery capacity in kWh
    charging_power_kw: float  # Charging power in kW
    soc_current: float  # Current SOC percentage (0-100)
```

### Vehicle Config Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `battery_capacity_kwh` | float | ✅ | Total battery capacity (e.g., 40.0 for 40 kWh) |
| `charging_power_kw` | float | ✅ | Charging power (e.g., 7.4 for 7.4 kW) |
| `soc_current` | float | ✅ | Current SOC percentage (0-100) |

### Vehicle Config Examples

#### Low SOC Vehicle
```python
{
    "battery_capacity_kwh": 40.0,
    "charging_power_kw": 7.4,
    "soc_current": 49.0  # 49% SOC = 19.6 kWh available
}
```

#### High SOC Vehicle
```python
{
    "battery_capacity_kwh": 40.0,
    "charging_power_kw": 7.4,
    "soc_current": 80.0  # 80% SOC = 32 kWh available
}
```

---

## Power Profile Data Model

### Power Profile Entity

**Purpose**: Power profile for planning horizon (power in Watts for each hour)

```python
@dataclass
class PowerProfile:
    """Power profile for planning horizon."""
    
    charging_power_kw: float  # Charging power in kW
    planning_horizon_days: int  # Number of days to plan
    profile: List[float]  # Power in Watts for each hour
```

### Power Profile Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `charging_power_kw` | float | ✅ | Charging power in kW |
| `planning_horizon_days` | int | ✅ | Number of days to plan |
| `profile` | List[float] | ✅ | Power in Watts for each hour |

### Power Profile Example

**Scenario**: 7 days planning horizon, 7.4 kW charging power

```python
{
    "charging_power_kw": 7.4,
    "planning_horizon_days": 7,
    "profile": [
        0, 0, 0, 0, 0, 0, 0,  # Hour 0-6: No charging
        7400, 7400, 7400, 7400,  # Hour 7-10: Full charging (7.4 kW = 7400 W)
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # Hour 11-20: No charging
        7400, 7400,  # Hour 21-22: Full charging
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # Hour 23-38: No charging
        # ... continues for 7 days * 24 hours = 168 hours
    ]
}
```

---

## Test Fixtures

### Mock Home Assistant Instance

**Purpose**: Create mock HA instance for testing

```python
@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance with storage simulation."""
    hass = MagicMock()
    hass.data = {}
    hass._storage = {}  # Simulated persistent storage
    
    # Async task creation
    future = asyncio.Future()
    future.set_result(None)
    hass.async_create_task = lambda *args, **kwargs: future
    hass.async_add_executor_job = lambda *args, **kwargs: future
    
    return hass
```

### Trip Manager Fixture

**Purpose**: Create TripManager instance for testing

```python
@pytest.fixture
def trip_manager(mock_hass):
    """Create TripManager instance."""
    from custom_components.ev_trip_planner.trip_manager import TripManager
    return TripManager(mock_hass, "test_vehicle")
```

### Sample Trip Fixture

**Purpose**: Create sample trip for testing

```python
@pytest.fixture
def sample_trip():
    """Create a sample trip that needs 7.5 kWh."""
    from homeassistant.util import dt as dt_util
    from datetime import timedelta
    
    return {
        "descripcion": "Test Trip",
        "datetime": dt_util.now() + timedelta(days=3),  # 3 days from now
        "kwh": 7.5,
        "source": "recurring",
    }
```

---

## Test Data Flows

### Trip Calculation Test Flow

```
1. Create mock_hass
2. Create TripManager(mock_hass, "test_vehicle")
3. Add trips (recurring or punctual)
4. Call async_get_next_trip() or async_get_kwh_needed_today()
5. Verify returned values
```

**Example**:
```python
async def test_get_kwh_needed_today_multiple_trips(mock_hass):
    # 1. Create manager
    mgr = TripManager(mock_hass, "test_vehicle")
    
    # 2. Add trips
    await mgr.async_add_recurring_trip(
        dia_semana="lunes",
        hora="08:00",
        km=25,
        kwh=3.75,
        descripcion="Trabajo"
    )
    
    await mgr.async_add_punctual_trip(
        datetime_str="2024-01-15T14:00:00",
        km=50,
        kwh=7.5,
        descripcion="Compras"
    )
    
    # 3. Call function
    kwh_today = await mgr.async_get_kwh_needed_today()
    
    # 4. Verify
    assert kwh_today == 11.25  # 3.75 + 7.5
```

### SOC-Aware Power Profile Test Flow

```
1. Create mock_hass
2. Create TripManager(mock_hass, "test_vehicle")
3. Add trips
4. Call async_generate_power_profile(vehicle_config=...)
5. Verify profile considers SOC
```

**Example**:
```python
async def test_power_profile_with_soc_below_threshold(trip_manager, sample_trip, vehicle_config):
    # 1. Setup
    trip_manager.async_get_all_trips_expanded = AsyncMock(return_value=[sample_trip])
    
    # 2. Call with low SOC
    profile = await trip_manager.async_generate_power_profile(
        charging_power_kw=vehicle_config["charging_power_kw"],
        planning_horizon_days=7,
        vehicle_config=vehicle_config  # SOC = 49%
    )
    
    # 3. Verify charging is scheduled
    charging_hours = [p for p in profile if p > 0]
    assert len(charging_hours) > 0  # Should have some charging hours
```

---

## Validation Rules

### Trip Validation

- `id`: Must be unique
- `descripcion`: Non-empty string
- `datetime`: Must be valid datetime (for punctual trips)
- `source`: Must be "recurring" or "punctual"
- `kwh`: Must be positive float
- `km`: Must be positive float
- `dia_semana`: Must be valid Spanish day name (if present)
- `hora`: Must be valid time format "HH:MM" (if present)

### Vehicle Config Validation

- `battery_capacity_kwh`: Must be positive float
- `charging_power_kw`: Must be positive float
- `soc_current`: Must be float between 0 and 100

### Power Profile Validation

- `charging_power_kw`: Must be positive float
- `planning_horizon_days`: Must be positive integer
- `profile`: List of floats (power in Watts), length = planning_horizon_days * 24

---

## References

- **Spec**: specs/007-complete-milestone-3-verify-1-2/spec.md
- **Plan**: specs/007-complete-milestone-3-verify-1-2/plan.md
- **Research**: specs/007-complete-milestone-3-verify-1-2/research.md
- **Code**: custom_components/ev_trip_planner/trip_manager.py

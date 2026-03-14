# TDD Plan - Milestone 3 Annex: Configuration Flow Fixes

## 📋 Problem Analysis

During configuration of vehicle "Chispitas" (OVMS integration), several UI/UX issues were identified:

### 🔴 Critical Issues

1. **Charging Status Sensor Filter**
   - **Problem**: OVMS charging status sensor not appearing in selector
   - **Location**: `config_flow.py` line 139-144
   - **Current filter**: `domain="binary_sensor", device_class="plug"`
   - **OVMS sensor**: Likely doesn't have `device_class: plug`

2. **Missing Translations**
   - `safety_margin_percent` - field label not translated
   - `planning_horizon_days` - field label not translated  
   - `planning_sensor_entity` - field label not translated
   - Checkbox under "planning_sensor_entity" - no label/text
   - Checkbox under "Maximum Deferrable Loads" - no label/text

3. **Vehicle Coordinates Field**
   - **Problem**: Single field expects combined lat/lon, but OVMS provides separate sensors
   - **Location**: `config_flow.py` line 381-383
   - **Current**: Single entity selector
   - **Needed**: Support for separate lat/lon sensors or auto-combine

### 🎯 TDD Approach

**Phase 1: Write Failing Tests**
- Create test file: `tests/test_config_flow_issues.py`
- Tests will verify:
  - OVMS charging sensor appears in selector (without device_class filter)
  - All field labels have translations in strings.json
  - All field labels have translations in es.json
  - Checkboxes have proper labels
  - Coordinate field accepts separate lat/lon sensors

**Phase 2: Implement Fixes**
- Fix sensor filters in config_flow.py
- Add missing translation keys to strings.json
- Add missing translation keys to es.json
- Add checkbox labels in config_flow.py
- Enhance coordinate field to support separate sensors

**Phase 3: Verify Tests Pass**
- Run pytest: `./venv/bin/pytest tests/test_config_flow_issues.py -v`
- Verify all tests pass
- Manual testing in Home Assistant UI

## 📝 Test Cases

### Test 1: Charging Status Sensor Selector
```python
def test_charging_status_sensor_includes_ovms_sensors():
    """Test that OVMS charging sensors appear without device_class filter."""
    # Mock available entities
    mock_entities = [
        "binary_sensor.ovms_chispitas_charging",  # OVMS sensor without device_class
        "binary_sensor.plug_status",  # Sensor with device_class: plug
    ]
    
    # Initialize config flow
    flow = EVTripPlannerConfigFlow()
    flow.hass = MockHass(entities=mock_entities)
    
    # Get sensors step schema
    schema = flow._get_sensors_schema()
    
    # Verify charging_status field includes both sensors
    charging_field = schema.schema.get(CONF_CHARGING_STATUS)
    assert charging_field is not None
    # Should not filter by device_class strictly
```

### Test 2: Translation Keys Exist
```python
def test_all_fields_have_translations():
    """Verify all config flow fields have translation keys."""
    required_keys = [
        "safety_margin_percent",
        "planning_horizon_days", 
        "planning_sensor_entity",
        "checkbox_planning_sensor_enable",  # New key needed
        "checkbox_max_loads_enable",  # New key needed
    ]
    
    # Check strings.json
    with open("strings.json") as f:
        strings = json.load(f)
    
    for key in required_keys:
        assert key in strings["config"]["step"]["consumption"]["data"] or \
               key in strings["config"]["step"]["emhass"]["data"]
```

### Test 3: Coordinate Field Enhancement
```python
def test_coordinate_field_accepts_separate_sensors():
    """Test that coordinate field can handle separate lat/lon sensors."""
    flow = EVTripPlannerConfigFlow()
    
    # Test with separate sensors
    user_input = {
        "vehicle_coordinates_sensor_lat": "sensor.ovms_lat",
        "vehicle_coordinates_sensor_lon": "sensor.ovms_lon",
    }
    
    # Should combine into single coordinate sensor
    result = flow._process_coordinate_sensors(user_input)
    assert "vehicle_coordinates_sensor" in result
```

## 🔧 Implementation Plan

### Step 1: Fix Charging Status Sensor Filter
**File**: `config_flow.py`
**Lines**: 139-144
**Change**: Remove strict device_class filter or make it optional

```python
# Current
vol.Optional(CONF_CHARGING_STATUS): selector.EntitySelector(
    selector.EntitySelectorConfig(
        domain="binary_sensor",
        device_class="plug",
    )
),

# New (more flexible)
vol.Optional(CONF_CHARGING_STATUS): selector.EntitySelector(
    selector.EntitySelectorConfig(
        domain="binary_sensor",
        # Remove device_class filter to include OVMS sensors
    )
),
```

### Step 2: Add Missing Translations
**File**: `strings.json`
**Add**:
```json
{
  "config": {
    "step": {
      "consumption": {
        "data": {
          "safety_margin_percent": "Safety Margin (%)"
        }
      },
      "emhass": {
        "data": {
          "planning_horizon_days": "Planning Horizon (days)",
          "planning_sensor_entity": "Planning Sensor Entity",
          "enable_planning_sensor": "Use dynamic planning horizon from sensor",
          "enable_max_loads_override": "Override maximum deferrable loads"
        }
      }
    }
  }
}
```

**File**: `translations/es.json`
**Add corresponding Spanish translations**

### Step 3: Fix Coordinate Field
**File**: `config_flow.py`
**Add**: Support for separate lat/lon sensors
**New approach**: 
- Keep single field for combined sensor
- Add optional separate fields
- Auto-combine if separate fields provided

## 📊 Success Criteria

- [ ] All tests pass (`pytest` returns 0)
- [ ] OVMS charging sensor appears in UI selector
- [ ] All field labels show translated text
- [ ] Checkboxes have descriptive labels
- [ ] Coordinate configuration accepts OVMS separate sensors
- [ ] Manual UI testing confirms fixes

## 🔄 Integration with Milestone 3

This TDD annex will be integrated into Milestone 3 as **Phase 3F: Configuration Flow Refinement**

**Dependencies**:
- Requires Milestone 3 Phase 3A (Configuration) to be complete
- Blocks Milestone 3 Phase 3E (Integration Testing) until resolved

**Timeline**: 2-3 days for TDD cycle
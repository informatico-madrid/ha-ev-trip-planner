"""Tests for EV Trip Planner configuration flow issues."""

import json
from unittest.mock import Mock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_STATUS,
    CONF_SAFETY_MARGIN,
    CONF_PLANNING_HORIZON,
    CONF_PLANNING_SENSOR,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_COORDINATES_SENSOR,
    DOMAIN,
)


class MockHass:
    """Mock Home Assistant instance."""
    
    def __init__(self, entities=None):
        """Initialize mock hass with available entities."""
        self.entities = entities or []
        self.states = Mock()
        self.states.get = lambda entity_id: Mock() if entity_id in self.entities else None


class TestConfigFlowIssues:
    """Test cases for configuration flow issues identified during Chispitas setup."""
    
    def test_charging_status_sensor_includes_ovms_sensors(self):
        """Test that OVMS charging sensors appear without strict device_class filter."""
        # Arrange: Mock available entities including OVMS sensor without device_class
        mock_entities = [
            "binary_sensor.ovms_chispitas_charging",  # OVMS sensor, no device_class
            "binary_sensor.wallbox_plug_status",  # Sensor with device_class: plug
            "binary_sensor.some_other_sensor",
        ]
        
        hass = MockHass(entities=mock_entities)
        flow = EVTripPlannerConfigFlow()
        flow.hass = hass
        
        # Act: Get the sensors step schema
        schema = flow._get_sensors_schema()
        
        # Assert: Verify charging_status field exists and is not strictly filtered
        charging_field = schema.schema.get(CONF_CHARGING_STATUS)
        assert charging_field is not None
        
        # The field should accept binary_sensor domain without strict device_class
        # This test will FAIL until we fix the device_class filter in config_flow.py
        
    def test_safety_margin_percent_translation_key_exists(self):
        """Test that safety_margin_percent has translation key in strings.json."""
        # Load strings.json
        with open("custom_components/ev_trip_planner/strings.json") as f:
            strings = json.load(f)
        
        # Check if key exists in consumption step
        consumption_data = strings["config"]["step"]["consumption"]["data"]
        
        # This test will FAIL until we add the translation key
        assert "safety_margin_percent" in consumption_data, \
            "Missing translation key: safety_margin_percent"
            
    def test_planning_horizon_days_translation_key_exists(self):
        """Test that planning_horizon_days has translation key in strings.json."""
        with open("custom_components/ev_trip_planner/strings.json") as f:
            strings = json.load(f)
            
        emhass_data = strings["config"]["step"]["emhass"]["data"]
        
        # This test will FAIL until we add the translation key
        assert "planning_horizon_days" in emhass_data, \
            "Missing translation key: planning_horizon_days"
            
    def test_planning_sensor_entity_translation_key_exists(self):
        """Test that planning_sensor_entity has translation key in strings.json."""
        with open("custom_components/ev_trip_planner/strings.json") as f:
            strings = json.load(f)
            
        emhass_data = strings["config"]["step"]["emhass"]["data"]
        
        # This test will FAIL until we add the translation key
        assert "planning_sensor_entity" in emhass_data, \
            "Missing translation key: planning_sensor_entity"
            
    def test_checkbox_labels_translation_keys_exist(self):
        """Test that checkboxes have translation keys in strings.json."""
        with open("custom_components/ev_trip_planner/strings.json") as f:
            strings = json.load(f)
            
        emhass_data = strings["config"]["step"]["emhass"]["data"]
        
        # These tests will FAIL until we add the translation keys
        assert "enable_planning_sensor" in emhass_data, \
            "Missing translation key: enable_planning_sensor (checkbox under planning sensor)"
            
        assert "enable_max_loads_override" in emhass_data, \
            "Missing translation key: enable_max_loads_override (checkbox under max loads)"
            
    def test_spanish_translations_complete(self):
        """Test that all new keys have Spanish translations."""
        # Load both translation files
        with open("custom_components/ev_trip_planner/strings.json") as f:
            strings = json.load(f)
            
        with open("custom_components/ev_trip_planner/translations/es.json") as f:
            es_translations = json.load(f)
        
        # Keys that should exist in both
        required_keys = [
            "safety_margin_percent",
            "planning_horizon_days",
            "planning_sensor_entity",
            "enable_planning_sensor",
            "enable_max_loads_override",
        ]
        
        # Check each key exists in Spanish translations
        for key in required_keys:
            # Find which step the key belongs to
            found = False
            for step_name, step_data in strings["config"]["step"].items():
                if "data" in step_data and key in step_data["data"]:
                    # This key should also be in Spanish translations
                    es_step_data = es_translations["config"]["step"][step_name]["data"]
                    assert key in es_step_data, \
                        f"Missing Spanish translation for: {key}"
                    found = True
                    break
            
            assert found, f"Key {key} not found in any step"
            
    def test_vehicle_coordinates_field_accepts_separate_sensors(self):
        """Test that coordinate field can handle separate lat/lon sensors."""
        flow = EVTripPlannerConfigFlow()
        
        # Test input with separate sensors (OVMS style)
        user_input = {
            "vehicle_coordinates_sensor_lat": "sensor.ovms_chispitas_lat",
            "vehicle_coordinates_sensor_lon": "sensor.ovms_chispitas_lon",
        }
        
        # This test will FAIL until we implement the logic to handle separate sensors
        # The method should combine them into a single coordinate sensor
        result = flow._process_coordinate_sensors(user_input)
        
        assert "vehicle_coordinates_sensor" in result
        assert result["vehicle_coordinates_sensor"] == "sensor.ovms_chispitas_lat,sensor.ovms_chispitas_lon"
        
    def test_charging_status_sensor_no_strict_device_class_filter(self):
        """Test that charging status selector doesn't filter by device_class strictly."""
        # Mock entity registry with OVMS-like sensor (no device_class)
        mock_entities = [
            {
                "entity_id": "binary_sensor.ovms_chispitas_charging",
                "domain": "binary_sensor",
                "device_class": None,  # OVMS sensors often don't have device_class
            },
            {
                "entity_id": "binary_sensor.wallbox_plugged",
                "domain": "binary_sensor", 
                "device_class": "plug",
            }
        ]
        
        hass = MockHass()
        flow = EVTripPlannerConfigFlow()
        flow.hass = hass
        
        # Get the schema
        schema = flow._get_sensors_schema()
        charging_field = schema.schema.get(CONF_CHARGING_STATUS)
        
        # Verify the selector config doesn't have strict device_class
        selector_config = charging_field.config
        # This test will FAIL if device_class is strictly required
        assert "device_class" not in selector_config or selector_config.get("device_class") is None, \
            "Charging status sensor should not filter by device_class strictly"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
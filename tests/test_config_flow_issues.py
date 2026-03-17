"""Tests for EV Trip Planner configuration flow issues."""

import json

import pytest


class TestConfigFlowIssues:
    """Test cases for configuration flow issues identified during Chispitas setup."""

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


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
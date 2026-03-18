#!/usr/bin/env python3
"""Tests for UI issues detected after deployment - EV Trip Planner."""

import json
import os
import pytest


class TestUIIssuesPostDeployment:
    """Test UI issues detected after deployment using TDD approach."""

    def test_charging_status_sensor_translation_key_exists(self):
        """Test that 'charging_status' translation key exists and is properly translated."""
        # Load strings.json
        strings_path = "custom_components/ev_trip_planner/strings.json"
        with open(strings_path, 'r', encoding='utf-8') as f:
            strings_data = json.load(f)
        
        # Check if the key exists in the sensors step data
        assert "sensors" in strings_data["config"]["step"]
        sensors_data = strings_data["config"]["step"]["sensors"]["data"]
        
        # The key should be "charging_status" not "charging_status_sensor"
        assert "charging_status" in sensors_data
        # The label should be properly translated, not the raw key
        assert sensors_data["charging_status"] != "charging_status_sensor"
        assert sensors_data["charging_status"] == "Charging Status (optional)"

    def test_charging_status_sensor_spanish_translation(self):
        """Test that Spanish translation for charging_status is correct."""
        # Load es.json
        es_path = "custom_components/ev_trip_planner/translations/es.json"
        with open(es_path, 'r', encoding='utf-8') as f:
            es_data = json.load(f)
        
        sensors_data = es_data["config"]["step"]["sensors"]["data"]
        
        # Should be translated to Spanish
        assert "charging_status" in sensors_data
        assert sensors_data["charging_status"] == "Estado de Carga (opcional)"
        assert "charging_status_sensor" not in sensors_data

    def test_checkbox_labels_have_clear_descriptions(self):
        """Test that checkbox labels have clear descriptions explaining what they do."""
        # Load strings.json
        strings_path = "custom_components/ev_trip_planner/strings.json"
        with open(strings_path, 'r', encoding='utf-8') as f:
            strings_data = json.load(f)
        
        # Check EMHASS step data descriptions
        emhass_data_desc = strings_data["config"]["step"]["emhass"]["data_description"]
        
        # Check enable_planning_sensor checkbox description
        assert "enable_planning_sensor" in emhass_data_desc
        description = emhass_data_desc["enable_planning_sensor"]

        # Should have a descriptive translation (in either English or Spanish)
        assert len(description) > 5, "Checkbox description should be descriptive"

        # Check enable_max_loads_override checkbox description if it exists
        if "enable_max_loads_override" in emhass_data_desc:
            description = emhass_data_desc["enable_max_loads_override"]
            # Should have a descriptive translation
            assert len(description) > 5, "Checkbox description should be descriptive"

    def test_checkbox_spanish_descriptions_clear(self):
        """Test that Spanish checkbox descriptions are clear and explanatory."""
        # Load es.json
        es_path = "custom_components/ev_trip_planner/translations/es.json"
        with open(es_path, 'r', encoding='utf-8') as f:
            es_data = json.load(f)
        
        emhass_data_desc = es_data["config"]["step"]["emhass"]["data_description"]
        
        # Check enable_planning_sensor description in Spanish
        assert "enable_planning_sensor" in emhass_data_desc
        description = emhass_data_desc["enable_planning_sensor"]
        
        # Should clearly explain both states
        assert "Marcar" in description or "marcar" in description
        assert "sobrescribir" in description
        
        # Check enable_max_loads_override description in Spanish
        assert "enable_max_loads_override" in emhass_data_desc
        description = emhass_data_desc["enable_max_loads_override"]
        
        # Should clearly explain both states
        assert "Marcar" in description or "marcar" in description
        assert "habilitar" in description

    def test_config_flow_no_device_class_filter(self):
        """Test that config_flow.py doesn't have device_class filter for charging_status."""
        config_flow_path = "custom_components/ev_trip_planner/config_flow.py"
        
        with open(config_flow_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the charging_status selector section
        lines = content.split('\n')
        in_charging_status_section = False
        device_class_found = False
        
        for i, line in enumerate(lines):
            if "CONF_CHARGING_STATUS" in line and "selector.EntitySelector" in line:
                in_charging_status_section = True
                # Check next 10 lines for device_class
                for j in range(i, min(i+10, len(lines))):
                    if "device_class" in lines[j]:
                        device_class_found = True
                        break
                break
        
        # Should not have device_class filter
        assert not device_class_found, "device_class filter still present in charging_status selector"

    @pytest.mark.skip(reason="Vehicle coordinates feature not implemented")
    def test_vehicle_coordinates_separate_fields_in_config(self):
        """Test that config_flow.py has separate lat/lon fields for vehicle coordinates."""
        config_flow_path = "custom_components/ev_trip_planner/config_flow.py"
        
        with open(config_flow_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should have separate lat/lon fields or a method to process them
        has_lat_field = "vehicle_coordinates_sensor_lat" in content
        has_lon_field = "vehicle_coordinates_sensor_lon" in content
        has_process_method = "_process_coordinate_sensors" in content
        
        assert (has_lat_field and has_lon_field) or has_process_method, \
            "No support for separate lat/lon sensors found in config_flow.py"

    def test_all_fields_have_translations(self):
        """Test that all data fields have both English and Spanish translations."""
        # Load both translation files
        strings_path = "custom_components/ev_trip_planner/strings.json"
        es_path = "custom_components/ev_trip_planner/translations/es.json"
        
        with open(strings_path, 'r', encoding='utf-8') as f:
            strings_data = json.load(f)
        
        with open(es_path, 'r', encoding='utf-8') as f:
            es_data = json.load(f)
        
        # Check all steps
        for step_name in ["user", "sensors", "consumption", "emhass", "presence"]:
            if step_name in strings_data["config"]["step"]:
                # Check data fields
                step_data = strings_data["config"]["step"][step_name]["data"]
                es_step_data = es_data["config"]["step"][step_name]["data"]
                
                for key in step_data.keys():
                    assert key in es_step_data, f"Spanish translation missing for {key} in {step_name}"
                    assert es_step_data[key] != key, f"Spanish translation not translated for {key} in {step_name}"
                
                # Check data descriptions
                if "data_description" in strings_data["config"]["step"][step_name]:
                    step_desc = strings_data["config"]["step"][step_name]["data_description"]
                    es_step_desc = es_data["config"]["step"][step_name]["data_description"]
                    
                    for key in step_desc.keys():
                        assert key in es_step_desc, f"Spanish description missing for {key} in {step_name}"
                        assert es_step_desc[key] != step_desc[key], \
                            f"Spanish description not translated for {key} in {step_name}"
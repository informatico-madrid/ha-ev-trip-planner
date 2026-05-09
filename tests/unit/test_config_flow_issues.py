"""Tests for EV Trip Planner configuration flow issues."""

import json

import pytest


class TestConfigFlowIssues:
    """Test cases for configuration flow issues identified during Chispitas setup."""

    def test_vehicle_type_not_in_config_flow(self):
        """Test that vehicle_type is NOT in the config flow schema (US1)."""
        # Import the actual schema to test
        from custom_components.ev_trip_planner.config_flow import STEP_USER_SCHEMA

        # Convert schema to string representation to check contents
        schema_str = str(STEP_USER_SCHEMA.schema)

        # vehicle_type should NOT be present in the schema
        assert (
            "vehicle_type" not in schema_str
        ), "vehicle_type should NOT be in config flow (US1: eliminar selector)"

        # CONF_VEHICLE_NAME should be present (the only required field)
        assert (
            "vehicle_name" in schema_str
        ), "vehicle_name should be present in step 1 schema"

    def test_config_flow_step_count(self):
        """Test that config flow has exactly 4 steps (no vehicle_type step)."""
        from custom_components.ev_trip_planner import config_flow

        # Count the step schemas defined
        step_schemas = [
            "STEP_USER_SCHEMA",  # Step 1: Vehicle name
            "STEP_SENSORS_SCHEMA",  # Step 2: Sensors
            "STEP_EMHASS_SCHEMA",  # Step 3: EMHASS
            "STEP_PRESENCE_SCHEMA",  # Step 4: Presence
        ]

        for step_name in step_schemas:
            assert hasattr(
                config_flow, step_name
            ), f"Step schema {step_name} should exist"

    def test_safety_margin_percent_translation_key_exists(self):
        """Test that safety_margin_percent has translation key in strings.json."""
        # Load strings.json
        with open("custom_components/ev_trip_planner/strings.json") as f:
            strings = json.load(f)

        # Check if key exists in consumption step
        consumption_data = strings["config"]["step"]["consumption"]["data"]

        # This test will FAIL until we add the translation key
        assert (
            "safety_margin_percent" in consumption_data
        ), "Missing translation key: safety_margin_percent"

    def test_planning_horizon_days_translation_key_exists(self):
        """Test that planning_horizon_days has translation key in strings.json."""
        with open("custom_components/ev_trip_planner/strings.json") as f:
            strings = json.load(f)

        emhass_data = strings["config"]["step"]["emhass"]["data"]

        # This test will FAIL until we add the translation key
        assert (
            "planning_horizon_days" in emhass_data
        ), "Missing translation key: planning_horizon_days"

    def test_planning_sensor_entity_translation_key_exists(self):
        """Test that planning_sensor_entity has translation key in strings.json."""
        with open("custom_components/ev_trip_planner/strings.json") as f:
            strings = json.load(f)

        emhass_data = strings["config"]["step"]["emhass"]["data"]

        # This test will FAIL until we add the translation key
        assert (
            "planning_sensor_entity" in emhass_data
        ), "Missing translation key: planning_sensor_entity"

    def test_checkbox_labels_translation_keys_exist(self):
        """Test that checkboxes have translation keys in strings.json."""
        with open("custom_components/ev_trip_planner/strings.json") as f:
            strings = json.load(f)

        emhass_data = strings["config"]["step"]["emhass"]["data"]

        # These tests will FAIL until we add the translation keys
        assert (
            "enable_planning_sensor" in emhass_data
        ), "Missing translation key: enable_planning_sensor (checkbox under planning sensor)"

        assert (
            "enable_max_loads_override" in emhass_data
        ), "Missing translation key: enable_max_loads_override (checkbox under max loads)"

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
                    assert (
                        key in es_step_data
                    ), f"Missing Spanish translation for: {key}"
                    found = True
                    break

            assert found, f"Key {key} not found in any step"

    def test_charging_status_sensor_spanish_translation(self):
        """Test that charging_status_sensor entity is translated to Spanish (US2)."""
        # The entity translations are in translations/es.json
        with open("custom_components/ev_trip_planner/translations/es.json") as f:
            es_translations = json.load(f)

        # Verify charging_status_sensor entity exists and is in Spanish
        assert (
            "entity" in es_translations
        ), "Missing 'entity' section in translations/es.json"
        assert (
            "charging_status_sensor" in es_translations["entity"]
        ), "Missing charging_status_sensor in entity translations"

        # The translation should be in Spanish
        spanish_name = es_translations["entity"]["charging_status_sensor"]["name"]
        assert (
            spanish_name == "Sensor de Estado de Carga del Vehículo"
        ), f"Expected Spanish translation 'Sensor de Estado de Carga del Vehículo', got: {spanish_name}"

        # Verify it's NOT in English (check it's not the English version)
        assert (
            "Charging Status Sensor" not in spanish_name
        ), "Translation should be in Spanish, not English"

    def test_charging_status_config_flow_spanish(self):
        """Test that charging_status in config flow step is translated to Spanish (US2)."""
        # The Spanish translations are in translations/es.json
        with open("custom_components/ev_trip_planner/translations/es.json") as f:
            es_translations = json.load(f)

        # Verify charging_status in sensors step is in Spanish
        sensors_data = es_translations["config"]["step"]["sensors"]["data"]
        assert (
            "charging_status" in sensors_data
        ), "Missing charging_status in sensors step data"

        # Should be in Spanish
        spanish_label = sensors_data["charging_status"]
        assert (
            spanish_label == "Estado de Carga (opcional)"
        ), f"Expected 'Estado de Carga (opcional)', got: {spanish_label}"

        # Verify data_description is also in Spanish
        sensors_desc = es_translations["config"]["step"]["sensors"]["data_description"]
        assert (
            "charging_status" in sensors_desc
        ), "Missing charging_status in sensors step data_description"

        # Spanish description should contain Spanish words
        spanish_description = sensors_desc["charging_status"]
        assert (
            "opcional" in spanish_description.lower()
        ), "data_description should be in Spanish"
        assert (
            "sensor binario" in spanish_description.lower()
        ), "data_description should mention binary sensor in Spanish"

    def test_charging_status_sensor_has_help_hint(self):
        """Test that charging_status has a helpful hint with clear instructions (US2)."""
        # Load Spanish translations
        with open("custom_components/ev_trip_planner/translations/es.json") as f:
            es_translations = json.load(f)

        # Get the data_description for charging_status in sensors step
        sensors_desc = es_translations["config"]["step"]["sensors"]["data_description"]
        assert (
            "charging_status" in sensors_desc
        ), "Missing charging_status in sensors step data_description"

        hint = sensors_desc["charging_status"]

        # The hint should contain helpful information
        # Check 1: Mention it's optional
        assert "opcional" in hint.lower(), "Hint should mention it's optional"

        # Check 2: Mention it's a binary sensor
        assert (
            "sensor binario" in hint.lower() or "binario" in hint.lower()
        ), "Hint should mention binary sensor"

        # Check 3: Explain what state to look for (on/charging)
        assert (
            "on" in hint.lower() or "cargando" in hint.lower()
        ), "Hint should explain when the sensor shows 'on' (charging)"

        # Check 4: Provide examples of what to look for in sensor names
        # The hint should tell users what entity_ids to search for
        assert (
            "charging" in hint.lower()
            or "charge" in hint.lower()
            or "plugged" in hint.lower()
        ), "Hint should provide examples of what to look for in sensor names (charging, charge, plugged)"

        # Check 5: Provide actual entity examples
        assert (
            "binary_sensor" in hint.lower()
        ), "Hint should provide entity examples with domain (binary_sensor.XXX)"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

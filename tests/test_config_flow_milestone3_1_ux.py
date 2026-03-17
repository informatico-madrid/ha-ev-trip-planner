"""Tests for Milestone 3.1 UX Improvements."""

import json
import os

import pytest


@pytest.mark.asyncio
async def test_strings_json_includes_data_descriptions():
    """Test that strings.json includes data_description fields for all config steps."""
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )

    with open(strings_path) as f:
        strings_data = json.load(f)

    # Verify all steps have data_description
    config_steps = ["user", "sensors", "emhass", "presence"]

    for step in config_steps:
        assert "data_description" in strings_data["config"]["step"][step], \
            f"Step '{step}' missing data_description"

        # Verify data_description is not empty
        data_desc = strings_data["config"]["step"][step]["data_description"]
        assert len(data_desc) > 0, f"Step '{step}' has empty data_description"

        # Verify each field in data has a description
        data_fields = strings_data["config"]["step"][step]["data"]
        for field in data_fields:
            assert field in data_desc, \
                f"Field '{field}' in step '{step}' missing data_description"


@pytest.mark.asyncio
async def test_error_messages_are_descriptive():
    """Test that error messages in strings.json are descriptive and helpful."""
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )

    with open(strings_path) as f:
        strings_data = json.load(f)

    # Verify error messages exist and are descriptive
    error_messages = strings_data["config"]["error"]

    required_errors = [
        "invalid_planning_horizon",
        "invalid_max_deferrable_loads",
        "home_sensor_not_found",
        "plugged_sensor_not_found",
        "invalid_coordinates_format",
    ]

    for error_key in required_errors:
        assert error_key in error_messages, f"Missing error message: {error_key}"
        assert len(error_messages[error_key]) > 10, \
            f"Error message '{error_key}' is too short to be descriptive"


@pytest.mark.asyncio
async def test_data_descriptions_include_examples():
    """Test that data descriptions include concrete examples."""
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )

    with open(strings_path) as f:
        strings_data = json.load(f)

    # Check for examples in key fields
    sensors_desc = strings_data["config"]["step"]["sensors"]["data_description"]

    # Battery capacity should mention kWh and give example
    capacity_desc = sensors_desc["battery_capacity"]
    has_kwh = "kwh" in capacity_desc.lower()
    has_example = "example" in capacity_desc.lower() or "e.g." in capacity_desc.lower()

    assert has_kwh, f"Battery capacity description should mention kWh: {capacity_desc}"
    assert has_example, f"Battery capacity description should include examples: {capacity_desc}"


@pytest.mark.asyncio
async def test_emhass_step_description_mentions_emhass_integration():
    """Test that EMHASS step description mentions EMHASS integration clearly."""
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )

    with open(strings_path) as f:
        strings_data = json.load(f)

    emhass_step = strings_data["config"]["step"]["emhass"]

    # Description should mention EMHASS
    description = emhass_step["description"]
    assert "emhass" in description.lower() or "optimizer" in description.lower()

    # Should explain it's optional
    assert "optional" in description.lower() or "configure" in description.lower()


@pytest.mark.asyncio
async def test_presence_step_description_mentions_prevention():
    """Test that presence step description mentions preventing charging when away."""
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )

    with open(strings_path) as f:
        strings_data = json.load(f)

    presence_step = strings_data["config"]["step"]["presence"]

    # Description should mention purpose
    description = presence_step["description"]
    assert "presence" in description.lower() or "home" in description.lower()
    # Description should mention charging sensor is required
    assert "charging" in description.lower() or "required" in description.lower()

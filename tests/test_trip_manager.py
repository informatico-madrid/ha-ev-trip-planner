"""Tests for storage API not available in Container environment.

This test reproduces the P004 error:
"'HomeAssistant' object has no attribute 'storage'" /
"Storage API not available for vehicle {vehicle_id}"

In Home Assistant Container, the storage API is not available.
The fix is to use YAML file persistence as a fallback.
"""

from __future__ import annotations

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def vehicle_id() -> str:
    """Return a test vehicle ID."""
    return "morgan"


@pytest.fixture
def mock_hass_no_storage():
    """Create a mock hass WITHOUT storage (Container environment).

    In Home Assistant Container, the storage API is not available.
    This fixture simulates that environment by returning None for storage.
    """
    from unittest.mock import MagicMock

    hass = MagicMock()
    # Mock config_entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # DO NOT set hass.storage - this simulates Container environment
    # In Container, hass.storage is None or does not exist
    hass.storage = None

    return hass


@pytest.mark.asyncio
async def test_load_trips_with_yaml_fallback(mock_hass_no_storage, vehicle_id, tmp_path, caplog):
    """Test that _load_trips works with YAML fallback when storage is not available.

    This test verifies the P004 fix where:
    - hass.storage is None in Container environment
    - YAML fallback is used instead
    - Expected: PASS after fix (trips loaded successfully via YAML)

    See: docs/LOGS_ANALYSIS_2026-03-20.md for P004 details.
    """
    from pathlib import Path as PathLib

    # Setup YAML file with test data
    config_dir = tmp_path / "config"
    storage_key = "ev_trip_planner_morgan"
    yaml_dir = config_dir / "ev_trip_planner"
    yaml_dir.mkdir(parents=True, exist_ok=True)
    yaml_file = yaml_dir / f"{storage_key}.yaml"

    # Create test YAML data
    test_data = {
        "version": 1,
        "data": {
            "trips": {"trip1": {"id": "trip1", "tipo": "punctual"}},
            "recurring_trips": {
                "rec_lunes_001": {
                    "id": "rec_lunes_001",
                    "tipo": "recurring",
                    "dia_semana": "lunes",
                    "hora": "08:00",
                    "km": 50.0,
                    "kwh": 10.0,
                    "descripcion": "Test recurring trip",
                    "activo": True,
                }
            },
            "punctual_trips": {
                "pun_20260320_001": {
                    "id": "pun_20260320_001",
                    "tipo": "punctual",
                    "datetime": "2026-03-20T10:00",
                    "km": 100.0,
                    "kwh": 20.0,
                    "descripcion": "Test punctual trip",
                    "estado": "pendiente",
                }
            },
            "last_update": "2026-03-20T10:00:00",
        },
    }

    import yaml
    with open(yaml_file, "w") as f:
        yaml.dump(test_data, f)

    # Setup mock to use our config directory
    mock_hass_no_storage.config.config_dir = str(config_dir)

    manager = TripManager(mock_hass_no_storage, vehicle_id)

    # After fix: YAML fallback should work and trips should load
    await manager._load_trips()

    # Verify YAML fallback worked
    assert "cargados desde YAML fallback" in caplog.text

    # Verify trips were loaded from YAML
    assert len(manager._recurring_trips) == 1
    assert len(manager._punctual_trips) == 1
    assert "rec_lunes_001" in manager._recurring_trips
    assert "pun_20260320_001" in manager._punctual_trips
    assert manager._recurring_trips["rec_lunes_001"]["dia_semana"] == "lunes"
    assert manager._punctual_trips["pun_20260320_001"]["km"] == 100.0


@pytest.mark.asyncio
async def test_load_trips_fails_when_storage_not_available(mock_hass_no_storage, vehicle_id, caplog):
    """Test that _load_trips handles missing YAML file gracefully.

    This test verifies that when storage is not available AND no YAML file exists,
    the code handles it gracefully without errors.

    See: docs/LOGS_ANALYSIS_2026-03-20.md for P004 details.
    """
    manager = TripManager(mock_hass_no_storage, vehicle_id)

    # No YAML file exists, should handle gracefully
    await manager._load_trips()

    # Verify no error was logged (graceful handling)
    assert "Error cargando viajes" not in caplog.text

    # Verify trips are empty (expected when no YAML file)
    assert manager._trips == {}
    assert manager._recurring_trips == {}
    assert manager._punctual_trips == {}


@pytest.mark.asyncio
async def test_save_trips_with_yaml_fallback(mock_hass_no_storage, vehicle_id, tmp_path, caplog):
    """Test that async_save_trips works with YAML fallback when storage is not available.

    This test verifies the P004 fix where:
    - hass.storage is None in Container environment
    - YAML file is created and trips are saved successfully

    See: docs/LOGS_ANALYSIS_2026-03-20.md for P004 details.
    """
    import yaml

    # Setup YAML directory
    config_dir = tmp_path / "config"
    storage_key = "ev_trip_planner_morgan"
    yaml_dir = config_dir / "ev_trip_planner"
    yaml_dir.mkdir(parents=True, exist_ok=True)

    # Setup mock to use our config directory
    mock_hass_no_storage.config.config_dir = str(config_dir)

    manager = TripManager(mock_hass_no_storage, vehicle_id)

    # Add a test trip
    await manager.async_add_recurring_trip(
        dia_semana="martes",
        hora="09:00",
        km=50.0,
        kwh=10.0,
        descripcion="Test trip",
    )

    # Verify trips were saved to YAML
    yaml_file = yaml_dir / f"{storage_key}.yaml"
    assert yaml_file.exists(), "YAML file should be created"

    # Read and verify YAML content
    with open(yaml_file, "r") as f:
        saved_data = yaml.safe_load(f)

    assert saved_data is not None
    assert "data" in saved_data
    assert "recurring_trips" in saved_data["data"]
    assert len(saved_data["data"]["recurring_trips"]) == 1

    # Verify trip data was saved correctly
    trip_id = list(saved_data["data"]["recurring_trips"].keys())[0]
    trip = saved_data["data"]["recurring_trips"][trip_id]
    assert trip["dia_semana"] == "martes"
    assert trip["hora"] == "09:00"
    assert trip["km"] == 50.0
    assert trip["kwh"] == 10.0
    assert trip["descripcion"] == "Test trip"

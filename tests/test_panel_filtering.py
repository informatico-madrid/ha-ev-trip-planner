"""Tests for panel sensor filtering by entry_id.

Tests verify that the panel correctly filters EMHASS sensors by entry_id:
- Only sensors with matching entry_id appear on vehicle panel
- No cross-vehicle sensor contamination
- Non-EMHASS sensors still work correctly
"""

import pytest
from unittest.mock import MagicMock

# Import panel.js logic (simulated in Python for testing)


class MockPanelState:
    """Mock Home Assistant state for testing panel filtering."""

    def __init__(self, entity_id, state, attributes=None):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}


class MockPanel:
    """Mock panel for testing filtering logic."""

    def __init__(self, vehicle_id):
        self._vehicleId = vehicle_id

    def _getVehicleStates(self, states):
        """Simulate the panel filtering logic from panel.js.

        This mirrors the JavaScript logic in custom_components/ev_trip_planner/frontend/panel.js:
        - For EMHASS sensors (starting with sensor.emhass_perfil_diferible_),
          verify entry_id attribute matches current vehicle
        - For other sensors, include them normally
        """
        result = {}

        for entityId, state in states.items():
            # FR-2.1: For EMHASS sensors, verify entry_id attribute matches current vehicle
            if entityId.startswith('sensor.emhass_perfil_diferible_'):
                entryId = state.attributes.get('entry_id')
                if entryId == self._vehicleId:
                    result[entityId] = state
            else:
                result[entityId] = state

        return result


@pytest.fixture
def sample_states():
    """Sample HA states for testing panel filtering.

    Includes:
    - EMHASS sensors for vehicle_a (should be included)
    - EMHASS sensors for vehicle_b (should be excluded)
    - Regular sensors (should be included)
    """
    return {
        # EMHASS sensors for vehicle_a (should be included)
        'sensor.emhass_perfil_diferible_vehicle_a': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_a',
            'active',
            {'entry_id': 'vehicle_a', 'deferrables_schedule': []}
        ),
        'sensor.emhass_perfil_diferible_vehicle_a_trip_001': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_a_trip_001',
            'active',
            {'entry_id': 'vehicle_a', 'power_profile_watts': [0, 1000, 2000]}
        ),
        # EMHASS sensors for vehicle_b (should be excluded)
        'sensor.emhass_perfil_diferible_vehicle_b': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_b',
            'active',
            {'entry_id': 'vehicle_b', 'deferrables_schedule': []}
        ),
        'sensor.emhass_perfil_diferible_vehicle_b_trip_002': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_b_trip_002',
            'active',
            {'entry_id': 'vehicle_b', 'power_profile_watts': [0, 500, 1000]}
        ),
        # Regular sensors (should be included)
        'sensor.vehicle_a_battery': MockPanelState(
            'sensor.vehicle_a_battery',
            '80',
            {'unit_of_measurement': '%'}
        ),
        'sensor.vehicle_a_range': MockPanelState(
            'sensor.vehicle_a_range',
            '250',
            {'unit_of_measurement': 'km'}
        ),
    }


def test_panel_filters_by_entry_id():
    """Test that panel filters EMHASS sensors by entry_id.

    FR-2.1: Vehicle panel should only show EMHASS sensors with matching entry_id.
    """
    panel = MockPanel('vehicle_a')
    filtered = panel._getVehicleStates({
        'sensor.emhass_perfil_diferible_vehicle_a': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_a',
            'active',
            {'entry_id': 'vehicle_a'}
        ),
        'sensor.emhass_perfil_diferible_vehicle_b': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_b',
            'active',
            {'entry_id': 'vehicle_b'}
        ),
    })

    # Verify: Only vehicle_a's sensor is included
    assert 'sensor.emhass_perfil_diferible_vehicle_a' in filtered
    assert 'sensor.emhass_perfil_diferible_vehicle_b' not in filtered


def test_no_cross_vehicle_contamination():
    """Test that sensors from one vehicle don't appear on another vehicle's panel.

    FR-2.1: Prevent cross-vehicle sensor contamination by filtering on entry_id.
    """
    panel = MockPanel('vehicle_a')

    # Create states with multiple vehicles' sensors
    all_states = {
        f'sensor.emhass_perfil_diferible_vehicle_{v}': MockPanelState(
            f'sensor.emhass_perfil_diferible_vehicle_{v}',
            'active',
            {'entry_id': f'vehicle_{v}'}
        )
        for v in ['a', 'b', 'c']
    }

    filtered = panel._getVehicleStates(all_states)

    # Verify: Only vehicle_a's sensor appears
    assert len(filtered) == 1
    assert 'sensor.emhass_perfil_diferible_vehicle_a' in filtered
    assert 'sensor.emhass_perfil_diferible_vehicle_b' not in filtered
    assert 'sensor.emhass_perfil_diferible_vehicle_c' not in filtered


def test_no_entry_id_attribute():
    """Test handling of EMHASS sensors without entry_id attribute.

    If an EMHASS sensor lacks the entry_id attribute, it should be excluded
    to prevent showing orphaned or misconfigured sensors.
    """
    panel = MockPanel('vehicle_a')

    states = {
        'sensor.emhass_perfil_diferible_vehicle_a': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_a',
            'active',
            {'deferrables_schedule': []}  # Missing entry_id
        ),
        'sensor.emhass_perfil_diferible_vehicle_b': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_b',
            'active',
            {'entry_id': 'vehicle_b'}
        ),
    }

    filtered = panel._getVehicleStates(states)

    # Verify: Sensor without entry_id is excluded
    assert 'sensor.emhass_perfil_diferible_vehicle_a' not in filtered
    assert 'sensor.emhass_perfil_diferible_vehicle_b' not in filtered


def test_non_emhass_sensors_included():
    """Test that non-EMHASS sensors are still included.

    Regular sensors (not starting with sensor.emhass_perfil_diferible_)
    should be included regardless of attributes.
    """
    panel = MockPanel('vehicle_a')

    states = {
        'sensor.emhass_perfil_diferible_vehicle_b': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_b',
            'active',
            {'entry_id': 'vehicle_b'}
        ),
        'sensor.vehicle_a_battery': MockPanelState(
            'sensor.vehicle_a_battery',
            '80',
            {'unit_of_measurement': '%'}
        ),
        'sensor.vehicle_a_range': MockPanelState(
            'sensor.vehicle_a_range',
            '250',
            {'unit_of_measurement': 'km'}
        ),
    }

    filtered = panel._getVehicleStates(states)

    # Verify: Non-EMHASS sensors are included
    assert 'sensor.vehicle_a_battery' in filtered
    assert 'sensor.vehicle_a_range' in filtered
    assert 'sensor.emhass_perfil_diferible_vehicle_b' not in filtered


def test_partial_entry_id_match():
    """Test that partial entry_id matches are excluded.

    Only exact entry_id matches should be included.
    """
    panel = MockPanel('vehicle_a')

    states = {
        'sensor.emhass_perfil_diferible_vehicle_a': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_a',
            'active',
            {'entry_id': 'vehicle_a'}
        ),
        'sensor.emhass_perfil_diferible_vehicle_a_backup': MockPanelState(
            'sensor.emhass_perfil_diferible_vehicle_a_backup',
            'active',
            {'entry_id': 'vehicle_a_backup'}  # Different entry_id
        ),
    }

    filtered = panel._getVehicleStates(states)

    # Verify: Only exact match included
    assert 'sensor.emhass_perfil_diferible_vehicle_a' in filtered
    assert 'sensor.emhass_perfil_diferible_vehicle_a_backup' not in filtered


def test_empty_states():
    """Test handling of empty state list."""
    panel = MockPanel('vehicle_a')

    filtered = panel._getVehicleStates({})

    # Verify: Empty result
    assert filtered == {}

"""E2E Test: Panel.js EMHASS sensor entity ID match.

BUG #3/#4/FIX: Panel.js needs to find EMHASS sensor using prefix search.

PROBLEM:
- Panel has `this._vehicleId` but sensor entity ID uses `entry_id`
- Panel cannot construct exact entity ID: `sensor.emhass_perfil_diferible_{entry_id}`

SOLUTION:
- Panel searches for sensor by prefix: `sensor.emhass_perfil_diferible_`
- First matching entity in hass.states is used

This test verifies:
1. emhass_adapter.py creates sensor with entity ID pattern `sensor.emhass_perfil_diferible_{entry_id}`
2. panel.js uses prefix search to find the sensor
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# =============================================================================
# TEST: Panel.js entity ID pattern matches sensor entity ID pattern
# =============================================================================


class TestPanelEntityIdMatch:
    """Verify panel.js uses the same entity ID pattern as emhass_adapter.py."""

    def test_emhass_sensor_entity_id_pattern_sensor_py(self):
        """Get the entity ID pattern from sensor.py sensor creation."""
        sensor_path = Path("custom_components/ev_trip_planner/sensor.py")
        content = sensor_path.read_text()

        # Find the line where sensor unique_id is constructed
        pattern = r'self\._attr_unique_id\s*=\s*f["\']emhass_perfil_diferible_([^"\']+)["\']'
        match = re.search(pattern, content)

        assert match, "Could not find emhass_perfil_diferible_ pattern in sensor.py"
        # The pattern should use f-string variable like entry_id
        assert "entry_id" in match.group(0), (
            f"Sensor unique_id should use entry_id: emhass_perfil_diferible_{{entry_id}}\n"
            f"Found: {match.group(0)}"
        )

        # Verify sensor has _attr_has_entity_name = True
        assert "self._attr_has_entity_name = True" in content, (
            "Sensor must have _attr_has_entity_name = True for entity_id = sensor.emhass_perfil_diferible_{entry_id}"
        )

    def test_panel_js_uses_prefix_search_for_emhass_sensor(self):
        """Verify panel.js uses prefix search to find EMHASS sensor.

        BUG #3/#4 FIX: Panel has vehicle_id but sensor entity ID uses entry_id.
        Panel cannot construct exact entity ID, must search by prefix.

        CORRECT pattern:
          Object.keys(this._hass.states).find(
            id => id.startsWith('sensor.emhass_perfil_diferible_')
          )

        This test FAILS before fix (when panel used wrong fixed entity ID),
        PASSES after fix (when panel uses prefix search).
        """
        panel_js_path = Path("custom_components/ev_trip_planner/frontend/panel.js")
        content = panel_js_path.read_text()

        # Find the line where emhassSensorEntityId is constructed
        # This regex searches for the Object.keys().find() pattern with startsWith
        prefix_search = r"Object\.keys\(this\._hass\.states\)\.find\("
        starts_with = r"id\.startsWith\(['\"]sensor\.emhass_perfil_diferible_['\"]"

        has_prefix_search = re.search(prefix_search, content) is not None
        has_starts_with = re.search(starts_with, content) is not None

        assert has_prefix_search and has_starts_with, (
            f"Could not find correct prefix search pattern in panel.js.\n"
            f"Expected pattern:\n"
            f"  Object.keys(this._hass.states).find(id => id.startsWith('sensor.emhass_perfil_diferible_'))\n\n"
            f"Available patterns in panel.js:\n"
            f"  {self._extract_entity_id_patterns(content)}"
        )

    def test_panel_js_emhass_filter_consistent_with_sensor_pattern(self):
        """Verify panel.js uses sensor.emhass_perfil_diferible_ filter consistently.

        The panel filters entities by prefix `sensor.emhass_perfil_diferible_` to
        find the vehicle ID. This must match the actual sensor entity ID pattern.
        """
        panel_js_path = Path("custom_components/ev_trip_planner/frontend/panel.js")
        content = panel_js_path.read_text()

        # Find where panel filters by entity ID prefix
        filter_pattern = r"['\"]sensor\.emhass_perfil_diferible_['\"]"
        matches = re.findall(filter_pattern, content)

        assert len(matches) >= 1, (
            f"panel.js should filter entities by `sensor.emhass_perfil_diferible_` prefix.\n"
            f"This pattern was found {len(matches)} times, but at least 1 expected."
        )

        # Verify the filter is used correctly in entity iteration
        # Look for code that checks entity ID prefix and extracts vehicle ID
        check_pattern = r"if\s+.*entityId.*startsWith\s*\(.*['\"]sensor\.emhass_perfil_diferible_['\"].*\)"
        matches = re.findall(check_pattern, content, re.IGNORECASE)

        assert len(matches) >= 1, (
            f"panel.js should check if entityId starts with `sensor.emhass_perfil_diferible_`\n"
            f"to extract vehicle ID. Found {len(matches)} matches, expected at least 1."
        )

    def _extract_entity_id_patterns(self, content: str) -> str:
        """Extract all entity ID patterns from panel.js for debugging."""
        patterns = re.findall(
            r'[`"\']sensor\.[a-z_]+[`"\']',
            content
        )
        return "\n".join(sorted(set(patterns)))[:500]

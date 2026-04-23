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
        """Verify panel.js filters EMHASS sensor by vehicle_id attribute for multi-vehicle safety.

        BUG #3/#4 FIX (UPDATED): Panel has vehicle_id but sensor entity ID uses entry_id.
        Panel cannot construct exact entity ID, must search by prefix AND verify vehicle_id.

        FR-2.1 MULTI-VEHICLE FIX: In multi-vehicle installs, panel must filter EMHASS
        sensors by vehicle_id attribute to avoid rendering/copying wrong vehicle's config.

        CORRECT pattern (updated for multi-vehicle safety):
          for (const [entityId, state] of Object.entries(states)) {
            if (entityId.includes('emhass_perfil_diferible_')) {
              const vehicleId = state.attributes?.vehicle_id;
              if (vehicleId === this._vehicleId) {
                emhassSensorEntityId = entityId;
                break;
              }
            }
          }

        This test verifies:
        1. Panel searches for sensor by prefix 'emhass_perfil_diferible_' using includes
        2. Panel filters by vehicle_id attribute (multi-vehicle safety)
        3. Pattern matches _getVehicleStates() filtering for consistency
        """
        panel_js_path = Path("custom_components/ev_trip_planner/frontend/panel.js")
        content = panel_js_path.read_text()

        # Verify panel uses includes to find EMHASS sensor by pattern
        includes_pattern = r"includes\(['\"]emhass_perfil_diferible_['\"]"
        has_includes = re.search(includes_pattern, content) is not None

        assert has_includes, (
            f"Panel.js must filter EMHASS sensors using includes('emhass_perfil_diferible_').\n"
            f"Available patterns in panel.js:\n"
            f"  {self._extract_entity_id_patterns(content)}"
        )

        # Verify panel filters by vehicle_id attribute (FR-2.1: multi-vehicle safety)
        vehicle_id_filter = r"state\.attributes\?\.vehicle_id"
        has_vehicle_filter = re.search(vehicle_id_filter, content) is not None

        assert has_vehicle_filter, (
            "Panel.js must filter EMHASS sensors by vehicle_id attribute for multi-vehicle safety.\n"
            "Expected: state.attributes?.vehicle_id check in _renderEmhassConfig()"
        )

        # Verify the filter comparison matches current vehicle
        vehicle_comparison = r"vehicleId === this\._vehicleId"
        has_vehicle_comparison = re.search(vehicle_comparison, content) is not None

        assert has_vehicle_comparison, (
            "Panel.js must compare sensor vehicle_id with this._vehicleId for filtering.\n"
            "Expected: vehicleId === this._vehicleId check in _renderEmhassConfig()"
        )

    def test_panel_js_emhass_filter_consistent_with_sensor_pattern(self):
        """Verify panel.js emhass filtering is consistent with _getVehicleStates() pattern.

        FR-2.1: Multi-vehicle safety - both _renderEmhassConfig() and _getVehicleStates()
        must use the same vehicle_id filtering to ensure consistency.

        REQUIREMENT: Panel emhass sensor lookup in _renderEmhassConfig() must match
        the filtering pattern used in _getVehicleStates():
        1. Filter by pattern 'emhass_perfil_diferible_' using includes
        2. Verify vehicle_id attribute matches this._vehicleId
        3. Return first matching sensor (break out of loop)
        """
        panel_js_path = Path("custom_components/ev_trip_planner/frontend/panel.js")
        content = panel_js_path.read_text()

        # Find where panel filters by entity ID pattern using includes
        filter_pattern = r"includes\(['\"]emhass_perfil_diferible_['\"]"
        matches = re.findall(filter_pattern, content)

        assert len(matches) >= 1, (
            f"panel.js should filter entities using includes('emhass_perfil_diferible_') pattern.\n"
            f"This pattern was found {len(matches)} times, but at least 1 expected."
        )

        # Verify the filter is used correctly in entity iteration (FR-2.1 multi-vehicle check)
        # Look for code that checks entity ID pattern AND extracts/verifies vehicle ID
        check_pattern = r"if\s+.*entityId.*includes\s*\(.*['\"]emhass_perfil_diferible_['\"].*\)"
        matches = re.findall(check_pattern, content, re.IGNORECASE)

        assert len(matches) >= 1, (
            f"panel.js should check if entityId includes `emhass_perfil_diferible_`\n"
            f"to extract vehicle ID. Found {len(matches)} matches, expected at least 1."
        )

        # FR-2.1 MUST-HAVE: Verify vehicle_id filtering is in _renderEmhassConfig
        renderemhass_section = self._extract_method_body(content, "_renderEmhassConfig")
        assert renderemhass_section, (
            "Could not find _renderEmhassConfig() method in panel.js"
        )

        has_vehicle_filter_in_method = "state.attributes?.vehicle_id" in renderemhass_section or \
                                       "state.attributes?.vehicle_id" in renderemhass_section
        assert has_vehicle_filter_in_method, (
            "FR-2.1: _renderEmhassConfig() must filter EMHASS sensors by vehicle_id attribute.\n"
            "This prevents panel from rendering wrong vehicle's config in multi-vehicle installs."
        )

    def _extract_method_body(self, content: str, method_name: str) -> str:
        """Extract method body for validation.

        Args:
            content: JavaScript file content
            method_name: Name of the method to extract

        Returns:
            Method body or empty string if not found
        """
        # Find method definition and extract its body
        pattern = rf"{method_name}\s*\(\s*\)\s*\{{(.*?)\n  \}}"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else ""

    def _extract_entity_id_patterns(self, content: str) -> str:
        """Extract all entity ID patterns from panel.js for debugging."""
        patterns = re.findall(
            r'[`"\']sensor\.[a-z_]+[`"\']',
            content
        )
        return "\n".join(sorted(set(patterns)))[:500]

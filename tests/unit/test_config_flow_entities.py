"""Tests for config_flow/_entities.py uncovered code paths."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.ev_trip_planner.config_flow._entities import (
    auto_select_sensor,
    scan_entities,
    scan_notify_entities,
)


class TestScanEntities:
    """Test scan_entities."""

    def test_scan_returns_matching_entities(self):
        """Returns sorted matching entity IDs."""
        hass = MagicMock()
        mock_registry = MagicMock()
        mock_registry.entities = {
            "binary_sensor.motion": MagicMock(),
            "input_boolean.guest": MagicMock(),
            "sensor.temperature": MagicMock(),
        }
        with patch(
            "custom_components.ev_trip_planner.config_flow._entities.er.async_get",
            return_value=mock_registry,
        ):
            result = scan_entities(hass, ["binary_sensor.", "input_boolean."])
            assert result == ["binary_sensor.motion", "input_boolean.guest"]

    def test_scan_no_matches(self):
        """No matching entities returns empty list."""
        hass = MagicMock()
        mock_registry = MagicMock()
        mock_registry.entities = {"sensor.temp": MagicMock()}
        with patch(
            "custom_components.ev_trip_planner.config_flow._entities.er.async_get",
            return_value=mock_registry,
        ):
            result = scan_entities(hass, ["binary_sensor.", "input_boolean."])
            assert result == []

    def test_scan_exception_returns_empty_list(self):
        """Exception in async_get returns empty list (lines 44-46)."""
        hass = MagicMock()
        with patch(
            "custom_components.ev_trip_planner.config_flow._entities.er.async_get",
            side_effect=RuntimeError("registry error"),
        ):
            result = scan_entities(hass, ["binary_sensor."])
            assert result == []


class TestScanNotifyEntities:
    """Test scan_notify_entities."""

    def test_scan_notify_with_notify_entities(self):
        """Returns notify entities from registry."""
        hass = MagicMock()
        mock_entity1 = MagicMock()
        mock_entity1.domain = "notify"
        mock_entity1.entity_id = "notify.mobile"
        mock_entity2 = MagicMock()
        mock_entity2.domain = "sensor"
        mock_entity2.entity_id = "sensor.temp"
        mock_registry = MagicMock()
        mock_registry.entities.values.return_value = [mock_entity1, mock_entity2]
        with patch(
            "custom_components.ev_trip_planner.config_flow._entities.er.async_get",
            return_value=mock_registry,
        ):
            result = scan_notify_entities(hass)
            assert result == ["notify.mobile"]

    def test_scan_notify_fallback_to_services(self):
        """Registry exception → falls back to services API (lines 73-84)."""
        hass = MagicMock()
        hass.services.async_services.return_value = {
            "notify": {"mobile": {}, "email": {}}
        }
        with patch(
            "custom_components.ev_trip_planner.config_flow._entities.er.async_get",
            side_effect=RuntimeError("registry unavailable"),
        ):
            result = scan_notify_entities(hass)
            assert result == ["email", "mobile"]


class TestAutoSelectSensor:
    """Test auto_select_sensor."""

    def test_already_selected_returns_early(self):
        """Sensor already in user_input → returns unchanged (line 108)."""
        user_input = {"charging_sensor": "binary_sensor.motion"}
        hass = MagicMock()
        result = auto_select_sensor(
            hass, ["binary_sensor."], user_input, "charging_sensor"
        )
        assert result == user_input

    def test_auto_select_first_entity(self):
        """No sensor selected → selects first from scan."""
        hass = MagicMock()
        user_input = {"charging_sensor": None}
        mock_registry = MagicMock()
        mock_registry.entities = {
            "binary_sensor.motion": MagicMock(),
        }
        with patch(
            "custom_components.ev_trip_planner.config_flow._entities.er.async_get",
            return_value=mock_registry,
        ):
            result = auto_select_sensor(
                hass, ["binary_sensor."], user_input, "charging_sensor"
            )
            assert result["charging_sensor"] == "binary_sensor.motion"

    def test_no_entities_available(self):
        """No entities found → logs error, returns unchanged (line 121)."""
        hass = MagicMock()
        user_input = {"charging_sensor": None}
        mock_registry = MagicMock()
        mock_registry.entities = {}
        with patch(
            "custom_components.ev_trip_planner.config_flow._entities.er.async_get",
            return_value=mock_registry,
        ):
            result = auto_select_sensor(
                hass, ["binary_sensor."], user_input, "charging_sensor"
            )
            assert result == user_input

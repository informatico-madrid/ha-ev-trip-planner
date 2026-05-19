"""US-5: Log constant assertion tests for vehicle module.

Asserts that extracted log format string constants exist and have
the expected values. These tests kill log_text mutations where
mutmut replaces string literals in logger calls with None.
"""

from unittest.mock import MagicMock

import pytest


class TestVehicleControllerLogConstants:
    """Test US-5 log constants in VehicleController."""

    def test_log_constants_exist_in_controller(self):
        """Verify log constants are importable from controller module."""
        from custom_components.ev_trip_planner.vehicle.controller import (
            _LOG_SETUP,
            _LOG_PRESENCE_FAILED,
            _LOG_ALREADY_CHARGING,
            _LOG_SENSOR_NOT_FOUND,
            _LOG_CHARGING_STATUS,
            _LOG_CANNOT_ACTIVATE,
            _LOG_NO_STRATEGY,
            _LOG_RETRY_EXCEEDED,
            _LOG_ACTIVATED,
            _LOG_ACTIVATION_FAILED,
            _LOG_DISCONNECT_RESET,
            _LOG_RETRY_RESET,
        )

        # All constants must be non-empty strings
        assert isinstance(_LOG_SETUP, str) and _LOG_SETUP
        assert isinstance(_LOG_PRESENCE_FAILED, str) and _LOG_PRESENCE_FAILED
        assert isinstance(_LOG_ALREADY_CHARGING, str) and _LOG_ALREADY_CHARGING
        assert isinstance(_LOG_SENSOR_NOT_FOUND, str) and _LOG_SENSOR_NOT_FOUND
        assert isinstance(_LOG_CHARGING_STATUS, str) and _LOG_CHARGING_STATUS
        assert isinstance(_LOG_CANNOT_ACTIVATE, str) and _LOG_CANNOT_ACTIVATE
        assert isinstance(_LOG_NO_STRATEGY, str) and _LOG_NO_STRATEGY
        assert isinstance(_LOG_RETRY_EXCEEDED, str) and _LOG_RETRY_EXCEEDED
        assert isinstance(_LOG_ACTIVATED, str) and _LOG_ACTIVATED
        assert isinstance(_LOG_ACTIVATION_FAILED, str) and _LOG_ACTIVATION_FAILED
        assert isinstance(_LOG_DISCONNECT_RESET, str) and _LOG_DISCONNECT_RESET
        assert isinstance(_LOG_RETRY_RESET, str) and _LOG_RETRY_RESET

    def test_log_setup_format(self):
        """_LOG_SETUP format string matches expected pattern."""
        from custom_components.ev_trip_planner.vehicle.controller import _LOG_SETUP

        assert "%s" in _LOG_SETUP
        result = _LOG_SETUP % "test_vehicle"
        assert "test_vehicle" in result

    def test_log_already_charging_format(self):
        """_LOG_ALREADY_CHARGING format string matches expected pattern."""
        from custom_components.ev_trip_planner.vehicle.controller import _LOG_ALREADY_CHARGING

        assert "%s" in _LOG_ALREADY_CHARGING
        result = _LOG_ALREADY_CHARGING % "test_vehicle"
        assert "test_vehicle" in result

    def test_log_sensor_not_found_format(self):
        """_LOG_SENSOR_NOT_FOUND has two format placeholders."""
        from custom_components.ev_trip_planner.vehicle.controller import _LOG_SENSOR_NOT_FOUND

        assert _LOG_SENSOR_NOT_FOUND.count("%s") >= 2
        result = _LOG_SENSOR_NOT_FOUND % ("sensor.charging", "test_vehicle")
        assert "sensor.charging" in result
        assert "test_vehicle" in result

    def test_log_charging_status_format(self):
        """_LOG_CHARGING_STATUS has three format placeholders."""
        from custom_components.ev_trip_planner.vehicle.controller import _LOG_CHARGING_STATUS

        assert _LOG_CHARGING_STATUS.count("%s") >= 3
        result = _LOG_CHARGING_STATUS % ("v1", "sensor.charging", "on")
        assert "v1" in result
        assert "sensor.charging" in result
        assert "on" in result

    def test_log_retry_exceeded_format(self):
        """_LOG_RETRY_EXCEEDED has mixed format placeholders (%d and %s)."""
        from custom_components.ev_trip_planner.vehicle.controller import (
            _LOG_RETRY_EXCEEDED,
        )

        # Should accept int placeholders
        result = _LOG_RETRY_EXCEEDED % (3, "test_vehicle", 300)
        assert "3" in result
        assert "test_vehicle" in result
        assert "300" in result

    def test_log_activation_failed_format(self):
        """_LOG_ACTIVATION_FAILED has mixed format placeholders."""
        from custom_components.ev_trip_planner.vehicle.controller import _LOG_ACTIVATION_FAILED

        result = _LOG_ACTIVATION_FAILED % ("v1", 2, 3)
        assert "v1" in result
        assert "2" in result
        assert "3" in result


class TestSwitchStrategyLogConstants:
    """Test US-5 log constants in SwitchStrategy."""

    def test_switch_log_constants_exist(self):
        """Verify switch log constants exist in strategy module."""
        from custom_components.ev_trip_planner.vehicle.strategy import (
            _LOG_SWITCH_ACTIVATED,
            _LOG_SWITCH_ERROR,
            _LOG_SWITCH_DEACTIVATED,
            _LOG_SWITCH_DEACTIVATE_ERROR,
            _LOG_SWITCH_STATUS_ON,
        )

        assert isinstance(_LOG_SWITCH_ACTIVATED, str) and _LOG_SWITCH_ACTIVATED
        assert isinstance(_LOG_SWITCH_ERROR, str) and _LOG_SWITCH_ERROR
        assert isinstance(_LOG_SWITCH_DEACTIVATED, str) and _LOG_SWITCH_DEACTIVATED
        assert isinstance(_LOG_SWITCH_DEACTIVATE_ERROR, str) and _LOG_SWITCH_DEACTIVATE_ERROR
        assert isinstance(_LOG_SWITCH_STATUS_ON, str) and _LOG_SWITCH_STATUS_ON

    def test_switch_activated_format(self):
        """_LOG_SWITCH_ACTIVATED has placeholder."""
        from custom_components.ev_trip_planner.vehicle.strategy import _LOG_SWITCH_ACTIVATED

        result = _LOG_SWITCH_ACTIVATED % "switch.charging"
        assert "switch.charging" in result

    def test_switch_error_format(self):
        """_LOG_SWITCH_ERROR has placeholder."""
        from custom_components.ev_trip_planner.vehicle.strategy import _LOG_SWITCH_ERROR

        result = _LOG_SWITCH_ERROR % Exception("fail")
        assert "fail" in result

    def test_switch_deactivated_format(self):
        """_LOG_SWITCH_DEACTIVATED has placeholder."""
        from custom_components.ev_trip_planner.vehicle.strategy import _LOG_SWITCH_DEACTIVATED

        result = _LOG_SWITCH_DEACTIVATED % "switch.charging"
        assert "switch.charging" in result

    def test_switch_deactivate_error_format(self):
        """_LOG_SWITCH_DEACTIVATE_ERROR has placeholder."""
        from custom_components.ev_trip_planner.vehicle.strategy import _LOG_SWITCH_DEACTIVATE_ERROR

        result = _LOG_SWITCH_DEACTIVATE_ERROR % Exception("fail")
        assert "fail" in result

    def test_switch_status_on_value(self):
        """_LOG_SWITCH_STATUS_ON is the literal 'on'."""
        from custom_components.ev_trip_planner.vehicle.strategy import _LOG_SWITCH_STATUS_ON

        assert _LOG_SWITCH_STATUS_ON == "on"


class TestServiceStrategyLogConstants:
    """Test US-5 log constants in ServiceStrategy."""

    def test_service_log_constants_exist(self):
        """Verify service log constants exist in strategy module."""
        from custom_components.ev_trip_planner.vehicle.strategy import (
            _LOG_SERVICE_ACTIVATED,
            _LOG_SERVICE_ERROR,
            _LOG_SERVICE_DEACTIVATED,
            _LOG_SERVICE_DEACTIVATE_ERROR,
        )

        assert isinstance(_LOG_SERVICE_ACTIVATED, str) and _LOG_SERVICE_ACTIVATED
        assert isinstance(_LOG_SERVICE_ERROR, str) and _LOG_SERVICE_ERROR
        assert isinstance(_LOG_SERVICE_DEACTIVATED, str) and _LOG_SERVICE_DEACTIVATED
        assert isinstance(_LOG_SERVICE_DEACTIVATE_ERROR, str) and _LOG_SERVICE_DEACTIVATE_ERROR

    def test_service_activated_format(self):
        """_LOG_SERVICE_ACTIVATED has placeholder."""
        from custom_components.ev_trip_planner.vehicle.strategy import _LOG_SERVICE_ACTIVATED

        result = _LOG_SERVICE_ACTIVATED % "homeassistant.turn_on"
        assert "homeassistant.turn_on" in result

    def test_service_error_format(self):
        """_LOG_SERVICE_ERROR has two placeholders."""
        from custom_components.ev_trip_planner.vehicle.strategy import _LOG_SERVICE_ERROR

        result = _LOG_SERVICE_ERROR % ("homeassistant.turn_on", Exception("fail"))
        assert "homeassistant.turn_on" in result

    def test_service_deactivated_format(self):
        """_LOG_SERVICE_DEACTIVATED has placeholder."""
        from custom_components.ev_trip_planner.vehicle.strategy import _LOG_SERVICE_DEACTIVATED

        result = _LOG_SERVICE_DEACTIVATED % "homeassistant.turn_off"
        assert "homeassistant.turn_off" in result

    def test_service_deactivate_error_format(self):
        """_LOG_SERVICE_DEACTIVATE_ERROR has two placeholders."""
        from custom_components.ev_trip_planner.vehicle.strategy import _LOG_SERVICE_DEACTIVATE_ERROR

        result = _LOG_SERVICE_DEACTIVATE_ERROR % ("homeassistant.turn_off", Exception("fail"))
        assert "homeassistant.turn_off" in result


class TestScriptStrategyLogConstants:
    """Test US-5 log constants in ScriptStrategy."""

    def test_script_log_constants_exist(self):
        """Verify script log constants exist in external module."""
        from custom_components.ev_trip_planner.vehicle.external import (
            _LOG_SCRIPT_ACTIVATED,
            _LOG_SCRIPT_ERROR,
            _LOG_SCRIPT_DEACTIVATED,
        )

        assert isinstance(_LOG_SCRIPT_ACTIVATED, str) and _LOG_SCRIPT_ACTIVATED
        assert isinstance(_LOG_SCRIPT_ERROR, str) and _LOG_SCRIPT_ERROR
        assert isinstance(_LOG_SCRIPT_DEACTIVATED, str) and _LOG_SCRIPT_DEACTIVATED

    def test_script_activated_format(self):
        """_LOG_SCRIPT_ACTIVATED has placeholder."""
        from custom_components.ev_trip_planner.vehicle.external import _LOG_SCRIPT_ACTIVATED

        result = _LOG_SCRIPT_ACTIVATED % "script.start_charging"
        assert "script.start_charging" in result

    def test_script_error_format(self):
        """_LOG_SCRIPT_ERROR has two placeholders."""
        from custom_components.ev_trip_planner.vehicle.external import _LOG_SCRIPT_ERROR

        result = _LOG_SCRIPT_ERROR % ("script.start_charging", Exception("fail"))
        assert "script.start_charging" in result

    def test_script_deactivated_format(self):
        """_LOG_SCRIPT_DEACTIVATED has placeholder."""
        from custom_components.ev_trip_planner.vehicle.external import _LOG_SCRIPT_DEACTIVATED

        result = _LOG_SCRIPT_DEACTIVATED % "script.stop_charging"
        assert "script.stop_charging" in result


class TestExternalStrategyLogConstants:
    """Test US-5 log constants in ExternalStrategy."""

    def test_external_log_constants_exist(self):
        """Verify external log constants exist in external module."""
        from custom_components.ev_trip_planner.vehicle.external import (
            _LOG_EXTERNAL_NOOP,
        )

        assert isinstance(_LOG_EXTERNAL_NOOP, str) and _LOG_EXTERNAL_NOOP

    def test_external_noop_value(self):
        """_LOG_EXTERNAL_NOOP is the expected string."""
        from custom_components.ev_trip_planner.vehicle.external import _LOG_EXTERNAL_NOOP

        assert "no action taken" in _LOG_EXTERNAL_NOOP.lower()

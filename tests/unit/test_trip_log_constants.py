"""Constant-assertion tests for US-5 log string extraction.

These tests kill log_text mutations by asserting the exact values of
module-level log format string constants. Without these tests, mutmut
can mutate the constant string values and the mutants survive because
log output is not tested.
"""

from __future__ import annotations

import pytest


class TestTripCRUDLogConstants:
    """Assert values of log format string constants in _crud.py."""

    def test_log_add_recurring_debug_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert (
            _crud._LOG_ADD_RECURRING_DEBUG
            == "Adding recurring trip for vehicle %s: dia_semana=%s, hora=%s, km=%.1f, kwh=%.2f"
        )

    def test_log_add_recurring_info_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert _crud._LOG_ADD_RECURRING_INFO == "Added recurring trip %s for vehicle %s"

    def test_log_add_punctual_debug_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert (
            _crud._LOG_ADD_PUNCTUAL_DEBUG
            == "Adding punctual trip for vehicle %s: datetime=%s, km=%.1f, kwh=%.2f"
        )

    def test_log_add_punctual_info_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert _crud._LOG_ADD_PUNCTUAL_INFO == "Added punctual trip %s for vehicle %s"

    def test_log_update_debug_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert _crud._LOG_UPDATE_DEBUG == "Updating trip %s for vehicle %s: updates=%s"

    def test_log_update_info_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert _crud._LOG_UPDATE_INFO == "Updated %s trip %s for vehicle %s"

    def test_log_update_not_found_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert (
            _crud._LOG_UPDATE_NOT_FOUND
            == "Trip %s not found for update in vehicle %s"
        )

    def test_log_delete_debug_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert _crud._LOG_DELETE_DEBUG == "Deleting trip %s from vehicle %s"

    def test_log_delete_not_found_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert (
            _crud._LOG_DELETE_NOT_FOUND
            == "Trip %s not found for deletion in vehicle %s"
        )

    def test_log_delete_info_format(self):
        _crud = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._crud"
        )
        assert _crud._LOG_DELETE_INFO == "Deleted trip %s from vehicle %s"


class TestTripPersistenceLogConstants:
    """Assert values of log format string constants in _persistence.py."""

    def test_log_setup_info_format(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SETUP_INFO
            == "Configurando gestor de viajes para vehículo: %s"
        )

    def test_log_save_start_info_format(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SAVE_START_INFO
            == "async_save_trips START - vehicle=%s, recurrentes=%d, puntuales=%d"
        )

    def test_log_save_injected(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_SAVE_INJECTED == "=== Using injected storage ==="

    def test_log_save_fallback(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_SAVE_FALLBACK == "=== Using fallback HA Store ==="

    def test_log_save_key_info(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_SAVE_KEY_INFO == "Creating store with key: %s"

    def test_log_save_success_info(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SAVE_SUCCESS_INFO
            == "Viajes guardados en HA storage: %d recurrentes, %d puntuales"
        )

    def test_log_save_error(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_SAVE_ERROR == "Error guardando viajes: %s"

    def test_log_load_skip_debug(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_LOAD_SKIP_DEBUG
            == "Skipping _load_trips for %s: already have %d punctual, %d recurring trips"
        )

    def test_log_load_start_debug(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_LOAD_START_DEBUG == "=== _load_trips START === vehicle=%s"

    def test_log_load_cancel_warning(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_LOAD_CANCEL_WARNING
            == "Storage load cancelled (known timing issue) - continuing with empty state"
        )

    def test_log_load_error(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_LOAD_ERROR == "Error cargando viajes: %s"

    def test_log_load_yaml_error(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_LOAD_YAML_ERROR == "Error cargando viajes desde YAML: %s"

    def test_log_save_yaml_fail_error(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SAVE_YAML_FAIL_ERROR
            == "Error guardando viajes en YAML: %s"
        )

    def test_log_sanitize_warning(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SANITIZE_WARNING
            == "%d recurring trip(s) ignored due to invalid hora format."
        )
